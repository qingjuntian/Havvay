"""Extract and normalize a PDF into TTS text and page-preserving JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

try:
    from .text_normalize import match_text, normalize_text
except ImportError:
    from text_normalize import match_text, normalize_text


HEADING_RE = re.compile(
    r"^(?:第一章|第二章|第三章|第四章|第五章|第六章|第七章|第八章|第九章|第十章|"
    r"第一节|第二节|第三节|第四节|第五节|第六节|第七节|第八节|第九节|第十节|"
    r"[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）|\([一二三四五六七八九十]+\)|\d+\.)"
)
FIGURE_RE = re.compile(r"^(?:图表?|表格?)\s*\d*\s*[:：.、]?", re.IGNORECASE)
PAGE_BREAK_TOKEN = "<<<BOOK_PAGE_BREAK>>>"
SENTENCE_END_RE = re.compile(r"[。！？!?；;]")


def reconcile_page_breaks(page_texts: list[str]) -> list[str]:
    """Move page breaks to the nearest sentence end without changing page count."""
    pages = list(page_texts)
    for index in range(len(pages) - 1):
        left, right = pages[index], pages[index + 1]
        boundary = len(left)
        combined = left + right
        sentence_ends = [match.end() for match in SENTENCE_END_RE.finditer(combined)]
        before = max((position for position in sentence_ends if position <= boundary), default=None)
        after = min((position for position in sentence_ends if position > boundary), default=None)
        if before is None and after is None:
            continue
        if before is None or (after is not None and after - boundary < boundary - before):
            boundary = after
        else:
            boundary = before
        pages[index] = combined[:boundary]
        pages[index + 1] = combined[boundary:]
    return pages


def extract_page_records(pdf: Path) -> tuple[list[dict], list[dict]]:
    raw_pages = [(page.extract_text() or "") for page in PdfReader(str(pdf)).pages]
    repeated = set()
    line_sets = []
    for raw in raw_pages:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        line_sets.append(lines)
    for position in (0, -1):
        counts: dict[str, int] = {}
        for lines in line_sets:
            if lines:
                value = re.sub(r"\d+", "", lines[position])
                counts[value] = counts.get(value, 0) + 1
        repeated.update(value for value, count in counts.items() if count >= max(2, len(raw_pages) // 2))

    pages = []
    checklist = []
    for page_number, lines in enumerate(line_sets, 1):
        kept = []
        body = []

        def flush_body() -> None:
            if body:
                kept.append("".join(body))
                body.clear()

        for line in lines:
            if re.fullmatch(rf"第?\s*{page_number}\s*页(?:\s*共\s*\d+\s*页)?", line):
                continue
            if re.sub(r"\d+", "", line) in repeated:
                continue
            if FIGURE_RE.match(line):
                checklist.append({"page": page_number, "text": line, "reason": "figure_or_table_caption", "speak": False})
                continue
            if HEADING_RE.match(line):
                flush_body()
                kept.append(normalize_text(line))
                kept.append("")
            else:
                body.append(line)
        flush_body()
        page_text = "\n\n".join(normalize_text(block) for block in kept if block)
        pages.append({
            "page": page_number,
            "raw_text": raw_pages[page_number - 1],
            "text": page_text,
            "match_text": match_text(page_text),
        })
    spoken_pages = reconcile_page_breaks([page["text"] for page in pages])
    for page, spoken_text in zip(pages, spoken_pages):
        page["text"] = spoken_text
        page["match_text"] = match_text(spoken_text)
    return pages, checklist


def extract_pages(pdf: Path) -> tuple[list[str], list[dict]]:
    records, checklist = extract_page_records(pdf)
    return [page["text"] for page in records], checklist


def join_pages_for_tts(pages: list[str]) -> str:
    """Mark page regions so TTS chunks and rendered pages remain aligned."""
    return f"\n\n{PAGE_BREAK_TOKEN}\n\n".join(page.strip() for page in pages)


def render_page_images(pdf: Path, images_dir: Path, dpi: int = 160) -> int:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF (pymupdf) to render PDF pages to PNG") from exc

    images_dir.mkdir(parents=True, exist_ok=True)
    for old_image in images_dir.glob("page_*.png"):
        old_image.unlink()
    scale = dpi / 72
    with fitz.open(pdf) as document:
        for index, page in enumerate(document, 1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            pixmap.save(images_dir / f"page_{index:04d}.png")
        return len(document)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a normalized, page-preserving book from PDF.")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--images-dir")
    parser.add_argument("--text-output", required=True)
    parser.add_argument("--pages-output", required=True)
    args = parser.parse_args()

    pages, checklist = extract_page_records(Path(args.pdf))
    if args.images_dir:
        rendered_page_count = render_page_images(Path(args.pdf), Path(args.images_dir))
        if rendered_page_count != len(pages):
            raise RuntimeError(
                f"PDF renderer produced {rendered_page_count} images but text extraction found {len(pages)} pages"
            )
    text_output = Path(args.text_output)
    pages_output = Path(args.pages_output)
    text_output.parent.mkdir(parents=True, exist_ok=True)
    pages_output.parent.mkdir(parents=True, exist_ok=True)
    text_output.write_text(join_pages_for_tts([page["text"] for page in pages]) + "\n", encoding="utf-8")
    payload = {
        "pdf": str(Path(args.pdf)),
        "checklist": checklist,
        "pages": pages,
    }
    pages_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    checklist_output = pages_output.with_name("book_checklist.json")
    checklist_output.write_text(json.dumps({"items": checklist}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(pages)} pages to {args.text_output} and {args.pages_output}")
    print(f"Checklist: {len(checklist)} suspected figure/table items in {checklist_output}")


if __name__ == "__main__":
    main()
