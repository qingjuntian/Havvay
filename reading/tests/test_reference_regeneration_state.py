import hashlib
from pathlib import Path

import service.app as app
import service.store as store


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_reference_input_is_not_invalidated_by_downstream_regeneration(tmp_path, monkeypatch):
    home = tmp_path / "service_home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("READING_SERVICE_HOME", str(home))
    monkeypatch.setenv("READING_SERVICE_DB", str(home / "service.sqlite3"))

    store.init_db()
    book_id = "book-1"
    store.create_book(book_id, "Demo Book")

    voice_path = home / "books" / book_id / "inputs" / "voice.wav"
    voice_path.parent.mkdir(parents=True, exist_ok=True)
    voice_path.write_bytes(b"voice-data")
    ref_text_path = home / "books" / book_id / "inputs" / "ref_text.txt"
    ref_text_path.write_text("hello world\n", encoding="utf-8")

    voice_art = store.add_artifact(
        book_id,
        "reference_input",
        "voice_sample",
        voice_path,
        _sha256(voice_path),
        "audio/wav",
        {"original_filename": "voice.wav"},
    )
    ref_art = store.add_artifact(
        book_id,
        "reference_input",
        "ref_text",
        ref_text_path,
        _sha256(ref_text_path),
        "text/plain; charset=utf-8",
        {"characters": 11},
    )

    processed = store.add_artifact(
        book_id,
        "reference_review",
        "processed_audio",
        home / "books" / book_id / "artifacts" / "reference" / "v1" / "reference.wav",
        "abc123",
        "audio/wav",
        {"job_id": "job-1"},
    )

    count = store.invalidate_reference_dependent_artifacts(book_id, "regeneration")
    assert count >= 1

    with store.connect() as db:
        invalidated_ids = {
            row["artifact_id"]
            for row in db.execute("SELECT artifact_id FROM invalidated_artifacts").fetchall()
        }

    assert voice_art["id"] not in invalidated_ids
    assert ref_art["id"] not in invalidated_ids
    assert processed["id"] in invalidated_ids


def test_regenerate_from_start_keeps_reference_and_requeues_audio_generation(tmp_path, monkeypatch):
    home = tmp_path / "service_home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("READING_SERVICE_HOME", str(home))
    monkeypatch.setenv("READING_SERVICE_DB", str(home / "service.sqlite3"))

    store.init_db()
    book_id = "book-2"
    store.create_book(book_id, "Regenerate Book")
    store.set_book_state(book_id, "full_audio", "ready")

    voice_path = home / "books" / book_id / "inputs" / "voice.wav"
    voice_path.parent.mkdir(parents=True, exist_ok=True)
    voice_path.write_bytes(b"voice-data")
    ref_text_path = home / "books" / book_id / "inputs" / "ref_text.txt"
    ref_text_path.write_text("hello world\n", encoding="utf-8")

    voice_art = store.add_artifact(
        book_id,
        "reference_input",
        "voice_sample",
        voice_path,
        _sha256(voice_path),
        "audio/wav",
        {"original_filename": "voice.wav"},
    )
    ref_art = store.add_artifact(
        book_id,
        "reference_input",
        "ref_text",
        ref_text_path,
        _sha256(ref_text_path),
        "text/plain; charset=utf-8",
        {"characters": 11},
    )
    audio_art = store.add_artifact(
        book_id,
        "final_audio_review",
        "audiobook_mp3",
        home / "books" / book_id / "artifacts" / "full_audio" / "v1" / "audiobook.mp3",
        "aaa111",
        "audio/mpeg",
        {"text_version": 1},
    )
    video_art = store.add_artifact(
        book_id,
        "final_video_review",
        "video_mp4",
        home / "books" / book_id / "artifacts" / "full_video" / "v1" / "reading.mp4",
        "bbb222",
        "video/mp4",
        {"preview": False},
    )

    calls = []

    def fake_enqueue(book_id_arg: str, stage: str, task_name: str):
        calls.append((book_id_arg, stage, task_name))
        return {"id": "job-queued", "status": "queued"}

    monkeypatch.setattr(app, "_enqueue_job", fake_enqueue)

    result = app.regenerate_book_from_start(book_id)

    assert result == {"id": "job-queued", "status": "queued"}
    assert calls == [(book_id, "full_audio_update", "service.worker.synthesize_full_audio_update")]

    with store.connect() as db:
        invalidated_ids = {
            row["artifact_id"]
            for row in db.execute("SELECT artifact_id FROM invalidated_artifacts").fetchall()
        }

    assert voice_art["id"] not in invalidated_ids
    assert ref_art["id"] not in invalidated_ids
    assert audio_art["id"] in invalidated_ids
    assert video_art["id"] in invalidated_ids
