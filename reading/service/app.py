"""FastAPI entry point for the audiobook preparation and review service."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from service import store

MAX_UPLOAD_BYTES = int(os.environ.get("READING_MAX_UPLOAD_BYTES", str(200 * 1024 * 1024)))
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
        timeout = 86400 if stage in {"preview_audio", "full_audio", "preview_video", "full_video"} else 7200
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
async def create_book(docx: UploadFile = File(...), title: str = Form(default="")) -> dict:
    filename = Path(docx.filename or "book.docx").name
    if Path(filename).suffix.lower() != ".docx":
        raise HTTPException(status_code=415, detail="Upload a .docx document")

    book_id = str(uuid.uuid4())
    book_root = store.book_directory(book_id)
    input_path = book_root / "inputs" / "original.docx"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with input_path.open("wb") as target:
            while block := await docx.read(1024 * 1024):
                written += len(block)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="DOCX exceeds the configured upload limit")
                target.write(block)
    except Exception:
        input_path.unlink(missing_ok=True)
        raise
    finally:
        await docx.close()

    if written == 0:
        input_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded DOCX is empty")

    book_title = title.strip() or Path(filename).stem or "Untitled book"
    store.create_book(book_id, book_title)
    store.add_artifact(
        book_id, "input", "docx", input_path, _sha256(input_path),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
    if book["current_stage"] != "text_review" or book["status"] != "awaiting_text_review":
        raise HTTPException(status_code=409, detail="Text is locked after approval; reopen text review before editing")
    if not update.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(update.text) > 2_000_000:
        raise HTTPException(status_code=413, detail="Text exceeds the 2 MB limit")
    page_artifacts = [
        item for item in book["artifacts"] if item["stage"] == "pages" and item["kind"] == "page_metadata"
    ]
    if page_artifacts:
        latest_pages = max(page_artifacts, key=lambda item: item["version"])
        metadata_path = (store.service_home() / latest_pages["path"]).resolve()
        page_count = len(json.loads(metadata_path.read_text(encoding="utf-8"))["pages"])
        if update.text.count("<<<BOOK_PAGE_BREAK>>>") != page_count - 1:
            raise HTTPException(status_code=400, detail=f"Text must keep exactly {page_count - 1} page-break markers")

    versions = [
        item["version"] for item in book["artifacts"]
        if item["stage"] == "text" and item["kind"] == "normalized_text"
    ]
    version = max(versions, default=0) + 1
    output_path = store.book_directory(book_id) / "artifacts" / "text" / f"v{version}" / "book.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(update.text, encoding="utf-8")
    artifact = store.add_artifact(
        book_id, "text", "normalized_text", output_path, _sha256(output_path), "text/plain; charset=utf-8",
        {"edited_by_user": True},
    )
    store.set_book_state(book_id, "text_review", "awaiting_text_review")
    store.add_event(book_id, "text", "text_edited", "user", "Normalized TTS text updated", version)
    store.add_event(book_id, "text", "downstream_invalidated", "system", "Text changed; later approvals must be repeated", version)
    return artifact


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
        "preview_video": (
            "preview_video", {"queue_unavailable", "failed"}, "service.worker.render_preview_video",
        ),
        "full_audio": (
            "full_audio", {"ready", "queue_unavailable", "failed"}, "service.worker.synthesize_full_audio",
        ),
        "full_video": (
            "full_video", {"queue_unavailable", "failed"}, "service.worker.render_full_video",
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