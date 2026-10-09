"""Prepare ordered image pages and user-provided per-page TTS text."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.prepare_book import join_pages_for_tts
from src.text_normalize import match_text, normalize_text


def prepare_image_book(
    images_dir: Path,
    page_texts_path: Path,
    output_dir: Path,
    text_output: Path,
    pages_output: Path,
) -> list[dict]:
    submitted_pages = json.loads(page_texts_path.read_text(encoding="utf-8"))
    if not isinstance(submitted_pages, list) or not submitted_pages:
        raise ValueError("No image pages or page texts were provided")

    page_records = []
    normalized_texts = []
    output_images = output_dir / "pages"
    output_images.mkdir(parents=True, exist_ok=True)
    for page_number, submitted in enumerate(submitted_pages, 1):
        source_image = images_dir / f"page_{page_number:04d}.png"
        if not source_image.is_file():
            raise FileNotFoundError(f"Missing image for page {page_number}")
        raw_text = submitted.get("text", "")
        text = normalize_text(raw_text)
        if not text:
            raise ValueError(f"Page {page_number} has no TTS text")
        image_path = output_images / source_image.name
        shutil.copy2(source_image, image_path)
        page_records.append({
            "page": page_number,
            "raw_text": raw_text,
            "text": text,
            "match_text": match_text(text),
            "source_image": submitted.get("filename", source_image.name),
        })
        normalized_texts.append(text)

    text_output.parent.mkdir(parents=True, exist_ok=True)
    pages_output.parent.mkdir(parents=True, exist_ok=True)
    text_output.write_text(join_pages_for_tts(normalized_texts) + "\n", encoding="utf-8")
    payload = {"source": "user_images", "checklist": [], "pages": page_records}
    pages_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pages_output.with_name("book_checklist.json").write_text(
        json.dumps({"items": []}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return page_records
