"""Create a manuscript-following reading video from narration audio."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]


def audio_duration(audio: Path) -> float:
    from moviepy import AudioFileClip

    clip = AudioFileClip(str(audio))
    duration = float(clip.duration)
    clip.close()
    return duration


def load_image_files(images_dir: str | None) -> list[Path]:
    if not images_dir:
        return []
    image_dir = Path(images_dir).resolve()
    return sorted(
        image_dir.glob("*.png"),
        key=lambda path: [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)],
    )


def load_page_timings(path: str | None) -> list[dict]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["pages"]


def paste_turning_page(canvas, page, origin: tuple[int, int], progress: float) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    page_width, page_height = page.size
    fold_width = max(1, int(page_width * (1.0 - progress)))
    folded_page = page.resize((fold_width, page_height), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    strips = 32
    skew = int(page_width * 0.08 * (1.0 - progress))
    for index in range(strips):
        top = page_height * index // strips
        bottom = page_height * (index + 1) // strips
        center = (top + bottom) / (2 * page_height)
        offset = int(skew * (center - 0.5))
        strip = folded_page.crop((0, top, fold_width, bottom))
        layer.paste(strip, (origin[0] + offset, origin[1] + top))

    edge_top = origin[0] + fold_width - skew // 2
    edge_bottom = origin[0] + fold_width + skew // 2
    edge_y = origin[1]
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.line(
        (edge_top + 4, edge_y, edge_bottom + 4, edge_y + page_height),
        fill=(25, 20, 15, int(100 * (1.0 - progress))),
        width=max(4, int(page_width * 0.018)),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, int(page_width * 0.012))))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(layer)

    highlight = ImageDraw.Draw(canvas)
    highlight.line(
        (edge_top, edge_y, edge_bottom, edge_y + page_height),
        fill=(255, 255, 255, int(80 * (1.0 - progress))),
        width=max(2, int(page_width * 0.006)),
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def locate_progress(source: str, words: list[dict]) -> list[dict]:
    """Map ASR word timestamps to manuscript offsets using global alignment.

    A per-word exact search drifts badly when one Chinese word is misrecognized.
    Aligning the complete ASR character stream first prevents each local error
    from advancing the manuscript cursor artificially.
    """
    manuscript = normalize_text(source)
    asr_tokens = [normalize_text(word["word"]) for word in words]
    asr_tokens = [token for token in asr_tokens if token]
    asr_text = "".join(asr_tokens)
    if not manuscript or not asr_text:
        return []

    matcher = difflib.SequenceMatcher(None, asr_text, manuscript, autojunk=False)
    asr_to_source: dict[int, int] = {}
    for tag, asr_start, asr_end, source_start, source_end in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(asr_end - asr_start + 1):
                asr_to_source[asr_start + offset] = source_start + offset
        elif tag in {"replace", "delete"}:
            # Replace mismatched text by the nearest source anchor, without
            # consuming the rest of the manuscript for every ASR error.
            for offset in range(asr_end - asr_start + 1):
                asr_to_source[asr_start + offset] = source_start

    timeline = []
    asr_offset = 0
    previous_char = 0
    token_index = 0
    for word in words:
        token = normalize_text(word["word"])
        if not token:
            continue
        asr_offset += len(token)
        source_char = asr_to_source.get(asr_offset, previous_char)
        source_char = max(previous_char, min(source_char, len(manuscript)))
        timeline.append({"start": float(word["start"]), "end": float(word["end"]), "char": source_char})
        previous_char = source_char
        token_index += 1
    return timeline


def progress_at(timeline: list[dict], seconds: float) -> int:
    progress = 0
    for item in timeline:
        if item["start"] > seconds:
            break
        progress = max(progress, item["char"])
    return progress


def find_font(font_arg: str | None, size: int) -> ImageFont.FreeTypeFont:
    from PIL import ImageFont

    candidates = [
        font_arg,
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    raise FileNotFoundError(
        "No Chinese font found. Install one with "
        "'apt-get update && apt-get install -y fonts-noto-cjk', "
        "or pass --font with a .ttf/.ttc/.otf font path."
    )


def wrap_pages(text: str, font: ImageFont.FreeTypeFont, width: int, height: int, margin: int) -> list[str]:
    from PIL import Image, ImageDraw

    probe = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(probe)
    lines: list[str] = []
    current = ""
    for char in text.replace("\r", ""):
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        candidate = current + char
        if draw.textbbox((0, 0), candidate, font=font)[2] > width - 2 * margin:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    line_height = int(font.size * 1.8)
    per_page = max(1, (height - 2 * margin) // line_height)
    return ["\n".join(lines[i : i + per_page]) for i in range(0, len(lines), per_page)]


def write_srt(segments: list[dict], path: Path) -> None:
    def stamp(seconds: float) -> str:
        millis = int(round(seconds * 1000))
        hours, millis = divmod(millis, 3_600_000)
        minutes, millis = divmod(millis, 60_000)
        seconds, millis = divmod(millis, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    entries = []
    for index, item in enumerate(segments, 1):
        entries.append(f"{index}\n{stamp(item['start'])} --> {stamp(item['end'])}\n{item['text']}")
    path.write_text("\n\n".join(entries) + "\n", encoding="utf-8")


def transcribe(
    audio: Path,
    model_name: str,
    language: str,
    model_dir: str | None,
    device: str,
    compute_type: str,
    download_timeout: int,
) -> tuple[list[dict], float]:
    # faster-whisper downloads CTranslate2 models through huggingface_hub.
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", str(download_timeout))
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", str(download_timeout))
    # Some environments can reach Hugging Face but cannot authenticate to the
    # Xet CAS endpoint. The regular Hub download path works without a token.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit("Install dependencies first: pip install -r requirements-video.txt") from exc

    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=model_dir,
    )
    segments, info = model.transcribe(str(audio), language=language, word_timestamps=True, vad_filter=True)
    result = []
    for segment in segments:
        words = [
            {"word": word.word, "start": word.start, "end": word.end}
            for word in (segment.words or [])
            if word.start is not None and word.end is not None
        ]
        result.append({"start": segment.start, "end": segment.end, "text": segment.text.strip(), "words": words})
    return result, float(info.duration)


def build_video(args: argparse.Namespace) -> None:
    import numpy as np
    from PIL import Image, ImageDraw

    try:
        from moviepy import AudioFileClip, VideoClip
    except ImportError as exc:
        raise SystemExit("Install dependencies first: pip install -r requirements-video.txt") from exc

    audio = Path(args.audio).resolve()
    output = Path(args.output).resolve()
    duration = audio_duration(audio)
    image_files = load_image_files(args.images_dir)
    page_timings = load_page_timings(args.timings)
    if page_timings and image_files and len(page_timings) > len(image_files):
        raise SystemExit("--timings page count cannot exceed the PNG image count")
    if args.average_pages and not image_files:
        raise SystemExit("--images-dir must contain at least one PNG image")
    if args.timings and not page_timings:
        raise SystemExit("--timings must contain a non-empty pages list")

    if args.average_pages or page_timings:
        source = ""
        segments = []
        timeline = []
    else:
        manuscript = Path(args.text).resolve()
        source = manuscript.read_text(encoding="utf-8")
        segments, duration = transcribe(
            audio,
            args.model,
            args.language,
            args.model_dir,
            args.device,
            args.compute_type,
            args.download_timeout,
        )
        words = [word for segment in segments for word in segment["words"]]
        timeline = locate_progress(source, words)

    output.parent.mkdir(parents=True, exist_ok=True)
    if segments:
        write_srt(segments, output.with_suffix(".srt"))
    output.with_suffix(".json").write_text(
        json.dumps({"segments": segments, "timeline": timeline}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    font = find_font(args.font, args.font_size) if source else None
    pages = wrap_pages(source, font, args.width, args.height, args.margin) if source else []
    text_len = max(1, len(normalize_text(source)))
    page_starts = []
    page_offset = 0
    for page in pages:
        page_starts.append(page_offset)
        page_offset += len(normalize_text(page))
    image_cache = {}
    background = (250, 247, 239)
    foreground = (42, 39, 34)
    accent = (190, 66, 46)
    page_number_font = find_font(args.font, 20)

    def frame(seconds: float):
        progress = progress_at(timeline, seconds)
        page_index = 0
        if page_timings:
            page_timing_index = min(
                len(page_timings) - 1,
                max(0, next((index - 1 for index, item in enumerate(page_timings[1:], 1) if seconds < item["start"]), len(page_timings) - 1)),
            )
            page_index = page_timing_index
            progress = seconds / max(duration, 0.001)
        elif args.average_pages:
            page_index = min(len(image_files) - 1, int(len(image_files) * seconds / max(duration, 0.001)))
            progress = min(1.0, seconds / max(duration, 0.001))
        elif not timeline:
            progress = int(text_len * min(1.0, seconds / max(duration, 0.001)))
            page_index = min(len(pages) - 1, max(0, next(
                (index - 1 for index, start in enumerate(page_starts[1:], 1) if progress < start),
                len(page_starts) - 1,
            )))
        else:
            image_index = min(len(image_files) - 1, int(len(image_files) * seconds / max(duration, 0.001)))
            page_index = image_index
        image = Image.new("RGBA", (args.width, args.height), (*background, 255))
        draw = ImageDraw.Draw(image)
        if image_files:
            def get_page(index: int):
                if index not in image_cache:
                    with Image.open(image_files[index]) as source_image:
                        page_image = source_image.convert("RGB")
                        page_image.thumbnail((args.width, args.height), Image.Resampling.LANCZOS)
                        image_cache[index] = page_image.copy()
                return image_cache[index]

            image_index = page_index
            if page_timings:
                image_index = int(page_timings[page_index].get("image_index", page_index))
            page_image = get_page(image_index)
            if page_timings and page_timing_index > 0:
                previous_timing = page_timings[page_timing_index - 1]
                previous_image_index = int(previous_timing.get("image_index", page_timing_index - 1))
                transition = min(args.transition, max(0.1, float(page_timings[page_timing_index].get("duration", args.transition))))
                elapsed = seconds - float(page_timings[page_timing_index]["start"])
                if 0 <= elapsed < transition:
                    old_image = get_page(previous_image_index)
                    progress_turn = elapsed / max(transition, 0.001)
                    old_x = (args.width - old_image.width) // 2
                    old_y = (args.height - old_image.height) // 2
                    image.paste(page_image, ((args.width - page_image.width) // 2, (args.height - page_image.height) // 2))
                    paste_turning_page(image, old_image, (old_x, old_y), progress_turn)
                else:
                    image.paste(page_image, ((args.width - page_image.width) // 2, (args.height - page_image.height) // 2))
            else:
                image.paste(page_image, ((args.width - page_image.width) // 2, (args.height - page_image.height) // 2))
        else:
            line_height = int(font.size * 1.8)
            page_text = pages[page_index]
            draw.text((args.margin, args.margin), page_text, font=font, fill=foreground, spacing=int(font.size * 0.8))
            local_progress = max(0, progress - page_starts[page_index])
            visible_count = 0
            cursor_line = 0
            cursor_column = 0
            for line_index, line in enumerate(page_text.split("\n")):
                line_count = len(normalize_text(line))
                if local_progress <= visible_count + line_count:
                    cursor_line = line_index
                    cursor_column = max(0, min(len(line), local_progress - visible_count))
                    break
                visible_count += line_count
            cursor_x = args.margin + int(draw.textlength(page_text.split("\n")[cursor_line][:cursor_column], font=font))
            cursor_y = args.margin + cursor_line * line_height
            draw.line((cursor_x, cursor_y + 4, cursor_x, cursor_y + font.size + 8), fill=accent, width=3)
        draw.rectangle((args.margin, args.height - 34, args.width - args.margin, args.height - 28), fill=(225, 218, 205))
        draw.rectangle(
            (args.margin, args.height - 34,
             args.margin + int((args.width - 2 * args.margin) * progress / text_len), args.height - 28),
            fill=accent,
        )
        total_pages = len(page_timings) if page_timings else (len(image_files) if image_files else len(pages))
        visible_page_number = page_index + 1 if not page_timings else (page_index + 1)
        draw.text((args.margin, args.height - 24), f"{visible_page_number} / {total_pages}", font=page_number_font, fill=(110, 103, 95))
        return np.array(image.convert("RGB"))

    clip = VideoClip(frame_function=frame, duration=duration)
    audio_clip = AudioFileClip(str(audio))
    clip = clip.with_audio(audio_clip)

    temp_output = output.with_suffix(".tmp.mp4")
    if temp_output.exists():
        temp_output.unlink()
    if output.exists():
        output.unlink()

    try:
        clip.write_videofile(str(temp_output), fps=args.fps, codec="libx264", audio_codec="aac", preset="medium")
        temp_output.replace(output)
    finally:
        audio_clip.close()
        clip.close()
        if temp_output.exists() and temp_output != output:
            temp_output.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Make a manuscript-following reading video.")
    parser.add_argument("--audio", required=True, help="Narration MP3/WAV")
    parser.add_argument("--text", default=str(ROOT / "data/book.txt"), help="UTF-8 manuscript")
    parser.add_argument("--images-dir", default=None, help="Optional directory of PNG page images")
    parser.add_argument("--timings", default=None, help="JSON page timings generated by page_timings.py")
    parser.add_argument("--average-pages", action="store_true", help="Show pages for equal durations without Whisper")
    parser.add_argument("--output", default=str(ROOT / "output/reading.mp4"))
    parser.add_argument("--model", default="small", help="tiny, base, small, medium, large-v3")
    parser.add_argument("--model-dir", default=None, help="Local Whisper model cache directory")
    parser.add_argument("--language", default="zh", help="Whisper language code")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Inference device")
    parser.add_argument("--compute-type", default="int8", help="CTranslate2 type, e.g. int8 or float16")
    parser.add_argument("--download-timeout", type=int, default=300, help="Model download timeout in seconds")
    parser.add_argument("--font", default=None, help="CJK font file")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--font-size", type=int, default=34)
    parser.add_argument("--margin", type=int, default=100)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--transition", type=float, default=0.8, help="Page-turn duration in seconds")
    build_video(parser.parse_args())


if __name__ == "__main__":
    main()