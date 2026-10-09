"""RQ worker tasks for document preparation and later audio/video stages."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

from service import store

ROOT = Path(__file__).resolve().parents[1]
PAGE_BREAK_TOKEN = "<<<BOOK_PAGE_BREAK>>>"


def changed_chunk_numbers(previous_chunks: list[tuple[str, float]], current_chunks: list[tuple[str, float]]) -> list[int]:
    return [
        index + 1
        for index in range(max(len(previous_chunks), len(current_chunks)))
        if index >= len(previous_chunks)
        or index >= len(current_chunks)
        or previous_chunks[index] != current_chunks[index]
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _latest_artifact(book: dict, stage: str, kind: str) -> dict:
    matches = [item for item in book["artifacts"] if item["stage"] == stage and item["kind"] == kind]
    if not matches:
        raise FileNotFoundError(f"Missing {stage}/{kind} artifact for book {book['id']}")
    return max(matches, key=lambda item: item["version"])


def _artifact_path(artifact: dict) -> Path:
    path = (store.service_home() / artifact["path"]).resolve()
    path.relative_to(store.service_home().resolve())
    if not path.is_file():
        raise FileNotFoundError(f"Artifact file is missing: {path}")
    return path


def _run_stage(
    job_id: str,
    book_id: str,
    stage: str,
    output_dir: Path,
    commands: list[list[str]],
    outputs: list[tuple[str, Path, str, dict]],
    result_stage: str,
    result_status: str,
) -> str:
    log_path = output_dir / "run.log"
    output_dir.mkdir(parents=True, exist_ok=True)
    store.update_job(job_id, "running", progress=0.05)
    store.set_book_state(book_id, stage, "running")
    log_parts = []
    try:
        for index, command in enumerate(commands, 1):
            store.update_job(job_id, "running", progress=0.1 + 0.7 * index / len(commands))
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=7200)
            log_parts.append(
                "COMMAND: " + " ".join(command)
                + f"\nEXIT CODE: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
            if result.returncode:
                details = "\n".join(part for part in (result.stderr.strip(), result.stdout.strip()) if part)
                raise RuntimeError(f"Command exited with status {result.returncode}" + (f"\n{details}" if details else ""))
        missing = [str(path) for _, path, _, _ in outputs if not path.is_file()]
        if missing:
            raise FileNotFoundError("Expected stage output missing: " + ", ".join(missing))
        log_path.write_text("\n\n".join(log_parts), encoding="utf-8")
        for kind, path, mime_type, metadata in outputs:
            store.add_artifact(book_id, result_stage, kind, path, _sha256(path), mime_type, {"job_id": job_id, **metadata})
        store.add_artifact(book_id, result_stage, "log", log_path, _sha256(log_path), "text/plain; charset=utf-8", {"job_id": job_id})
        store.add_event(book_id, result_stage, "completed", note=f"Completed {stage}")
        store.set_book_state(book_id, result_stage, result_status)
        store.update_job(job_id, "completed", progress=1)
        return f"Completed {stage} for book {book_id}"
    except Exception as exc:
        log_parts.append(f"ERROR: {exc}")
        log_path.write_text("\n\n".join(log_parts), encoding="utf-8")
        store.add_artifact(book_id, stage, "log", log_path, _sha256(log_path), "text/plain; charset=utf-8", {"job_id": job_id})
        store.add_event(book_id, stage, "failed", note=str(exc))
        store.set_book_state(book_id, stage, "failed")
        store.update_job(job_id, "failed", error=str(exc))
        raise


def _approved_text_pages(book: dict) -> tuple[list[str], list[dict]]:
    text_artifact = _latest_artifact(book, "text", "normalized_text")
    pages_artifact = _latest_artifact(book, "pages", "page_metadata")
    text = _artifact_path(text_artifact).read_text(encoding="utf-8")
    records = json.loads(_artifact_path(pages_artifact).read_text(encoding="utf-8"))["pages"]
    text_pages = text.split(PAGE_BREAK_TOKEN)
    if len(text_pages) != len(records):
        raise ValueError(f"TTS text has {len(text_pages)} page sections but the document has {len(records)} pages")
    text_pages = [page.strip() for page in text_pages]
    if any(not page for page in text_pages):
        raise ValueError("Every page must contain TTS text")
    from src.text_normalize import match_text

    for page, page_text in zip(records, text_pages):
        page["text"] = page_text
        page["match_text"] = match_text(page_text)
    return text_pages, records


def _latest_page_image_artifacts(book: dict) -> dict[int, dict]:
    latest: dict[int, dict] = {}
    for artifact in book["artifacts"]:
        if artifact["stage"] != "pages" or artifact["kind"] != "page_image" or artifact.get("stale"):
            continue
        page_number = int(artifact["metadata"]["page"])
        current = latest.get(page_number)
        if current is None or artifact.get("metadata", {}).get("page_version", 1) > current.get("metadata", {}).get("page_version", 1):
            latest[page_number] = artifact
    return latest


def prepare_reference(job_id: str) -> str:
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"Unknown reference preparation job: {job_id}")
    book_id = job["book_id"]
    book = store.get_book(book_id)
    if book is None:
        raise ValueError(f"Unknown book: {book_id}")
    voice_path = _artifact_path(_latest_artifact(book, "reference_input", "voice_sample"))
    transcript_path = _artifact_path(_latest_artifact(book, "reference_input", "ref_text"))
    output_dir = store.book_directory(book_id) / "artifacts" / "reference" / job_id
    processed_audio = output_dir / "reference.wav"
    processed_text = output_dir / "reference.txt"
    command = [
        os.environ.get("READING_VIDEO_PYTHON", sys.executable), str(ROOT / "src/prepare_reference.py"),
        "--input", str(voice_path), "--output", str(processed_audio), "--text-output", str(processed_text),
        "--ref-text", transcript_path.read_text(encoding="utf-8").strip(),
    ]
    return _run_stage(
        job_id, book_id, "reference_preparation", output_dir, [command],
        [
            ("processed_audio", processed_audio, "audio/wav", {}),
            ("ref_text", processed_text, "text/plain; charset=utf-8", {}),
        ],
        "reference_review", "awaiting_reference_review",
    )


def _synthesize_audio(job_id: str, page_limit: int | None = None) -> str:
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"Unknown synthesis job: {job_id}")
    book_id = job["book_id"]
    book = store.get_book(book_id)
    if book is None:
        raise ValueError(f"Unknown book: {book_id}")
    stage = job["stage"]
    update_existing = stage.endswith("_update")
    audio_kind = stage.removesuffix("_update")
    if audio_kind not in {"preview_audio", "full_audio"}:
        raise ValueError(f"Unsupported audio synthesis stage: {stage}")
    text_pages, page_records = _approved_text_pages(book)
    if page_limit is not None:
        text_pages = text_pages[:page_limit]
        page_records = page_records[:page_limit]

    output_dir = store.book_directory(book_id) / "artifacts" / audio_kind / job_id
    f5_dir = output_dir / "f5"
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    image_artifacts = _latest_page_image_artifacts(book)
    required_page_numbers = set(range(1, len(page_records) + 1))
    if not required_page_numbers.issubset(image_artifacts):
        raise ValueError("Page image files do not match the approved text pages")
    for page_number in sorted(required_page_numbers):
        artifact = image_artifacts[page_number]
        image_path = _artifact_path(artifact)
        shutil.copy2(image_path, pages_dir / f"page_{page_number:04d}.png")

    text_path = output_dir / "book.txt"
    text_path.write_text((f"\n\n{PAGE_BREAK_TOKEN}\n\n".join(text_pages)) + "\n", encoding="utf-8")
    pages_path = output_dir / "book_pages.json"
    pages_path.write_text(
        json.dumps({"pages": page_records}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    reference_audio = _artifact_path(_latest_artifact(book, "reference_review", "processed_audio"))
    reference_text = _artifact_path(_latest_artifact(book, "reference_review", "ref_text"))
    audio_path = f5_dir / "audiobook.mp3"
    wav_path = f5_dir / "audiobook.wav"
    f5_python = os.environ.get("READING_F5_PYTHON", sys.executable)
    max_chars = int(os.environ.get("READING_F5_MAX_CHARS", "100"))
    rerender_chunks: list[int] = []
    if update_existing:
        review_stage = "final_audio_review" if audio_kind == "full_audio" else "preview_audio_review"
        source_audio = _latest_artifact(book, review_stage, "audiobook_mp3")
        source_chunks_dir = _artifact_path(source_audio).parent / "chunks"
        destination_chunks_dir = f5_dir / "chunks"
        destination_chunks_dir.mkdir(parents=True, exist_ok=True)
        if source_chunks_dir.is_dir():
            for source_chunk in source_chunks_dir.glob("chunk_*"):
                shutil.copy2(source_chunk, destination_chunks_dir / source_chunk.name)

        text_artifacts = sorted(
            (item for item in book["artifacts"] if item["stage"] == "text" and item["kind"] == "normalized_text"),
            key=lambda item: item["version"],
        )
        current_text_version = text_artifacts[-1]["version"] if text_artifacts else 0
        previous_text_artifact = next(
            (item for item in reversed(text_artifacts) if item["version"] < current_text_version),
            None,
        )
        from src import narrate_book_f5 as f5_script

        f5_script.MAX_CHARS = max_chars
        current_pages = text_path.read_text(encoding="utf-8").split(PAGE_BREAK_TOKEN)
        if page_limit is not None:
            current_pages = current_pages[:page_limit]
        current_chunks = f5_script.build_chunks(f"\n\n{PAGE_BREAK_TOKEN}\n\n".join(current_pages))
        if previous_text_artifact is None:
            rerender_chunks = list(range(1, len(current_chunks) + 1))
        else:
            previous_text = _artifact_path(previous_text_artifact).read_text(encoding="utf-8")
            previous_pages = previous_text.split(PAGE_BREAK_TOKEN)
            if page_limit is not None:
                previous_pages = previous_pages[:page_limit]
            previous_chunks = f5_script.build_chunks(f"\n\n{PAGE_BREAK_TOKEN}\n\n".join(previous_pages))
            rerender_chunks = changed_chunk_numbers(previous_chunks, current_chunks)

    command = [
        f5_python, str(ROOT / "src/narrate_book_f5.py"),
        "--book", str(text_path), "--reference-audio", str(reference_audio),
        "--reference-text-file", str(reference_text), "--output-dir", str(f5_dir),
        "--speed", os.environ.get("READING_F5_SPEED", "1.2"),
        "--nfe-step", os.environ.get("READING_F5_NFE_STEP", "32"),
        "--max-chars", str(max_chars),
        "--test-limit", "0",
    ]
    if rerender_chunks:
        command += ["--rerender-chunks", ",".join(map(str, rerender_chunks))]
    resulting_stage, resulting_status = (
        ("preview_audio_review", "awaiting_preview_audio_review")
        if audio_kind == "preview_audio"
        else ("final_audio_review", "awaiting_final_audio_review")
    )
    return _run_stage(
        job_id, book_id, stage, output_dir, [command],
        [
            ("audiobook_mp3", audio_path, "audio/mpeg", {"page_count": len(page_records), "text_version": current_text_version if update_existing else text_artifact_version(book)}),
            ("audiobook_wav", wav_path, "audio/wav", {"page_count": len(page_records), "text_version": current_text_version if update_existing else text_artifact_version(book)}),
            ("page_metadata", pages_path, "application/json", {"page_count": len(page_records), "text_version": current_text_version if update_existing else text_artifact_version(book)}),
        ],
        resulting_stage, resulting_status,
    )


def text_artifact_version(book: dict) -> int | None:
    artifacts = [
        item["version"] for item in book["artifacts"]
        if item["stage"] == "text" and item["kind"] == "normalized_text"
    ]
    return max(artifacts, default=None)


def synthesize_preview_audio(job_id: str) -> str:
    return _synthesize_audio(job_id, page_limit=5)


def synthesize_full_audio(job_id: str) -> str:
    return _synthesize_audio(job_id)


def synthesize_preview_audio_update(job_id: str) -> str:
    return _synthesize_audio(job_id, page_limit=5)


def synthesize_full_audio_update(job_id: str) -> str:
    return _synthesize_audio(job_id)


def _render_video(job_id: str, preview: bool) -> str:
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"Unknown video job: {job_id}")
    book_id = job["book_id"]
    book = store.get_book(book_id)
    if book is None:
        raise ValueError(f"Unknown book: {book_id}")
    audio_stage = "preview_audio_review" if preview else "final_audio_review"
    audio_path = _artifact_path(_latest_artifact(book, audio_stage, "audiobook_mp3"))
    audio_root = audio_path.parent.parent
    output_dir = store.book_directory(book_id) / "artifacts" / job["stage"] / job_id
    timings_path = output_dir / "page_timings.json"
    video_path = output_dir / ("preview.mp4" if preview else "reading.mp4")
    pdf_path = _artifact_path(_latest_artifact(book, "pages", "rendered_pdf"))
    video_python = os.environ.get("READING_VIDEO_PYTHON", sys.executable)
    images_dir = output_dir / "pages"
    images_dir.mkdir(parents=True, exist_ok=True)
    latest_page_images: dict[int, dict] = {}
    for artifact in book["artifacts"]:
        if artifact["stage"] != "pages" or artifact["kind"] != "page_image" or artifact.get("stale"):
            continue
        page_number = int(artifact["metadata"]["page"])
        current = latest_page_images.get(page_number)
        if current is None or artifact["version"] > current["version"]:
            latest_page_images[page_number] = artifact
    page_records = json.loads(_artifact_path(_latest_artifact(book, audio_stage, "page_metadata")).read_text(encoding="utf-8"))["pages"]
    expected_pages = len(page_records)
    required_page_numbers = set(range(1, expected_pages + 1))
    if not required_page_numbers.issubset(latest_page_images):
        raise ValueError("Current page images do not match the audio page metadata")
    for page_number in sorted(required_page_numbers):
        artifact = latest_page_images[page_number]
        image_path = _artifact_path(artifact)
        shutil.copy2(image_path, images_dir / f"page_{page_number:04d}.png")
    commands = [
        [
            video_python, str(ROOT / "src/page_timings.py"), "--pdf", str(pdf_path),
            "--pages-json", str(audio_root / "book_pages.json"),
            "--chunks-dir", str(audio_root / "f5/chunks"), "--output", str(timings_path),
        ],
        [
            video_python, str(ROOT / "src/book_video.py"), "--audio", str(audio_path),
            "--images-dir", str(images_dir), "--timings", str(timings_path),
            "--width", "720", "--height", "1280", "--fps", "24", "--transition", "0.8",
            "--output", str(video_path),
        ],
    ]
    result_stage, result_status = (
        ("preview_video_review", "awaiting_preview_video_review")
        if preview
        else ("final_video_review", "awaiting_final_video_review")
    )
    return _run_stage(
        job_id, book_id, job["stage"], output_dir, commands,
        [
            ("page_timings", timings_path, "application/json", {"preview": preview}),
            ("video_mp4", video_path, "video/mp4", {"preview": preview}),
        ],
        result_stage, result_status,
    )


def render_preview_video(job_id: str) -> str:
    return _render_video(job_id, preview=True)


def render_full_video(job_id: str) -> str:
    return _render_video(job_id, preview=False)


def prepare_document(job_id: str) -> str:
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"Unknown document preparation job: {job_id}")
    book_id = job["book_id"]
    book = store.get_book(book_id)
    if book is None:
        raise ValueError(f"Unknown book: {book_id}")

    output_dir = store.book_directory(book_id) / "artifacts" / "document" / job_id
    images_dir = output_dir / "pages"
    pdf_path = output_dir / "rendered" / "book.pdf"
    text_path = output_dir / "book.txt"
    pages_path = output_dir / "book_pages.json"
    checklist_path = output_dir / "book_checklist.json"
    log_path = output_dir / "prepare.log"
    input_path = store.book_directory(book_id) / "inputs" / "original.pdf"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, pdf_path)

    store.update_job(job_id, "running", progress=0.05)
    store.set_book_state(book_id, "document", "preparing")
    command = [
        os.environ.get("READING_VIDEO_PYTHON", sys.executable),
        str(ROOT / "src/prepare_book.py"),
        "--pdf", str(pdf_path),
        "--images-dir", str(images_dir),
        "--text-output", str(text_path),
        "--pages-output", str(pages_path),
    ]
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=3600)
        log_path.write_text(
            "COMMAND: " + " ".join(command) + "\n\n" + result.stdout + "\n" + result.stderr,
            encoding="utf-8",
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}")

        store.update_job(job_id, "running", progress=0.8)
        metadata = {"job_id": job_id}
        store.add_artifact(book_id, "pages", "rendered_pdf", pdf_path, _sha256(pdf_path), "application/pdf", metadata)
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, _sha256(pages_path), "application/json", metadata)
        store.add_artifact(book_id, "pages", "checklist", checklist_path, _sha256(checklist_path), "application/json", metadata)
        store.add_artifact(book_id, "text", "normalized_text", text_path, _sha256(text_path), "text/plain; charset=utf-8", metadata)
        for image_path in sorted(images_dir.glob("page_*.png")):
            page_number = int(image_path.stem.split("_")[-1])
            store.add_artifact(
                book_id, "pages", "page_image", image_path, _sha256(image_path),
                mimetypes.guess_type(image_path.name)[0] or "image/png",
                {**metadata, "page": page_number},
            )
        store.add_artifact(book_id, "document", "log", log_path, _sha256(log_path), "text/plain; charset=utf-8", metadata)
        store.add_event(book_id, "pages", "prepared", note=f"Rendered {len(list(images_dir.glob('page_*.png')))} pages")
        store.set_book_state(book_id, "pages_review", "awaiting_page_review")
        store.update_job(job_id, "completed", progress=1)
        return f"Prepared document for book {book_id}"
    except Exception as exc:
        if not log_path.exists():
            log_path.write_text(str(exc), encoding="utf-8")
        store.add_artifact(book_id, "document", "log", log_path, _sha256(log_path), "text/plain; charset=utf-8", {"job_id": job_id})
        store.add_event(book_id, "document", "failed", note=str(exc))
        store.set_book_state(book_id, "document", "failed")
        store.update_job(job_id, "failed", error=str(exc))
        raise