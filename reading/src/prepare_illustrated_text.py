"""Split a multi-work TXT into image-aligned TTS pages."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image

try:
    from .text_normalize import match_text, normalize_text
except ImportError:
    from text_normalize import match_text, normalize_text

PAGE_BREAK_TOKEN = "<<<BOOK_PAGE_BREAK>>>"
TITLE_RE = re.compile(r"^\s*作品名称\s*[：:]\s*(.+?)\s*$")


def read_sections(path: Path) -> list[dict]:
    sections = []
    current_title = None
    current_lines: list[str] = []
    source = path.read_text(encoding="utf-8-sig")
    source = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", source)
    for line in source.splitlines():
        clean = line.strip()
        match = TITLE_RE.match(clean)
        if match:
            if current_title is not None:
                sections.append({"title": current_title, "text": "\n".join(current_lines).strip()})
            current_title = match.group(1).strip()
            current_lines = [line.rstrip()]
        elif current_title is not None:
            current_lines.append(line.rstrip())
    if current_title is not None:
        sections.append({"title": current_title, "text": "\n".join(current_lines).strip()})
    return sections


def sorted_images(images_dir: Path) -> list[Path]:
    allowed = {".png", ".jpg", ".jpeg"}
    return sorted(
        (path for path in images_dir.iterdir() if path.is_file() and path.suffix.lower() in allowed),
        key=lambda path: [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare TXT sections and image pages for a narrated video.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    source_text = Path(args.text).resolve()
    source_images = Path(args.images_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    for old_image in pages_dir.glob("page_*.png"):
        old_image.unlink()

    sections = read_sections(source_text)
    images = sorted_images(source_images)
    if not sections:
        raise SystemExit(f"No '作品名称：...' sections found in {source_text}")
    if len(sections) != len(images):
        raise SystemExit(f"Found {len(sections)} work sections but {len(images)} images in {source_images}")

    page_items = []
    for index, (section, image_path) in enumerate(zip(sections, images), 1):
        page_image = pages_dir / f"page_{index:04d}.png"
        with Image.open(image_path) as image:
            image.convert("RGB").save(page_image, format="PNG", optimize=True)
        page_items.append({
            "page": index,
            "title": section["title"],
            "image": page_image.name,
            "source_image": str(image_path),
            "text": section["text"],
            "match_text": match_text(section["text"]),
        })

    book_text = f"\n\n{PAGE_BREAK_TOKEN}\n\n".join(item["text"] for item in page_items) + "\n"
    (output_dir / "book.txt").write_text(book_text, encoding="utf-8")
    payload = {"source_text": str(source_text), "page_count": len(page_items), "pages": page_items, "checklist": []}
    (output_dir / "book_pages.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "book_checklist.json").write_text(json.dumps({"items": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(page_items)} text/image pages in {output_dir}")
    for item in page_items:
        print(f"{item['page']}: {item['title']} -> {item['image']}")


if __name__ == "__main__":
    main()
