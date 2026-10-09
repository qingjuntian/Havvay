"""FastAPI entry point for the audiobook preparation and review service."""

from __future__ import annotations

import hashlib
import io
import json
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from service import store
from src.text_normalize import normalize_text

MAX_UPLOAD_BYTES = int(os.environ.get("READING_MAX_UPLOAD_BYTES", str(200 * 1024 * 1024)))
MAX_PAGE_IMAGE_BYTES = int(os.environ.get("READING_MAX_PAGE_IMAGE_BYTES", str(25 * 1024 * 1024)))
UI_PATH = Path(__file__).with_name("ui.html")
app = FastAPI(title="Reading Audiobook Service", version="0.1.0")


class TextUpdate(BaseModel):
    text: str


class Approval(BaseModel):
    stage: str
    note: str = ""


@app.on_event("startup")
def startup() -> None:
    store.init_db()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _enqueue_job(book_id: str, stage: str, task_name: str) -> dict:
    active_job = store.get_active_job(book_id, stage)
    if active_job:
        return {"id": active_job["id"], "status": active_job["status"], "reused": True}
    job_id = str(uuid.uuid4())
    store.create_job(job_id, book_id, stage)
    store.set_book_state(book_id, stage, "queued")
    try:
        from redis import Redis
        from rq import Queue

        connection = Redis.from_url(os.environ.get("READING_REDIS_URL", "redis://127.0.0.1:6379/0"))
        timeout = 86400 if stage in {
            "preview_audio", "preview_audio_update", "full_audio", "full_audio_update",
            "preview_video", "full_video",
        } else 7200
        queue_job = Queue("reading", connection=connection).enqueue(task_name, job_id, job_timeout=timeout)
        store.update_job(job_id, "queued", queue_id=queue_job.id)
        return {"id": job_id, "status": "queued"}
    except Exception as exc:
        store.update_job(job_id, "failed", error=f"Could not enqueue {stage}: {exc}")
        store.set_book_state(book_id, stage, "queue_unavailable")
        store.add_event(book_id, stage, "queue_failed", note=str(exc))
        return {"id": job_id, "status": "failed", "error": str(exc)}


def _enqueue_document_job(book_id: str) -> dict:
    return _enqueue_job(book_id, "document", "service.worker.prepare_document")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return UI_PATH.read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/books")
def books() -> list[dict]:
    return store.list_books()


@app.post("/api/books", status_code=201)
async def create_book(pdf: UploadFile = File(...), title: str = Form(default="")) -> dict:
    filename = Path(pdf.filename or "book.pdf").name
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="Upload a laid-out .pdf document")

    book_id = str(uuid.uuid4())
    book_root = store.book_directory(book_id)
    input_path = book_root / "inputs" / "original.pdf"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with input_path.open("wb") as target:
            while block := await pdf.read(1024 * 1024):
                written += len(block)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="PDF exceeds the configured upload limit")
                target.write(block)
    except Exception:
        input_path.unlink(missing_ok=True)
        raise
    finally:
        await pdf.close()

    if written == 0:
        input_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty")
    with input_path.open("rb") as uploaded_file:
        pdf_header = uploaded_file.read(1024)
    if b"%PDF-" not in pdf_header:
        input_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF")

    book_title = title.strip() or Path(filename).stem or "Untitled book"
    store.create_book(book_id, book_title)
    store.add_artifact(
        book_id, "input", "source_pdf", input_path, _sha256(input_path), "application/pdf",
        {"original_filename": filename, "bytes": written},
    )
    job = _enqueue_document_job(book_id)
    return {"id": book_id, "title": book_title, "status": job["status"], "job": job}


@app.post("/api/books/{book_id}/prepare-document")
def prepare_document_again(book_id: str) -> dict:
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if book["current_stage"] != "document" or book["status"] not in {"queue_unavailable", "failed"}:
        raise HTTPException(status_code=409, detail="Document preparation is not waiting for a retry")
    return _enqueue_document_job(book_id)


@app.post("/api/books/{book_id}/reference")
async def upload_reference(
    book_id: str,
    voice: UploadFile = File(...),
    ref_text: str = Form(...),
) -> dict:
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if book["current_stage"] != "reference" or book["status"] != "awaiting_reference":
        raise HTTPException(status_code=409, detail="Approve the TTS text before uploading a voice reference")
    if not ref_text.strip():
        raise HTTPException(status_code=400, detail="REF_TEXT must match the spoken words in the recording")
    filename = Path(voice.filename or "voice.wav").name
    allowed_extensions = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
    if Path(filename).suffix.lower() not in allowed_extensions:
        raise HTTPException(status_code=415, detail="Upload WAV, MP3, M4A, FLAC, or OGG audio")

    input_dir = store.book_directory(book_id) / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    audio_path = input_dir / f"voice_{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
    written = 0
    try:
        with audio_path.open("wb") as target:
            while block := await voice.read(1024 * 1024):
                written += len(block)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Voice sample exceeds the configured upload limit")
                target.write(block)
    except Exception:
        audio_path.unlink(missing_ok=True)
        raise
    finally:
        await voice.close()
    if written == 0:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded voice sample is empty")

    transcript_path = input_dir / f"ref_text_{uuid.uuid4().hex}.txt"
    transcript_path.write_text(ref_text.strip() + "\n", encoding="utf-8")
    store.add_artifact(
        book_id, "reference_input", "voice_sample", audio_path, _sha256(audio_path),
        voice.content_type or "application/octet-stream", {"original_filename": filename, "bytes": written},
    )
    store.add_artifact(
        book_id, "reference_input", "ref_text", transcript_path, _sha256(transcript_path),
        "text/plain; charset=utf-8", {"characters": len(ref_text.strip())},
    )
    store.add_event(book_id, "reference_input", "uploaded", "user", "Voice sample and REF_TEXT uploaded")
    job = _enqueue_job(book_id, "reference_preparation", "service.worker.prepare_reference")
    return {"id": book_id, "status": job["status"], "job": job}


@app.get("/api/books/{book_id}")
def book_detail(book_id: str) -> dict:
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.post("/api/books/{book_id}/pages/{page_number}/image")
async def replace_page_image(book_id: str, page_number: int, image: UploadFile = File(...)) -> dict:
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be positive")
    if store.count_active_jobs(book_id):
        raise HTTPException(status_code=409, detail="Wait for this book's active task to finish before replacing a page image")

    metadata_artifacts = [
        item for item in book["artifacts"]
        if item["stage"] == "pages" and item["kind"] == "page_metadata" and not item["stale"]
    ]
    if not metadata_artifacts:
        raise HTTPException(status_code=409, detail="Page metadata is not ready; prepare the uploaded PDF first")
    metadata_artifact = max(metadata_artifacts, key=lambda item: item["version"])
    metadata_path = (store.service_home() / metadata_artifact["path"]).resolve()
    try:
        metadata_path.relative_to(store.service_home().resolve())
        page_count = len(json.loads(metadata_path.read_text(encoding="utf-8"))["pages"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Could not read the book's page metadata") from exc
    if page_number > page_count:
        raise HTTPException(status_code=404, detail=f"Page {page_number} does not exist; this book has {page_count} pages")

    raw_image = await image.read(MAX_PAGE_IMAGE_BYTES + 1)
    await image.close()
    if not raw_image:
        raise HTTPException(status_code=400, detail="The uploaded image is empty")
    if len(raw_image) > MAX_PAGE_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Page image exceeds the 25 MB upload limit")

    try:
        from PIL import Image, ImageOps, UnidentifiedImageError

        with Image.open(io.BytesIO(raw_image)) as source:
            if source.format not in {"PNG", "JPEG", "WEBP"}:
                raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or WebP page image")
            if source.width * source.height > 100_000_000:
                raise HTTPException(status_code=413, detail="Page image dimensions are too large")
            normalized = ImageOps.exif_transpose(source).convert("RGB")
            output = io.BytesIO()
            normalized.save(output, format="PNG", optimize=True)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid supported image") from exc

    previous_versions = [
        item["version"] for item in book["artifacts"]
        if item["stage"] == "pages" and item["kind"] == "page_image"
        and item["metadata"].get("page") == page_number
    ]
    page_version = max(previous_versions, default=0) + 1
    image_path = (
        store.book_directory(book_id) / "artifacts" / "page_images"
        / f"page_{page_number:04d}" / f"replacement_{page_version:03d}.png"
    )
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(output.getvalue())
    try:
        artifact = store.add_artifact(
            book_id, "pages", "page_image", image_path, _sha256(image_path), "image/png",
            {
                "page": page_number,
                "replacement": True,
                "page_version": page_version,
                "original_filename": Path(image.filename or "page.png").name,
                "width": normalized.width,
                "height": normalized.height,
            },
        )
        invalidated_count = store.invalidate_video_artifacts(book_id, f"Page {page_number} image replaced")
        store.add_event(
            book_id, "pages", "page_image_replaced", "user",
            f"Replaced page {page_number}; invalidated {invalidated_count} video artifacts",
            page_version,
        )
        if store.has_valid_artifact(book_id, "audiobook_mp3", ("final_audio_review",)):
            store.set_book_state(book_id, "full_video", "ready")
        elif store.has_valid_artifact(book_id, "audiobook_mp3", ("preview_audio_review",)):
            store.set_book_state(book_id, "preview_video", "ready")
        else:
            store.set_book_state(book_id, "pages_review", "awaiting_page_review")
    except Exception:
        image_path.unlink(missing_ok=True)
        raise
    return {**artifact, "invalidated_video_artifacts": invalidated_count}


@app.delete("/api/books/{book_id}")
def delete_book(book_id: str) -> dict[str, str]:
    try:
        result = store.delete_book(book_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Book not found")
    if result == "active_jobs":
        raise HTTPException(
            status_code=409,
            detail="This book has a queued or running task. Wait for it to finish before deleting the book.",
        )
    return {"id": book_id, "status": "deleted"}


@app.put("/api/books/{book_id}/text")
def update_text(book_id: str, update: TextUpdate) -> dict:
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if any(job["status"] in {"queued", "running"} for job in book["jobs"]):
        raise HTTPException(status_code=409, detail="Wait for the current processing task to finish before editing text")
    normalized_text = normalize_text(update.text)
    if not normalized_text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(normalized_text) > 2_000_000:
        raise HTTPException(status_code=413, detail="Text exceeds the 2 MB limit")
    page_artifacts = [
        item for item in book["artifacts"] if item["stage"] == "pages" and item["kind"] == "page_metadata"
    ]
    if page_artifacts:
        latest_pages = max(page_artifacts, key=lambda item: item["version"])
        metadata_path = (store.service_home() / latest_pages["path"]).resolve()
        page_count = len(json.loads(metadata_path.read_text(encoding="utf-8"))["pages"])
        if normalized_text.count("<<<BOOK_PAGE_BREAK>>>") != page_count - 1:
            raise HTTPException(status_code=400, detail=f"Text must keep exactly {page_count - 1} page-break markers")

    latest_text_artifact = max(
        (item for item in book["artifacts"] if item["stage"] == "text" and item["kind"] == "normalized_text"),
        key=lambda item: item["version"],
        default=None,
    )
    if latest_text_artifact is not None:
        previous_text_path = (store.service_home() / latest_text_artifact["path"]).resolve()
        previous_text_path.relative_to(store.service_home().resolve())
        if previous_text_path.is_file() and previous_text_path.read_text(encoding="utf-8") == normalized_text:
            return {**latest_text_artifact, "unchanged": True, "regeneration": None}

    final_audio_exists = any(
        item["kind"] == "audiobook_mp3" and item["stage"] == "final_audio_review"
        for item in book["artifacts"]
    )
    preview_audio_exists = any(
        item["kind"] == "audiobook_mp3" and item["stage"] == "preview_audio_review"
        for item in book["artifacts"]
    )

    versions = [
        item["version"] for item in book["artifacts"]
        if item["stage"] == "text" and item["kind"] == "normalized_text"
    ]
    version = max(versions, default=0) + 1
    output_path = store.book_directory(book_id) / "artifacts" / "text" / f"v{version}" / "book.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalized_text, encoding="utf-8")
    artifact = store.add_artifact(
        book_id, "text", "normalized_text", output_path, _sha256(output_path), "text/plain; charset=utf-8",
        {"edited_by_user": True},
    )
    invalidated_count = store.invalidate_text_dependent_artifacts(book_id, f"TTS text changed to version {version}")
    store.add_event(book_id, "text", "text_edited", "user", "Normalized TTS text updated", version)
    store.add_event(
        book_id, "text", "downstream_invalidated", "system",
        f"Invalidated {invalidated_count} audio/video artifacts derived from the previous text", version,
    )

    if final_audio_exists or preview_audio_exists:
        audio_kind = "full_audio" if final_audio_exists else "preview_audio"
        update_stage = f"{audio_kind}_update"
        task_name = "service.worker.synthesize_full_audio_update" if final_audio_exists else "service.worker.synthesize_preview_audio_update"
        queued_job = _enqueue_job(book_id, update_stage, task_name)
        return {**artifact, "invalidated_artifacts": invalidated_count, "regeneration": queued_job}

    store.set_book_state(book_id, "text_review", "awaiting_text_review")
    return {**artifact, "invalidated_artifacts": invalidated_count, "regeneration": None}


@app.post("/api/books/{book_id}/approve")
def approve_stage(book_id: str, approval: Approval) -> dict:
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    expected = {
        "pages": ("pages_review", "awaiting_page_review", "text_review", "awaiting_text_review"),
        "text": ("text_review", "awaiting_text_review", "reference", "awaiting_reference"),
        "reference": ("reference_review", "awaiting_reference_review", "preview_audio", "ready"),
        "preview_audio": ("preview_audio_review", "awaiting_preview_audio_review", "preview_video", "queued"),
        "preview_video": ("preview_video_review", "awaiting_preview_video_review", "full_audio", "queued"),
        "final_audio": ("final_audio_review", "awaiting_final_audio_review", "full_video", "queued"),
        "final_video": ("final_video_review", "awaiting_final_video_review", "complete", "complete"),
    }
    if approval.stage not in expected:
        raise HTTPException(status_code=400, detail="Unknown approval stage")
    current_stage, current_status, next_stage, next_status = expected[approval.stage]
    if approval.stage == "text" and store.has_valid_artifact(book_id, "processed_audio", ("reference_review",)):
        next_stage, next_status = "preview_audio", "ready"
    if book["current_stage"] != current_stage or book["status"] != current_status:
        raise HTTPException(status_code=409, detail="This stage is not currently waiting for approval")
    artifact_stage = {
        "pages": "pages",
        "text": "text",
        "reference": "reference_review",
        "preview_audio": "preview_audio_review",
        "preview_video": "preview_video_review",
        "final_audio": "final_audio_review",
        "final_video": "final_video_review",
    }[approval.stage]
    latest_version = max(
        (item["version"] for item in book["artifacts"] if item["stage"] == artifact_stage),
        default=None,
    )
    advanced = store.approve_if_current(
        book_id, current_stage, current_status, next_stage, next_status,
        approval.stage, "user", approval.note, latest_version,
    )
    if not advanced:
        latest_book = store.get_book(book_id)
        return {
            "id": book_id,
            "current_stage": latest_book["current_stage"],
            "status": latest_book["status"],
            "already_advanced": True,
            "job": None,
        }
    next_jobs = {
        "preview_video": "service.worker.render_preview_video",
        "full_audio": "service.worker.synthesize_full_audio",
        "full_video": "service.worker.render_full_video",
    }
    queued_job = _enqueue_job(book_id, next_stage, next_jobs[next_stage]) if next_stage in next_jobs else None
    return {"id": book_id, "current_stage": next_stage, "status": next_status, "job": queued_job}


@app.post("/api/books/{book_id}/jobs/{stage}")
def start_stage_job(book_id: str, stage: str) -> dict:
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    allowed = {
        "reference_preparation": (
            "reference_preparation", {"queue_unavailable", "failed"}, "service.worker.prepare_reference",
        ),
        "preview_audio": (
            "preview_audio", {"ready", "queue_unavailable", "failed"}, "service.worker.synthesize_preview_audio",
        ),
        "preview_audio_update": (
            "preview_audio_update", {"queue_unavailable", "failed"}, "service.worker.synthesize_preview_audio_update",
        ),
        "preview_video": (
            "preview_video", {"ready", "queue_unavailable", "failed"}, "service.worker.render_preview_video",
        ),
        "full_audio": (
            "full_audio", {"ready", "queue_unavailable", "failed"}, "service.worker.synthesize_full_audio",
        ),
        "full_audio_update": (
            "full_audio_update", {"queue_unavailable", "failed"}, "service.worker.synthesize_full_audio_update",
        ),
        "full_video": (
            "full_video", {"ready", "queue_unavailable", "failed"}, "service.worker.render_full_video",
        ),
    }
    if stage not in allowed:
        raise HTTPException(status_code=409, detail="This generation stage is not ready to start")
    expected_stage, statuses, task_name = allowed[stage]
    if book["current_stage"] != expected_stage or book["status"] not in statuses:
        raise HTTPException(status_code=409, detail="This generation stage is not ready to start")
    return _enqueue_job(book_id, stage, task_name)


@app.get("/api/artifacts/{artifact_id}")
def get_artifact(artifact_id: str) -> FileResponse:
    with store.connect() as db:
        row = db.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    artifact = dict(row)
    path = (store.service_home() / artifact["path"]).resolve()
    try:
        path.relative_to(store.service_home().resolve())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Artifact path is outside the service data directory") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file is missing")
    return FileResponse(path, media_type=artifact["mime_type"])