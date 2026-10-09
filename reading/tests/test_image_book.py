from __future__ import annotations

import asyncio
import io
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from service import store
from service.app import (
    create_image_book,
    create_image_book_draft,
    prepare_document_again,
    TextUpdate,
    update_text,
    upload_image_book_pages,
)
from service.worker import prepare_image_book as prepare_image_book_job
from src.prepare_image_book import prepare_image_book
from src.page_timings import build_timings, page_texts


def image_upload(filename: str, color: tuple[int, int, int]) -> UploadFile:
    stream = io.BytesIO()
    Image.new("RGB", (32, 48), color).save(stream, format="PNG")
    stream.seek(0)
    return UploadFile(filename=filename, file=stream, headers={"content-type": "image/png"})


class ImageBookPreparationTests(unittest.TestCase):
    def test_prepares_one_image_and_tts_page_per_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_images = root / "inputs"
            source_images.mkdir()
            Image.new("RGB", (32, 48), "red").save(source_images / "page_0001.png")
            Image.new("RGB", (48, 32), "blue").save(source_images / "page_0002.png")
            submitted_texts = [
                {"filename": "painting_1.png", "text": "2012年开始创作。"},
                {"filename": "photo_2.png", "text": "这是一张旅行照片。"},
            ]
            text_source = root / "page_texts.json"
            text_source.write_text(json.dumps(submitted_texts, ensure_ascii=False), encoding="utf-8")

            page_records = prepare_image_book(
                source_images, text_source, root / "artifacts", root / "book.txt", root / "book_pages.json"
            )
            book_text = (root / "book.txt").read_text(encoding="utf-8")
            metadata = json.loads((root / "book_pages.json").read_text(encoding="utf-8"))

            self.assertEqual(len(page_records), 2)
            self.assertEqual([page["source_image"] for page in metadata["pages"]], ["painting_1.png", "photo_2.png"])
            self.assertEqual([page["text"] for page in metadata["pages"]], ["二零一二年开始创作。", "这是一张旅行照片。"])
            self.assertEqual(book_text.count("<<<BOOK_PAGE_BREAK>>>"), 1)
            self.assertTrue((root / "artifacts/pages/page_0001.png").is_file())
            self.assertTrue((root / "artifacts/pages/page_0002.png").is_file())

    def test_page_timing_reads_image_book_metadata_without_a_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            pages_path = Path(temporary_directory) / "book_pages.json"
            pages_path.write_text(json.dumps({"pages": [
                {"match_text": "第一页"},
                {"match_text": "第二页"},
            ]}, ensure_ascii=False), encoding="utf-8")

            self.assertEqual(page_texts(None, pages_path), ["第一页", "第二页"])

    def test_page_timings_can_be_built_from_image_book_metadata_without_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = "第一张图"
            second = "第二张图"
            pages_path = root / "book_pages.json"
            pages_path.write_text(json.dumps({"pages": [
                {"match_text": first},
                {"match_text": second},
            ]}, ensure_ascii=False), encoding="utf-8")
            chunks = [
                {"name": "chunk_00001", "text_length": len(first), "start": 0, "end": len(first), "duration": 1.5},
                {"name": "chunk_00002", "text_length": len(second), "start": len(first), "end": len(first) + len(second), "duration": 2.0},
            ]
            with patch("src.page_timings.chunk_data", return_value=(chunks, first + second)):
                timings = build_timings(None, root / "chunks", pages_path)

            self.assertIsNone(timings["pdf"])
            self.assertEqual([page["duration"] for page in timings["pages"]], [1.5, 2.0])


class ImageBookUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"READING_SERVICE_HOME": self.temporary_directory.name})
        self.environment.start()
        store.init_db()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_image_book_upload_creates_input_artifacts_and_queues_preparation(self) -> None:
        job = {"id": str(uuid.uuid4()), "status": "queued"}
        with patch("service.app._enqueue_job", return_value=job):
            result = asyncio.run(create_image_book(
                images=[image_upload("painting_1.png", (200, 20, 20)), image_upload("photo_2.png", (10, 20, 200))],
                page_texts=json.dumps(["第一段文字。", "第二段文字。"]),
                title="画册测试",
            ))

        book = store.get_book(result["id"])
        assert book is not None
        source_images = [item for item in book["artifacts"] if item["kind"] == "source_image"]
        source_texts = [item for item in book["artifacts"] if item["kind"] == "source_page_texts"]
        self.assertEqual(result["page_count"], 2)
        self.assertEqual(len(source_images), 2)
        self.assertEqual(len(source_texts), 1)
        self.assertTrue(all(item["mime_type"] == "image/png" for item in source_images))
        self.assertTrue((store.book_directory(result["id"]) / "inputs/pages/page_0001.png").is_file())

    def test_create_draft_then_upload_pages(self) -> None:
        draft = create_image_book_draft("逐页添加测试")
        draft_book = store.get_book(draft["id"])
        assert draft_book is not None
        self.assertEqual((draft_book["current_stage"], draft_book["status"]), ("document", "awaiting_image_pages"))
        with patch("service.app._enqueue_job", return_value={"id": "job-after-pages", "status": "queued"}) as enqueue:
            result = asyncio.run(upload_image_book_pages(
                draft["id"],
                [image_upload("painting_1.png", (200, 20, 20)), image_upload("painting_2.png", (10, 20, 200))],
                json.dumps(["第一页的朗读内容。", "第二页的朗读内容。"]),
            ))

        self.assertEqual(result["id"], draft["id"])
        self.assertEqual(result["page_count"], 2)
        enqueue.assert_called_once_with(draft["id"], "document", "service.worker.prepare_image_book")

    def test_append_pages_after_initial_review_preserves_text_and_updates_page_count(self) -> None:
        initial = create_image_book_draft("追加页面测试")
        initial_job = {"id": str(uuid.uuid4()), "status": "queued"}
        with patch("service.app._enqueue_job", return_value=initial_job):
            asyncio.run(upload_image_book_pages(
                initial["id"], [image_upload("painting_1.png", (180, 40, 20))], json.dumps(["已有页面内容。"])
            ))
        prepare_job_id = str(uuid.uuid4())
        store.create_job(prepare_job_id, initial["id"], "document")
        prepare_image_book_job(prepare_job_id)
        update_text(initial["id"], TextUpdate(text="人工修订后的旧页文本。"))

        book = store.get_book(initial["id"])
        assert book is not None
        text_artifact = next(item for item in book["artifacts"] if item["stage"] == "text" and item["kind"] == "normalized_text")
        text_path = store.service_home() / text_artifact["path"]
        original_text = text_path.read_text(encoding="utf-8")
        first_page_breaks = original_text.count(store.PAGE_BREAK_TOKEN)
        audio_path = store.book_directory(initial["id"]) / "artifacts/final/audiobook.mp3"
        audio_path.parent.mkdir(parents=True)
        audio_path.write_bytes(b"existing audio")
        store.add_artifact(
            initial["id"], "final_audio_review", "audiobook_mp3", audio_path,
            "audio-digest", "audio/mpeg", {"page_count": 1},
        )
        store.set_book_state(initial["id"], "reference", "awaiting_reference")

        with patch("service.app._enqueue_job", return_value={"id": "audio-update", "status": "queued"}) as enqueue:
            result = asyncio.run(upload_image_book_pages(
                initial["id"], [image_upload("painting_2.png", (20, 40, 180))], json.dumps(["追加的新页面内容。"])
            ))

        updated = store.get_book(initial["id"])
        assert updated is not None
        current_text = max(
            (item for item in updated["artifacts"] if item["stage"] == "text" and item["kind"] == "normalized_text"),
            key=lambda item: item["version"],
        )
        updated_text = (store.service_home() / current_text["path"]).read_text(encoding="utf-8")
        latest_pages = max(
            (item for item in updated["artifacts"] if item["stage"] == "pages" and item["kind"] == "page_metadata"),
            key=lambda item: item["version"],
        )
        page_payload = json.loads((store.service_home() / latest_pages["path"]).read_text(encoding="utf-8"))
        self.assertIn("人工修订后的旧页文本。", updated_text)
        self.assertNotIn("已有页面内容。", updated_text)
        self.assertIn("追加的新页面内容。", updated_text)
        self.assertEqual(updated_text.count(store.PAGE_BREAK_TOKEN), first_page_breaks + 1)
        self.assertEqual(len(page_payload["pages"]), 2)
        self.assertEqual(result["appended_page_count"], 1)
        enqueue.assert_called_once_with(
            initial["id"], "full_audio_update", "service.worker.synthesize_full_audio_update"
        )
        self.assertEqual(result["text_update"]["regeneration"]["status"], "queued")

    def test_append_pages_rejects_non_image_books(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "普通 PDF 书")
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(upload_image_book_pages(
                book_id, [image_upload("page.png", (120, 80, 20))], json.dumps(["新增内容。"])
            ))
        self.assertEqual(raised.exception.status_code, 409)

    def test_append_pages_rejects_books_with_active_jobs(self) -> None:
        draft = create_image_book_draft("处理中画册")
        with patch("service.app._enqueue_job", return_value={"id": "initial", "status": "queued"}):
            asyncio.run(upload_image_book_pages(
                draft["id"], [image_upload("page_1.png", (120, 80, 20))], json.dumps(["已有内容。"])
            ))
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(upload_image_book_pages(
                draft["id"], [image_upload("page_2.png", (20, 80, 120))], json.dumps(["新增内容。"])
            ))
        self.assertEqual(raised.exception.status_code, 409)

    def test_image_book_upload_rejects_text_image_count_mismatch(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(create_image_book(
                images=[image_upload("painting_1.png", (200, 20, 20))],
                page_texts=json.dumps(["第一段文字。", "多余文字。"]),
            ))
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("exactly one text entry", raised.exception.detail)

    def test_image_book_upload_rejects_reserved_page_marker(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(create_image_book(
                images=[image_upload("painting_1.png", (200, 20, 20))],
                page_texts=json.dumps([f"文字{store.PAGE_BREAK_TOKEN}意外标记"]),
            ))
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("inserted automatically", raised.exception.detail)

    def test_retry_uses_image_preparation_worker(self) -> None:
        self.book_id = str(uuid.uuid4())
        store.create_book(self.book_id, "画册重试")
        source_texts = store.book_directory(self.book_id) / "inputs/page_texts.json"
        source_texts.parent.mkdir(parents=True)
        source_texts.write_text("[]", encoding="utf-8")
        store.add_artifact(
            self.book_id, "input", "source_page_texts", source_texts, "digest", "application/json"
        )
        store.set_book_state(self.book_id, "document", "failed")
        with patch("service.app._enqueue_job", return_value={"id": "retry", "status": "queued"}) as enqueue:
            prepare_document_again(self.book_id)

        enqueue.assert_called_once_with(self.book_id, "document", "service.worker.prepare_image_book")

    def test_image_preparation_job_registers_page_artifacts_and_review_state(self) -> None:
        book_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        store.create_book(book_id, "画册 worker 测试", "Page images and matching text uploaded")
        image_dir = store.book_directory(book_id) / "inputs/pages"
        image_dir.mkdir(parents=True)
        Image.new("RGB", (32, 48), "green").save(image_dir / "page_0001.png")
        texts_path = store.book_directory(book_id) / "inputs/page_texts.json"
        texts_path.write_text(json.dumps([{"filename": "art.png", "text": "一段完整的朗读文字。"}], ensure_ascii=False), encoding="utf-8")
        store.add_artifact(book_id, "input", "source_page_texts", texts_path, "digest", "application/json")
        store.create_job(job_id, book_id, "document")

        result = prepare_image_book_job(job_id)

        book = store.get_book(book_id)
        assert book is not None
        page_images = [item for item in book["artifacts"] if item["stage"] == "pages" and item["kind"] == "page_image"]
        page_metadata = [item for item in book["artifacts"] if item["stage"] == "pages" and item["kind"] == "page_metadata"]
        text_artifacts = [item for item in book["artifacts"] if item["stage"] == "text" and item["kind"] == "normalized_text"]
        self.assertIn(book_id, result)
        self.assertEqual(len(page_images), 1)
        self.assertEqual(len(page_metadata), 1)
        self.assertEqual(len(text_artifacts), 1)
        self.assertEqual((book["current_stage"], book["status"]), ("pages_review", "awaiting_page_review"))


if __name__ == "__main__":
    unittest.main()