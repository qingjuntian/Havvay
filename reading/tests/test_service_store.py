from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from service import store


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
        source_file = book_path / "inputs" / "original.docx"
        source_file.parent.mkdir(parents=True)
        source_file.write_bytes(b"test docx")
        artifact_path = book_path / "artifacts" / "preview.mp4"
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_bytes(b"test video")
        store.add_artifact(
            self.book_id, "input", "docx", source_file, "source-hash", "application/docx"
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
        source_file = book_path / "inputs" / "original.docx"
        source_file.parent.mkdir(parents=True)
        source_file.write_bytes(b"keep this file")
        store.create_job(str(uuid.uuid4()), self.book_id, "prepare_document")

        result = store.delete_book(self.book_id)

        self.assertEqual(result, "active_jobs")
        self.assertTrue(source_file.is_file())
        self.assertIsNotNone(store.get_book(self.book_id))


if __name__ == "__main__":
    unittest.main()