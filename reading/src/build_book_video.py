"""Run the PDF -> cloned audio -> page-timed MP4 pipeline."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run(command: list[str]) -> None:
    print("[run]", " ".join(str(item) for item in command))
    subprocess.run(command, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a page-timed book video from a laid-out PDF.")
    parser.add_argument("--pdf", required=True, help="Laid-out PDF; pages and images are generated from this file")
    parser.add_argument("--voice", required=True, help="Raw voice sample")
    parser.add_argument("--ref-text", required=True, help="Exact transcript of the retained reference speech")
    parser.add_argument("--f5-python", default=sys.executable, help="Python executable with F5-TTS installed")
    parser.add_argument("--work-dir", default="output/book_build")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--nfe-step", type=int, default=32)
    parser.add_argument("--max-chars", type=int, default=100)
    parser.add_argument("--test-limit", type=int, default=0)
    parser.add_argument("--page-limit", type=int, default=0, help="Render only the first N complete pages as a preview")
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--transition", type=float, default=0.8)
    parser.add_argument("--rerender-chunks", default="")
    parser.add_argument("--chunk-overrides", default=None)
    parser.add_argument("--output", default="output/book.mp4")
    args = parser.parse_args()
    if args.page_limit < 0:
        parser.error("--page-limit must be zero or greater")
    if args.page_limit and args.test_limit:
        parser.error("--page-limit and --test-limit cannot be combined")

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

    pdf = (ROOT / args.pdf).resolve()
    images_dir = work / "pages"
    run([sys.executable, str(SRC / "prepare_book.py"), "--pdf", str(pdf),
         "--images-dir", str(images_dir), "--text-output", str(book_text),
         "--pages-output", str(pages_json)])

    image_count = len(list(images_dir.glob("*.png")))
    if image_count == 0:
        raise SystemExit(f"No PNG page images found in {images_dir}")
    page_count = len(json.loads(pages_json.read_text(encoding="utf-8"))["pages"])
    if image_count != page_count:
        raise SystemExit(f"Document has {page_count} pages but images directory has {image_count} PNG files")

    selected_images_dir = images_dir
    selected_pages_json = pages_json
    if args.page_limit:
        try:
            from .prepare_book import join_pages_for_tts
        except ImportError:
            from prepare_book import join_pages_for_tts

        page_payload = json.loads(pages_json.read_text(encoding="utf-8"))
        selected_pages = page_payload["pages"][:args.page_limit]
        if not selected_pages:
            raise SystemExit("The document contains no pages to preview")
        preview_dir = work / f"preview_{len(selected_pages)}_pages"
        selected_images_dir = preview_dir / "pages"
        selected_images_dir.mkdir(parents=True, exist_ok=True)
        for old_image in selected_images_dir.glob("page_*.png"):
            old_image.unlink()
        source_images = sorted(images_dir.glob("*.png"))[:len(selected_pages)]
        for source_image in source_images:
            shutil.copy2(source_image, selected_images_dir / source_image.name)
        if len(source_images) != len(selected_pages):
            raise SystemExit("Not enough page images for the requested preview")
        selected_pages_json = preview_dir / "book_pages.json"
        selected_pages_json.write_text(
            json.dumps({**page_payload, "pages": selected_pages}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        book_text = preview_dir / "book.txt"
        book_text.write_text(join_pages_for_tts([page["text"] for page in selected_pages]) + "\n", encoding="utf-8")
        f5_dir = preview_dir / "f5"
        audio = f5_dir / "audiobook.mp3"
        timings = preview_dir / "page_timings.json"
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
    if args.test_limit > 0:
        print(f"[test] generated first {args.test_limit} chunks; skipping full-book page timing and video")
        print(f"[done] test audio: {audio}")
        return
    run([sys.executable, str(SRC / "page_timings.py"), "--pdf", str(pdf),
         "--pages-json", str(selected_pages_json), "--chunks-dir", str(f5_dir / "chunks"), "--output", str(timings)])
    run([sys.executable, str(SRC / "book_video.py"), "--audio", str(audio), "--images-dir", str(selected_images_dir),
         "--timings", str(timings), "--width", str(args.width), "--height", str(args.height),
         "--fps", str(args.fps), "--transition", str(args.transition), "--output", str(ROOT / args.output)])
    print(f"[done] {ROOT / args.output}")


if __name__ == "__main__":
    main()
