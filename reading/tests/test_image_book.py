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
    PageTextUpdate,
    prepare_document_again,
    PronunciationUpdate,
    regenerate_book,
    TextUpdate,
    update_text,
    update_page_text,
    update_pronunciations,
    upload_reference,
    upload_image_book_pages,
)
from service.worker import prepare_image_book as prepare_image_book_job
from src import narrate_book_f5
from src.prepare_image_book import prepare_image_book
from src.page_timings import build_timings, page_texts


def image_upload(filename: str, color: tuple[int, int, int]) -> UploadFile:
    stream = io.BytesIO()
    Image.new("RGB", (32, 48), color).save(stream, format="PNG")
    stream.seek(0)
    return UploadFile(filename=filename, file=stream, headers={"content-type": "image/png"})


class ImageBookPreparationTests(unittest.TestCase):
    def test_f5_keeps_heading_paragraphs_separate(self) -> None:
        text = "（一）服务对象层面的目标\n\n一、缓解生活困难\n\n社会工作服务帮助有困难的人。"

        chunks = narrate_book_f5.build_chunks(text)

        self.assertEqual([chunk[0] for chunk in chunks], [
            "（一）服务对象层面的目标",
            "一、缓解生活困难",
            "社会工作服务帮助有困难的人。",
        ])

    def test_f5_page_pause_is_configurable_without_changing_pdf_default(self) -> None:
        text = f"第一页内容。\n\n{store.PAGE_BREAK_TOKEN}\n\n第二页内容。"

        image_book_chunks = narrate_book_f5.build_chunks(text, page_pause=1.5)
        pdf_chunks = narrate_book_f5.build_chunks(text)

        self.assertEqual(image_book_chunks[0], ("第一页内容。", 1.5))
        self.assertEqual(pdf_chunks[0], ("第一页内容。", 0.0))

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
        reference_path = store.book_directory(initial["id"]) / "artifacts/reference/reference.wav"
        reference_path.parent.mkdir(parents=True)
        reference_path.write_bytes(b"processed reference")
        voice_path = store.book_directory(initial["id"]) / "inputs/voice.wav"
        voice_path.parent.mkdir(parents=True, exist_ok=True)
        voice_path.write_bytes(b"voice sample")
        store.add_artifact(
            initial["id"], "reference_input", "voice_sample", voice_path,
            "voice-digest", "audio/wav",
        )
        store.add_artifact(
            initial["id"], "reference_review", "processed_audio", reference_path,
            "reference-digest", "audio/wav",
        )
        audio_path = store.book_directory(initial["id"]) / "artifacts/final/audiobook.mp3"
        audio_path.parent.mkdir(parents=True)
        audio_path.write_bytes(b"existing audio")
        store.add_artifact(
            initial["id"], "final_audio_review", "audiobook_mp3", audio_path,
            "audio-digest", "audio/mpeg", {"page_count": 1, "text_version": 2},
        )
        store.set_book_state(initial["id"], "reference", "awaiting_reference")

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
        self.assertEqual(result["text_update"]["regeneration"], None)
        self.assertEqual((updated["current_stage"], updated["status"]), ("full_audio_update", "ready"))
        self.assertEqual(store.count_active_jobs(initial["id"]), 0)
        with patch("service.app._enqueue_job", return_value={"id": "audio-update", "status": "queued"}) as enqueue:
            regenerate_book(initial["id"])
        enqueue.assert_called_once_with(
            initial["id"], "full_audio_update", "service.worker.synthesize_full_audio_update"
        )

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

    def test_saving_page_text_advances_without_a_separate_approval(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "文字保存即确认")
        pages_path = store.book_directory(book_id) / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}, {"page": 2}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")

        result = update_text(book_id, TextUpdate(text="第一页文字。\n\n<<<BOOK_PAGE_BREAK>>>\n\n第二页文字。"))

        updated = store.get_book(book_id)
        assert updated is not None
        self.assertIsNone(result["regeneration"])
        self.assertEqual((updated["current_stage"], updated["status"]), ("reference", "awaiting_reference"))

    def test_bulk_saving_all_page_text_advances_legacy_book_to_reference(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "旧版整本确认")
        pages_path = store.book_directory(book_id) / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}, {"page": 2}, {"page": 3}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")

        result = update_text(book_id, TextUpdate(text="第一页。\n\n<<<BOOK_PAGE_BREAK>>>\n\n第二页。\n\n<<<BOOK_PAGE_BREAK>>>\n\n第三页。"))

        updated = store.get_book(book_id)
        assert updated is not None
        self.assertEqual(result["confirmed_page_count"], 3)
        self.assertTrue(result["review_complete"])
        self.assertEqual((updated["current_stage"], updated["status"]), ("reference", "awaiting_reference"))

    def test_saving_unchanged_page_text_still_confirms_review(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "未改文本保存")
        home = store.book_directory(book_id)
        pages_path = home / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")
        text_path = home / "artifacts/text/v1/book.txt"
        text_path.parent.mkdir(parents=True)
        text_path.write_text("这一页的朗读内容。\n", encoding="utf-8")
        store.add_artifact(book_id, "text", "normalized_text", text_path, "text", "text/plain")
        store.set_book_state(book_id, "pages_review", "awaiting_page_review")

        result = update_text(book_id, TextUpdate(text="这一页的朗读内容。"))

        updated = store.get_book(book_id)
        assert updated is not None
        self.assertEqual(result["confirmed_page_count"], 1)
        self.assertTrue(result["review_complete"])
        self.assertEqual((updated["current_stage"], updated["status"]), ("reference", "awaiting_reference"))

    def test_page_saves_confirm_individually_then_advance_after_last_page(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "逐页确认")
        root = store.book_directory(book_id)
        pages_path = root / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}, {"page": 2}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")
        text_path = root / "artifacts/text/v1/book.txt"
        text_path.parent.mkdir(parents=True)
        text_path.write_text("第一页原文。\n<<<BOOK_PAGE_BREAK>>>\n第二页原文。\n", encoding="utf-8")
        store.add_artifact(book_id, "text", "normalized_text", text_path, "text", "text/plain")
        store.set_book_state(book_id, "pages_review", "awaiting_page_review")

        first_save = update_page_text(book_id, 1, PageTextUpdate(text="第一页已核对。"))
        after_first = store.get_book(book_id)
        assert after_first is not None
        self.assertEqual(first_save["confirmed_page_count"], 1)
        self.assertEqual(first_save["page_count"], 2)
        self.assertEqual((after_first["current_stage"], after_first["status"]), ("pages_review", "awaiting_page_review"))

        second_save = update_page_text(book_id, 2, PageTextUpdate(text="第二页已核对。"))
        after_second = store.get_book(book_id)
        assert after_second is not None
        self.assertEqual(second_save["confirmed_page_count"], 2)
        self.assertEqual(second_save["review_complete"], True)
        self.assertEqual((after_second["current_stage"], after_second["status"]), ("reference", "awaiting_reference"))

    def test_page_text_endpoint_rejects_empty_page_text(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "空白页校验")
        home = store.book_directory(book_id)
        pages_path = home / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")
        text_path = home / "artifacts/text/v1/book.txt"
        text_path.parent.mkdir(parents=True)
        text_path.write_text("原页面文字。", encoding="utf-8")
        store.add_artifact(book_id, "text", "normalized_text", text_path, "text", "text/plain")

        with self.assertRaises(HTTPException) as raised:
            update_page_text(book_id, 1, PageTextUpdate(text="  \n  "))

        self.assertEqual(raised.exception.status_code, 400)

    def test_legacy_page_review_book_can_upload_reference_directly(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "旧书直接上传参考音频")
        root = store.book_directory(book_id)
        pages_path = root / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}, {"page": 2}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")
        text_path = root / "artifacts/text/v1/book.txt"
        text_path.parent.mkdir(parents=True)
        text_path.write_text("第一页原文。\n<<<BOOK_PAGE_BREAK>>>\n第二页原文。\n", encoding="utf-8")
        store.add_artifact(book_id, "text", "normalized_text", text_path, "text", "text/plain")
        store.set_book_state(book_id, "pages_review", "awaiting_page_review")
        voice = UploadFile(filename="voice.wav", file=io.BytesIO(b"test wave bytes"))

        result = asyncio.run(upload_reference(book_id, voice, "参考录音准确文本"))

        updated = store.get_book(book_id)
        assert updated is not None
        latest_text = max(
            (item for item in updated["artifacts"] if item["stage"] == "text" and item["kind"] == "normalized_text"),
            key=lambda item: item["version"],
        )
        self.assertEqual(latest_text["metadata"]["confirmed_pages"], [1, 2])
        self.assertEqual((updated["current_stage"], updated["status"]), ("reference_preparation", "ready"))
        self.assertEqual(result["regeneration"]["status"], "pending")
        self.assertEqual(store.count_active_jobs(book_id), 0)
        with patch("service.app._enqueue_job", return_value={"id": "reference-job", "status": "queued"}) as enqueue:
            regenerate_book(book_id)
        enqueue.assert_called_once_with(book_id, "reference_preparation", "service.worker.prepare_reference")

    def test_replaces_reference_during_review_and_preserves_old_artifacts_as_stale(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "替换参考声音")
        root = store.book_directory(book_id)
        artifacts = [
            ("reference_input", "voice_sample", "voice.wav"),
            ("reference_input", "ref_text", "text.txt"),
            ("reference_review", "processed_audio", "processed.wav"),
            ("preview_audio_review", "audiobook_mp3", "preview.mp3"),
        ]
        for stage, kind, filename in artifacts:
            path = root / "artifacts" / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"previous")
            store.add_artifact(book_id, stage, kind, path, filename, "application/octet-stream")
        store.set_book_state(book_id, "reference_review", "awaiting_reference_review")
        voice = UploadFile(filename="replacement.m4a", file=io.BytesIO(b"new voice"))

        result = asyncio.run(upload_reference(book_id, voice, "新的准确转写"))

        updated = store.get_book(book_id)
        assert updated is not None
        versions = [item for item in updated["artifacts"] if item["stage"] == "reference_input"]
        self.assertEqual(len([item for item in versions if item["kind"] == "voice_sample"]), 2)
        self.assertTrue(all(item["stale"] for item in versions if item["version"] == 1))
        self.assertFalse(max((item for item in versions if item["kind"] == "voice_sample"), key=lambda item: item["version"])["stale"])
        self.assertTrue(next(item for item in updated["artifacts"] if item["kind"] == "processed_audio")["stale"])
        self.assertTrue(next(item for item in updated["artifacts"] if item["kind"] == "audiobook_mp3")["stale"])
        self.assertEqual((updated["current_stage"], updated["status"]), ("reference_preparation", "ready"))
        self.assertEqual(result["regeneration"]["status"], "pending")
        self.assertEqual(store.count_active_jobs(book_id), 0)

    def test_rejects_reference_replacement_while_a_job_is_active(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "处理中不可替换")
        store.set_book_state(book_id, "preview_audio", "running")
        voice = UploadFile(filename="replacement.wav", file=io.BytesIO(b"new voice"))

        with patch("service.app.store.count_active_jobs", return_value=1):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(upload_reference(book_id, voice, "新的准确转写"))

        self.assertEqual(raised.exception.status_code, 409)

    def test_regenerate_after_image_change_only_queues_video(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "只更新视频")
        root = store.book_directory(book_id)
        artifacts = [
            ("pages", "page_metadata", "pages.json", {"pages": [{"page": 1}]}),
            ("text", "normalized_text", "book.txt", "朗读文本。"),
            ("reference_input", "voice_sample", "voice.wav", b"voice"),
            ("reference_review", "processed_audio", "reference.wav", b"reference"),
            ("final_audio_review", "audiobook_mp3", "final.mp3", {"page_count": 1, "text_version": 1}),
            ("final_video_review", "video_mp4", "final.mp4", b"video"),
        ]
        for stage, kind, filename, payload in artifacts:
            path = root / "artifacts" / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            if filename.endswith(".json"):
                path.write_text(json.dumps(payload), encoding="utf-8")
            elif filename.endswith(".txt"):
                path.write_text(payload, encoding="utf-8")
            else:
                path.write_bytes(payload if isinstance(payload, bytes) else b"audio")
            metadata = payload if isinstance(payload, dict) else {}
            store.add_artifact(book_id, stage, kind, path, filename, "application/octet-stream", metadata)
        store.invalidate_video_artifacts(book_id, "Page image replaced")
        store.set_book_state(book_id, "full_video", "ready")

        with patch("service.app._enqueue_job", return_value={"id": "video-job", "status": "queued"}) as enqueue:
            regenerate_book(book_id)

        enqueue.assert_called_once_with(book_id, "full_video", "service.worker.render_full_video")

    def test_regenerate_after_reference_change_does_not_reuse_old_audio_chunks(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "更新声音后全量合成")
        root = store.book_directory(book_id)
        text_path = root / "artifacts/text/v1/book.txt"
        text_path.parent.mkdir(parents=True)
        text_path.write_text("已确认的朗读文本。", encoding="utf-8")
        store.add_artifact(
            book_id, "text", "normalized_text", text_path, "text", "text/plain",
            {"confirmed_pages": [1]},
        )
        pages_path = root / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")
        old_audio_path = root / "artifacts/final/old.mp3"
        old_audio_path.parent.mkdir(parents=True)
        old_audio_path.write_bytes(b"old synthesized audio")
        store.add_artifact(
            book_id, "final_audio_review", "audiobook_mp3", old_audio_path,
            "old-audio", "audio/mpeg", {"page_count": 1, "text_version": 1},
        )
        voice_path = root / "inputs/new_voice.wav"
        voice_path.parent.mkdir(parents=True)
        voice_path.write_bytes(b"new voice")
        store.add_artifact(book_id, "reference_input", "voice_sample", voice_path, "voice", "audio/wav")
        processed_path = root / "artifacts/reference/new_reference.wav"
        processed_path.parent.mkdir(parents=True)
        processed_path.write_bytes(b"processed new voice")
        store.add_artifact(
            book_id, "reference_review", "processed_audio", processed_path,
            "new-reference", "audio/wav",
        )
        store.set_book_state(book_id, "full_audio_update", "ready")

        with patch("service.app._enqueue_job", return_value={"id": "fresh-audio", "status": "queued"}) as enqueue:
            regenerate_book(book_id)

        enqueue.assert_called_once_with(book_id, "full_audio", "service.worker.synthesize_full_audio")

    def test_regenerate_without_processed_reference_does_not_crash(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "无处理参考音频时仍应可生成")
        root = store.book_directory(book_id)
        text_path = root / "artifacts/text/v1/book.txt"
        text_path.parent.mkdir(parents=True)
        text_path.write_text("已确认的朗读文本。", encoding="utf-8")
        store.add_artifact(
            book_id, "text", "normalized_text", text_path, "text", "text/plain",
            {"confirmed_pages": [1]},
        )
        pages_path = root / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")
        old_audio_path = root / "artifacts/final/old.mp3"
        old_audio_path.parent.mkdir(parents=True)
        old_audio_path.write_bytes(b"old synthesized audio")
        store.add_artifact(
            book_id, "final_audio_review", "audiobook_mp3", old_audio_path,
            "old-audio", "audio/mpeg", {"page_count": 1, "text_version": 1},
        )
        voice_path = root / "inputs/voice.wav"
        voice_path.parent.mkdir(parents=True)
        voice_path.write_bytes(b"new voice")
        store.add_artifact(book_id, "reference_input", "voice_sample", voice_path, "voice", "audio/wav")
        store.set_book_state(book_id, "full_audio_update", "ready")

        with patch("service.app.store.has_valid_artifact", return_value=True):
            with patch("service.app._enqueue_job", return_value={"id": "fresh-audio", "status": "queued"}) as enqueue:
                regenerate_book(book_id)

        enqueue.assert_called_once_with(book_id, "full_audio", "service.worker.synthesize_full_audio")

    def test_pronunciation_dictionary_is_saved_and_waits_for_explicit_generation(self) -> None:
        book_id = str(uuid.uuid4())
        store.create_book(book_id, "人名读音词典")
        root = store.book_directory(book_id)
        text_path = root / "artifacts/text/v1/book.txt"
        text_path.parent.mkdir(parents=True)
        text_path.write_text("单于来到这里。", encoding="utf-8")
        store.add_artifact(
            book_id, "text", "normalized_text", text_path, "text", "text/plain",
            {"confirmed_pages": [1]},
        )
        pages_path = root / "artifacts/pages/book_pages.json"
        pages_path.parent.mkdir(parents=True)
        pages_path.write_text(json.dumps({"pages": [{"page": 1}]}), encoding="utf-8")
        store.add_artifact(book_id, "pages", "page_metadata", pages_path, "pages", "application/json")
        audio_path = root / "artifacts/final/audio.mp3"
        audio_path.parent.mkdir(parents=True)
        audio_path.write_bytes(b"existing audio")
        store.add_artifact(
            book_id, "final_audio_review", "audiobook_mp3", audio_path,
            "audio", "audio/mpeg", {"page_count": 1, "text_version": 1, "pronunciation_version": 0},
        )
        store.set_book_state(book_id, "final_audio_review", "awaiting_final_audio_review")

        result = update_pronunciations(book_id, PronunciationUpdate(entries={"单于": "shan4 yu2"}))

        saved = store.get_book(book_id)
        assert saved is not None
        self.assertFalse(result["unchanged"])
        self.assertEqual(result["metadata"]["entry_count"], 1)
        self.assertEqual((saved["current_stage"], saved["status"]), ("full_audio_update", "ready"))
        self.assertTrue(next(item for item in saved["artifacts"] if item["kind"] == "audiobook_mp3")["stale"])
        self.assertEqual(store.count_active_jobs(book_id), 0)
        dictionary_path = store.service_home() / result["path"]
        self.assertEqual(json.loads(dictionary_path.read_text(encoding="utf-8")), {"单于": "shan4 yu2"})

        repeated = update_pronunciations(book_id, PronunciationUpdate(entries={"单于": "shan4 yu2"}))
        self.assertTrue(repeated["unchanged"])

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
        self.assertEqual(text_artifacts[0]["metadata"]["confirmed_pages"], [1])
        self.assertEqual((book["current_stage"], book["status"]), ("reference", "awaiting_reference"))


if __name__ == "__main__":
    unittest.main()