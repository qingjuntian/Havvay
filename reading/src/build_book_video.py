"""Run the PDF -> cloned audio -> page-timed MP4 pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run(command: list[str]) -> None:
    print("[run]", " ".join(str(item) for item in command))
    subprocess.run(command, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a page-timed book video from PDF and voice reference.")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--voice", required=True, help="Raw voice sample")
    parser.add_argument("--ref-text", required=True, help="Exact transcript of the retained reference speech")
    parser.add_argument("--f5-python", default=sys.executable, help="Python executable with F5-TTS installed")
    parser.add_argument("--work-dir", default="output/book_build")
    parser.add_argument("--speed", type=float, default=1.2)
    parser.add_argument("--nfe-step", type=int, default=32)
    parser.add_argument("--max-chars", type=int, default=100)
    parser.add_argument("--test-limit", type=int, default=0)
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--transition", type=float, default=0.8)
    parser.add_argument("--rerender-chunks", default="")
    parser.add_argument("--chunk-overrides", default=None)
    parser.add_argument("--output", default="output/book.mp4")
    args = parser.parse_args()

    work = (ROOT / args.work_dir).resolve()
    reference_dir = work / "reference"
    f5_dir = work / "f5"
    work.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)
    book_text = work / "book.txt"
    pages_json = work / "book_pages.json"
    reference_audio = reference_dir / "reference.wav"
    reference_text = reference_dir / "reference.txt"
    timings = work / "page_timings.json"
    audio = f5_dir / "audiobook.mp3"

    image_count = len(list((ROOT / args.images_dir).resolve().glob("*.png")))
    if image_count == 0:
        raise SystemExit(f"No PNG images found in {args.images_dir}")
    run([sys.executable, str(SRC / "prepare_book.py"), "--pdf", args.pdf,
         "--text-output", str(book_text), "--pages-output", str(pages_json)])
    page_count = len(json.loads(pages_json.read_text(encoding="utf-8"))["pages"])
    if image_count != page_count:
        raise SystemExit(f"PDF has {page_count} pages but images directory has {image_count} PNG files")
    run([sys.executable, str(SRC / "prepare_reference.py"), "--input", args.voice,
         "--output", str(reference_audio), "--text-output", str(reference_text), "--ref-text", args.ref_text])
    f5_command = [args.f5_python, str(SRC / "narrate_book_f5.py"), "--book", str(book_text),
                  "--reference-audio", str(reference_audio), "--reference-text-file", str(reference_text),
                  "--output-dir", str(f5_dir), "--speed", str(args.speed), "--nfe-step", str(args.nfe_step),
                  "--max-chars", str(args.max_chars), "--test-limit", str(args.test_limit),
                  "--rerender-chunks", args.rerender_chunks]
    if args.chunk_overrides:
        f5_command += ["--chunk-overrides", args.chunk_overrides]
    run(f5_command)
    run([sys.executable, str(SRC / "page_timings.py"), "--pdf", args.pdf,
         "--pages-json", str(pages_json), "--chunks-dir", str(f5_dir / "chunks"), "--output", str(timings)])
    run([sys.executable, str(SRC / "book_video.py"), "--audio", str(audio), "--images-dir", args.images_dir,
         "--timings", str(timings), "--width", str(args.width), "--height", str(args.height),
         "--fps", str(args.fps), "--transition", str(args.transition), "--output", str(ROOT / args.output)])
    print(f"[done] {ROOT / args.output}")


if __name__ == "__main__":
    main()
