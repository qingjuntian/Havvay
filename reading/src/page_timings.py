"""Map PDF pages to narration chunks and derive page timing data."""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from moviepy import AudioFileClip
from pypdf import PdfReader

try:
    from .text_normalize import match_text
except ImportError:
    from text_normalize import match_text


def normalize(value: str) -> str:
    return match_text(value)


def page_texts(pdf_path: Path, pages_json: Path | None = None) -> list[str]:
    if pages_json:
        data = json.loads(pages_json.read_text(encoding="utf-8"))
        return [page["match_text"] for page in data["pages"]]
    pages = []
    for page_number, page in enumerate(PdfReader(str(pdf_path)).pages, 1):
        text = normalize(page.extract_text() or "")
        text = re.sub(rf"第{page_number}页共\d+页", "", text)
        pages.append(text)
    return pages


def chunk_data(chunks_dir: Path) -> tuple[list[dict], str]:
    items = []
    position = 0
    for text_path in sorted(chunks_dir.glob("chunk_*.txt")):
        text = normalize(text_path.read_text(encoding="utf-8").split("\n", 1)[-1])
        wav_path = text_path.with_suffix(".wav")
        audio = AudioFileClip(str(wav_path))
        duration = float(audio.duration)
        audio.close()
        items.append({
            "name": text_path.stem,
            "text_length": len(text),
            "start": position,
            "end": position + len(text),
            "duration": duration,
        })
        position += len(text)
    return items, "".join(
        normalize((chunks_dir / f"{item['name']}.txt").read_text(encoding="utf-8").split("\n", 1)[-1])
        for item in items
    )


def locate_page_starts(pages: list[str], joined: str) -> list[int]:
    starts = [0]
    previous = 0
    for page_number, page in enumerate(pages[1:], 2):
        start = None
        for length in (120, 80, 60, 40, 25, 15, 10):
            if len(page) < length:
                continue
            candidate = joined.find(page[:length], previous)
            if candidate >= 0:
                start = candidate
                break
        if start is None:
            blocks = SequenceMatcher(None, page[:300], joined[previous:], autojunk=False).get_matching_blocks()
            candidates = [block for block in blocks if block.size >= 15]
            if not candidates:
                raise ValueError(f"Could not locate the start of PDF page {page_number} in chunk text")
            block = max(candidates, key=lambda value: (value.size, -value.b))
            start = previous + block.b
        if start < previous:
            raise ValueError(f"PDF page {page_number} starts before the previous page")
        starts.append(start)
        previous = start
    return starts


def build_timings(pdf_path: Path, chunks_dir: Path, pages_json: Path | None = None) -> dict:
    pages = page_texts(pdf_path, pages_json)
    chunks, joined = chunk_data(chunks_dir)
    if len(pages) != 32:
        raise ValueError(f"Expected 32 PDF pages, found {len(pages)}")
    starts = locate_page_starts(pages, joined)
    if starts != sorted(starts) or starts[-1] >= len(joined):
        raise ValueError("PDF page boundaries are not monotonic")

    page_items = []
    for page_number, page_start in enumerate(starts):
        page_end = starts[page_number + 1] if page_number + 1 < len(starts) else len(joined)
        assigned = []
        duration = 0.0
        for chunk in chunks:
            overlap = max(0, min(chunk["end"], page_end) - max(chunk["start"], page_start))
            if overlap:
                share = chunk["duration"] * overlap / chunk["text_length"]
                duration += share
                assigned.append({"name": chunk["name"], "seconds": round(share, 6), "text_fraction": overlap / chunk["text_length"]})
        page_items.append({
            "page": page_number + 1,
            "image_index": page_number,
            "start": round(sum(item["duration"] for item in page_items), 6),
            "duration": round(duration, 6),
            "end": round(sum(item["duration"] for item in page_items) + duration, 6),
            "chunks": assigned,
        })
    total = sum(item["duration"] for item in page_items)
    return {"pdf": str(pdf_path), "chunks_dir": str(chunks_dir), "pages": page_items, "total_duration": round(total, 6)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create page timing data from a PDF and chunk WAV files.")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--chunks-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pages-json", default=None, help="Normalized page JSON from prepare_book.py")
    args = parser.parse_args()
    result = build_timings(Path(args.pdf), Path(args.chunks_dir), Path(args.pages_json) if args.pages_json else None)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}: {len(result['pages'])} pages, {result['total_duration']:.3f}s")


if __name__ == "__main__":
    main()
