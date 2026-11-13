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


def extract_pages(pdf: Path) -> tuple[list[str], list[dict]]:
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
        pages.append("\n\n".join(normalize_text(block) for block in kept if block))
    return pages, checklist


def join_pages_for_tts(pages: list[str]) -> str:
    """Join PDF pages without turning a visual page wrap into a speech pause."""
    if not pages:
        return ""
    text = pages[0]
    for page in pages[1:]:
        if HEADING_RE.match(page):
            text += "\n\n" + page
        else:
            text += page
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a normalized, page-preserving book from PDF.")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--text-output", required=True)
    parser.add_argument("--pages-output", required=True)
    args = parser.parse_args()

    pages, checklist = extract_pages(Path(args.pdf))
    text_output = Path(args.text_output)
    pages_output = Path(args.pages_output)
    text_output.parent.mkdir(parents=True, exist_ok=True)
    pages_output.parent.mkdir(parents=True, exist_ok=True)
    text_output.write_text(join_pages_for_tts(pages) + "\n", encoding="utf-8")
    payload = {
        "pdf": str(Path(args.pdf)),
        "checklist": checklist,
        "pages": [{"page": i, "text": text, "match_text": match_text(text)} for i, text in enumerate(pages, 1)],
    }
    pages_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    checklist_output = pages_output.with_name("book_checklist.json")
    checklist_output.write_text(json.dumps({"items": checklist}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(pages)} pages to {args.text_output} and {args.pages_output}")
    print(f"Checklist: {len(checklist)} suspected figure/table items in {checklist_output}")


if __name__ == "__main__":
    main()
