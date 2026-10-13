from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from service import store
from service.worker import changed_chunk_numbers


class ServiceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(
            os.environ,
            {"READING_SERVICE_HOME": self.temporary_directory.name},
        )
        self.environment.start()
        store.init_db()
        self.book_id = str(uuid.uuid4())
        store.create_book(self.book_id, "测试书籍")

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_artifact_versions_jobs_and_events_round_trip(self) -> None:
        artifact_path = store.book_directory(self.book_id) / "artifacts" / "text" / "book.txt"
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_text("二零一二年\n", encoding="utf-8")
        first = store.add_artifact(
            self.book_id, "text", "normalized_text", artifact_path, "digest-1", "text/plain", {"edited": False}
        )
        second = store.add_artifact(
            self.book_id, "text", "normalized_text", artifact_path, "digest-2", "text/plain", {"edited": True}
        )
        job_id = str(uuid.uuid4())
        store.create_job(job_id, self.book_id, "prepare_document")
        store.update_job(job_id, "running", progress=0.5, queue_id="rq-123")
        store.add_event(self.book_id, "text", "approved", "reviewer", "Looks good", second["version"])

        book = store.get_book(self.book_id)

        self.assertIsNotNone(book)
        assert book is not None
        self.assertEqual([first["version"], second["version"]], [1, 2])
        self.assertEqual(book["artifacts"][1]["metadata"], {"edited": True})
        self.assertEqual(book["jobs"][0]["status"], "running")
        self.assertEqual(book["jobs"][0]["queue_id"], "rq-123")
        self.assertEqual(book["events"][-1]["event_type"], "approved")
        self.assertEqual(store.list_books()[0]["id"], self.book_id)

    def test_approval_transition_is_idempotent(self) -> None:
        store.set_book_state(self.book_id, "preview_audio_review", "awaiting_preview_audio_review")

        first = store.approve_if_current(
            self.book_id,
            "preview_audio_review",
            "awaiting_preview_audio_review",
            "preview_video",
            "queued",
            "preview_audio",
            "reviewer",
            "approved",
            1,
        )
        second = store.approve_if_current(
            self.book_id,
            "preview_audio_review",
            "awaiting_preview_audio_review",
            "preview_video",
            "queued",
            "preview_audio",
            "reviewer",
            "duplicate click",
            1,
        )

        book = store.get_book(self.book_id)
        self.assertTrue(first)
        self.assertFalse(second)
        assert book is not None
        approvals = [event for event in book["events"] if event["event_type"] == "approved"]
        self.assertEqual(len(approvals), 1)
        self.assertEqual((book["current_stage"], book["status"]), ("preview_video", "queued"))

    def test_create_book_initializes_schema_when_db_is_empty(self) -> None:
        empty_db = Path(self.temporary_directory.name) / "empty.sqlite3"
        with patch.dict(os.environ, {"READING_SERVICE_DB": str(empty_db)}, clear=False):
            self.assertFalse(empty_db.exists())
            empty_db.parent.mkdir(parents=True, exist_ok=True)
            empty_db.write_bytes(b"")

            store.create_book("auto-init-book", "数据库未初始化时仍可创建")

            with store.connect() as db:
                self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'books'").fetchone()[0], "books")

    def test_book_text_stats_count_latest_tts_text_without_page_markers_or_whitespace(self) -> None:
        artifact_path = store.book_directory(self.book_id) / "artifacts" / "text" / "book.txt"
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_text("甲，乙。\n<<<BOOK_PAGE_BREAK>>>\n丙! \n", encoding="utf-8")
        store.add_artifact(
            self.book_id, "text", "normalized_text", artifact_path, "digest", "text/plain", {}
        )

        book = store.get_book(self.book_id)
        listed_book = store.list_books()[0]

        assert book is not None
        self.assertEqual(book["text_char_count"], 6)
        self.assertEqual(book["page_count"], 2)
        self.assertEqual(book["text_version"], 1)
        self.assertEqual(listed_book["text_char_count"], 6)
        self.assertEqual(listed_book["page_count"], 2)

    def test_delete_book_removes_its_records_and_files(self) -> None:
        book_path = store.book_directory(self.book_id)
        source_file = book_path / "inputs" / "original.pdf"
        source_file.parent.mkdir(parents=True)
        source_file.write_bytes(b"%PDF-test")
        artifact_path = book_path / "artifacts" / "preview.mp4"
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_bytes(b"test video")
        store.add_artifact(
            self.book_id, "input", "source_pdf", source_file, "source-hash", "application/pdf"
        )
        store.add_artifact(
            self.book_id, "preview", "video", artifact_path, "video-hash", "video/mp4"
        )
        store.add_event(self.book_id, "pages", "approved", "reviewer", "Confirmed")
        other_book_id = str(uuid.uuid4())
        store.create_book(other_book_id, "另一本文档")

        result = store.delete_book(self.book_id)

        self.assertEqual(result, "deleted")
        self.assertFalse(book_path.exists())
        self.assertIsNone(store.get_book(self.book_id))
        self.assertEqual([book["id"] for book in store.list_books()], [other_book_id])
        with store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM artifacts WHERE book_id = ?", (self.book_id,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE book_id = ?", (self.book_id,)).fetchone()[0], 0)

    def test_delete_book_refuses_queued_or_running_jobs(self) -> None:
        book_path = store.book_directory(self.book_id)
        source_file = book_path / "inputs" / "original.pdf"
        source_file.parent.mkdir(parents=True)
        source_file.write_bytes(b"keep this file")
        store.create_job(str(uuid.uuid4()), self.book_id, "prepare_document")

        result = store.delete_book(self.book_id)

        self.assertEqual(result, "active_jobs")
        self.assertTrue(source_file.is_file())
        self.assertIsNotNone(store.get_book(self.book_id))

    def test_image_change_invalidates_videos_but_preserves_audio(self) -> None:
        artifact_dir = store.book_directory(self.book_id) / "artifacts"
        artifact_dir.mkdir(parents=True)
        artifacts = [
            ("preview_audio_review", "audiobook_mp3", "preview.mp3"),
            ("preview_video_review", "video_mp4", "preview.mp4"),
            ("preview_video_review", "page_timings", "preview.json"),
            ("final_audio_review", "audiobook_mp3", "final.mp3"),
            ("final_video_review", "video_mp4", "final.mp4"),
        ]
        for stage, kind, filename in artifacts:
            path = artifact_dir / filename
            path.write_bytes(b"artifact")
            store.add_artifact(self.book_id, stage, kind, path, filename, "application/octet-stream")

        invalidated = store.invalidate_video_artifacts(self.book_id, "Page image replaced")
        book = store.get_book(self.book_id)
        assert book is not None
        by_kind = {(item["stage"], item["kind"]): item for item in book["artifacts"]}

        self.assertEqual(invalidated, 3)
        self.assertFalse(by_kind[("preview_audio_review", "audiobook_mp3")]["stale"])
        self.assertTrue(by_kind[("preview_video_review", "video_mp4")]["stale"])
        self.assertTrue(by_kind[("preview_video_review", "page_timings")]["stale"])
        self.assertFalse(by_kind[("final_audio_review", "audiobook_mp3")]["stale"])
        self.assertTrue(by_kind[("final_video_review", "video_mp4")]["stale"])

    def test_text_change_invalidates_audio_and_video_but_preserves_inputs(self) -> None:
        artifact_dir = store.book_directory(self.book_id) / "artifacts"
        artifact_dir.mkdir(parents=True)
        artifacts = [
            ("pages", "page_image", "page.png"),
            ("reference_review", "processed_audio", "reference.wav"),
            ("preview_audio_review", "audiobook_mp3", "preview.mp3"),
            ("preview_audio_review", "audiobook_wav", "preview.wav"),
            ("preview_video_review", "video_mp4", "preview.mp4"),
            ("final_audio_review", "audiobook_mp3", "full.mp3"),
            ("final_video_review", "video_mp4", "full.mp4"),
        ]
        for stage, kind, filename in artifacts:
            path = artifact_dir / filename
            path.write_bytes(b"artifact")
            store.add_artifact(self.book_id, stage, kind, path, filename, "application/octet-stream")

        invalidated = store.invalidate_text_dependent_artifacts(self.book_id, "Text edited")
        book = store.get_book(self.book_id)
        assert book is not None
        by_kind = {(item["stage"], item["kind"]): item for item in book["artifacts"]}

        self.assertEqual(invalidated, 5)
        self.assertFalse(by_kind[("pages", "page_image")]["stale"])
        self.assertFalse(by_kind[("reference_review", "processed_audio")]["stale"])
        self.assertTrue(by_kind[("preview_audio_review", "audiobook_mp3")]["stale"])
        self.assertTrue(by_kind[("preview_audio_review", "audiobook_wav")]["stale"])
        self.assertTrue(by_kind[("preview_video_review", "video_mp4")]["stale"])
        self.assertTrue(by_kind[("final_audio_review", "audiobook_mp3")]["stale"])
        self.assertTrue(by_kind[("final_video_review", "video_mp4")]["stale"])

    def test_voice_reference_replacement_invalidates_reference_and_all_downstream_media(self) -> None:
        artifact_dir = store.book_directory(self.book_id) / "artifacts"
        artifact_dir.mkdir(parents=True)
        artifacts = [
            ("reference_input", "voice_sample", "voice.wav"),
            ("reference_input", "ref_text", "ref.txt"),
            ("reference_review", "processed_audio", "processed.wav"),
            ("preview_audio_review", "audiobook_mp3", "preview.mp3"),
            ("preview_video_review", "video_mp4", "preview.mp4"),
            ("final_audio_review", "audiobook_mp3", "final.mp3"),
            ("final_video_review", "video_mp4", "final.mp4"),
            ("text", "normalized_text", "book.txt"),
        ]
        for stage, kind, filename in artifacts:
            path = artifact_dir / filename
            path.write_bytes(b"artifact")
            store.add_artifact(self.book_id, stage, kind, path, filename, "application/octet-stream")

        source_invalidated = store.invalidate_reference_input_artifacts(self.book_id, "Voice reference replaced")
        downstream_invalidated = store.invalidate_reference_dependent_artifacts(self.book_id, "Voice reference replaced")
        book = store.get_book(self.book_id)
        assert book is not None
        by_kind = {(item["stage"], item["kind"]): item for item in book["artifacts"]}

        self.assertEqual(source_invalidated, 2)
        self.assertEqual(downstream_invalidated, 5)
        self.assertTrue(by_kind[("reference_input", "voice_sample")]["stale"])
        self.assertTrue(by_kind[("reference_review", "processed_audio")]["stale"])
        self.assertTrue(by_kind[("preview_audio_review", "audiobook_mp3")]["stale"])
        self.assertTrue(by_kind[("preview_video_review", "video_mp4")]["stale"])
        self.assertTrue(by_kind[("final_audio_review", "audiobook_mp3")]["stale"])
        self.assertTrue(by_kind[("final_video_review", "video_mp4")]["stale"])
        self.assertFalse(by_kind[("text", "normalized_text")]["stale"])

    def test_changed_chunk_numbers_only_selects_changed_text_or_pause(self) -> None:
        previous = [("unchanged", 0.3), ("edited", 0.3), ("same text", 0.3)]
        current = [("unchanged", 0.3), ("edited version", 0.3), ("same text", 0.6), ("new", 0.3)]

        self.assertEqual(changed_chunk_numbers(previous, current), [2, 3, 4])
        self.assertEqual(changed_chunk_numbers(previous[:1], previous[:1]), [])


if __name__ == "__main__":
    unittest.main()