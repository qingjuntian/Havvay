r"""
Narrate a book in your cloned voice using F5-TTS (higher quality than XTTS-v2).

RUN WITH THE F5 VENV (not the system python):
    .venv-f5\Scripts\python.exe narrate_book_f5.py

NOTE: F5-TTS is SLOW on CPU (~1-1.5 min per chunk here). Fine for a poem / short text.
For a full ~300k-char book, run this SAME script on a GPU (e.g. Colab T4) - it auto-detects cuda.
Resume-on-crash: re-running skips already-generated chunks.
"""

import os
import sys

# Chinese text + Windows console = cp1252 crash; force UTF-8 and quiet wandb's stdout capture.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
os.environ.setdefault("WANDB_MODE", "disabled")
os.environ.setdefault("WANDB_CONSOLE", "off")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import re
import glob
import time
import math
import subprocess
import argparse
import json
import hashlib
from pathlib import Path

# ----------------------------- CONFIG -----------------------------
BOOK_FILE       = "data/book.txt"   # UTF-8 text to narrate
REFERENCE_AUDIO = "data/reference/919.wav" # 10s trim of ref_enhanced.wav, matched to REF_TEXT (F5 clips refs to 12s)
# Transcript of REFERENCE_AUDIO. Providing it skips the Whisper transcription (faster, no ffmpeg-for-ASR).
# Set to "" to auto-transcribe (needs Whisper + ffmpeg on PATH). MUST match ref.wav if you change it.
REF_TEXT        = "找一个短时间可以不被打扰的地方，坐着或躺着。尽量放开束缚你的物品。"
OUTPUT_DIR      = "output/f5"
MAX_CHARS       = 100              # hard cap for one sentence or clause chunk
SENTENCE_PAUSE  = 0.30
COLON_PAUSE     = 0.35             # shorter but still noticeable pause after a colon / introduction
PARAGRAPH_PAUSE = 0.65
PAGE_PAUSE      = 0.0
TEST_LIMIT      = 0                 # 0 = whole book; N>0 = first N chunks (smoke test)
MAKE_MP3        = True
NFE_STEP        = 32               # denoising steps: higher = better/slower (16 is ~2x faster, lower quality)
SPEED           = 1.0
# ------------------------------------------------------------------

SAMPLE_RATE = 24000
PAGE_BREAK_TOKEN = "<<<BOOK_PAGE_BREAK>>>"
LABEL_LINE_RE = re.compile(
    r"^(?:作品名称|作者|题字出处|创作年代|作品定位|画面基础信息|核心画面元素|风格特点|艺术表现巧思|"
    r"深层精神寓意|相关创作背景|所属系列|创作特点|图文内核的奇妙呼应|相关历史意义|原文|释义|"
    r"底部英文题记)\s*[:：]"
)
HEADING_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百]+章|第[一二三四五六七八九十百]+节|"
    r"[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）|\([一二三四五六七八九十]+\)|\d+\.)"
)


def is_title_like(text: str) -> bool:
    s = text.strip()
    if not s or len(s) > 18:
        return False
    if re.search(r"[。！？!?]$", s):
        return False
    if "：" in s or ":" in s:
        return False
    if re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9、（）()—·\s-]+", s):
        return True
    return False

# Resolve relative paths against the PROJECT ROOT (parent of this src/ folder).
_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
ROOT = os.path.dirname(_HERE)
def _resolve(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def validate_speed(value: str | float) -> float:
    try:
        speed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"speed must be a positive number, got {value!r}") from exc
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError(f"speed must be a positive finite number, got {value!r}")
    return speed


BOOK_FILE = _resolve(BOOK_FILE)
REFERENCE_AUDIO = _resolve(REFERENCE_AUDIO)
OUTPUT_DIR = _resolve(OUTPUT_DIR)
CHUNK_DIR = os.path.join(OUTPUT_DIR, "chunks")
AUDIO_SIGNATURE = f"ref={REFERENCE_AUDIO}|nfe={NFE_STEP}|speed={SPEED}|chars={MAX_CHARS}|page_pause={PAGE_PAUSE}"

# Static ffmpeg on PATH (for Whisper/pydub) + a full-path exe for the concat (avoids AV issues).
_FFMPEG_BIN = r"C:\Program Files\ffmpeg-master-latest-win64-gpl\bin"
if os.path.isdir(_FFMPEG_BIN):
    os.environ["PATH"] = _FFMPEG_BIN + os.pathsep + os.environ["PATH"]
_FFMPEG_EXE = os.path.join(_FFMPEG_BIN, "ffmpeg.exe")
if not os.path.isfile(_FFMPEG_EXE):
    _FFMPEG_EXE = "ffmpeg"

# torchcodec (audio IO) needs FFmpeg *shared* DLLs (FFmpeg 7.1). Register for DLL load only.
_FFMPEG_SHARED_BIN = r"C:\Users\qitia\ffmpeg-shared-7.1\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\bin"
if os.name == "nt" and os.path.isdir(_FFMPEG_SHARED_BIN):
    try:
        os.add_dll_directory(_FFMPEG_SHARED_BIN)
    except (AttributeError, OSError):
        pass


# ----------------------------- TEXT CHUNKING (EN + CJK) -----------------------------
def split_sentences(paragraph: str):
    paragraph = re.sub(r"\s+", " ", paragraph).strip()
    if not paragraph:
        return []
    if LABEL_LINE_RE.match(paragraph):
        return [paragraph]
    # German? No, treat colon as a natural pause boundary in Chinese narration.
    return [s.strip() for s in re.split(r"(?<=[.!?…。！？；;:：])\s*", paragraph) if s.strip()]


def split_long(sentence: str, max_chars: int):
    if len(sentence) <= max_chars:
        return [sentence]
    pieces, buf = [], ""
    for part in re.split(r"(?<=[,;:，；：、])\s*", sentence):
        if len(part) > max_chars:
            if " " in part:
                for word in part.split(" "):
                    if len(buf) + len(word) + 1 > max_chars and buf:
                        pieces.append(buf.strip())
                        buf = ""
                    buf += word + " "
            else:
                if buf.strip():
                    pieces.append(buf.strip())
                    buf = ""
                for i in range(0, len(part), max_chars):
                    pieces.append(part[i:i + max_chars])
            continue
        if len(buf) + len(part) + 1 > max_chars and buf:
            pieces.append(buf.strip())
            buf = ""
        buf += part + " "
    if buf.strip():
        pieces.append(buf.strip())
    return pieces


def build_chunks(text: str, page_pause: float = 0.0):
    chunks = []
    pages = text.split(PAGE_BREAK_TOKEN)
    for page_index, page_text in enumerate(pages):
        page_chunks = []
        for para in [p for p in re.split(r"\n\s*\n", page_text) if p.strip()]:
            stripped = para.strip()
            if HEADING_RE.match(stripped):
                heading = stripped
                pause = 0.8 if re.match(r"第[一二三四五六七八九十百]+章", heading) else 0.6
                page_chunks.append((heading, pause))
                continue
            if is_title_like(stripped) and not page_chunks:
                page_chunks.append((stripped, 0.6))
                continue
            para_chunks = []
            for sentence in split_sentences(para):
                for piece in split_long(sentence, MAX_CHARS):
                    para_chunks.append(piece.strip())
            for i, chunk_text in enumerate(para_chunks):
                is_last = i == len(para_chunks) - 1
                if is_last:
                    pause = PARAGRAPH_PAUSE
                elif chunk_text.rstrip().endswith((":", "：")):
                    pause = COLON_PAUSE
                else:
                    pause = SENTENCE_PAUSE
                page_chunks.append((chunk_text, pause))
        if page_chunks and page_index < len(pages) - 1:
            last_text, last_pause = page_chunks[-1]
            if page_pause > 0 or not HEADING_RE.match(last_text):
                page_chunks[-1] = (last_text, page_pause)
        chunks.extend(page_chunks)
    return chunks


# ----------------------------- MODEL / AUDIO -----------------------------
def load_model():
    import torch
    from f5_tts.api import F5TTS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[model] device = {device}")
    if device == "cpu":
        print("[model] CPU -> F5-TTS is SLOW (~1+ min/chunk). Fine for short text; use a GPU for a full book.")
    f5 = F5TTS(device=device)
    from f5_tts.infer.utils_infer import preprocess_ref_audio_text
    ref_audio, ref_text = preprocess_ref_audio_text(REFERENCE_AUDIO, REF_TEXT)
    print(f"[model] ref_text: {ref_text[:80]!r}")
    return f5, ref_audio, ref_text


def synth_chunk(f5, ref_audio, ref_text, text, pause_after, out_path):
    import numpy as np
    import soundfile as sf
    wav, sr, _ = f5.infer(
        ref_file=ref_audio, ref_text=ref_text, gen_text=text,
        nfe_step=NFE_STEP, speed=SPEED, show_info=lambda *a, **k: None,
    )
    wav = np.asarray(wav, dtype=np.float32)
    if pause_after > 0:
        wav = np.concatenate([wav, np.zeros(int(sr * pause_after), dtype=np.float32)])
    sf.write(out_path, wav, sr, subtype="PCM_16")


def concat_audio(chunk_paths):
    list_path = os.path.join(OUTPUT_DIR, "_concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in chunk_paths:
            f.write(f"file '{os.path.relpath(p, OUTPUT_DIR).replace(chr(92), '/')}'\n")
    print("[concat] building audiobook.wav ...")
    subprocess.run(
        [_FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", "-i", "_concat_list.txt", "-c", "copy", "audiobook.wav"],
        cwd=OUTPUT_DIR, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"[done] {os.path.join(OUTPUT_DIR, 'audiobook.wav')}")
    if MAKE_MP3:
        print("[concat] encoding audiobook.mp3 ...")
        subprocess.run(
            [_FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", "-i", "_concat_list.txt",
             "-c:a", "libmp3lame", "-q:a", "4", "audiobook.mp3"],
            cwd=OUTPUT_DIR, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"[done] {os.path.join(OUTPUT_DIR, 'audiobook.mp3')}")


# ----------------------------- MAIN -----------------------------
def main():
    global BOOK_FILE, REFERENCE_AUDIO, REF_TEXT, OUTPUT_DIR, CHUNK_DIR
    global MAX_CHARS, TEST_LIMIT, MAKE_MP3, NFE_STEP, SPEED, PAGE_PAUSE, AUDIO_SIGNATURE
    parser = argparse.ArgumentParser(description="Generate cloned-voice audio chunks with F5-TTS.")
    parser.add_argument("--book", default=BOOK_FILE, help="Normalized UTF-8 book text")
    parser.add_argument("--reference-audio", default=REFERENCE_AUDIO)
    parser.add_argument("--reference-text", default=None, help="Exact transcript of the reference audio")
    parser.add_argument("--reference-text-file", default=None)
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--speed", type=validate_speed, default=SPEED,
                        help="F5-TTS speed multiplier; > 0.0, where 1.0 is the original pace")
    parser.add_argument("--nfe-step", type=int, default=NFE_STEP)
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS)
    parser.add_argument("--page-pause", type=float, default=PAGE_PAUSE, help="Silence after each page, in seconds")
    parser.add_argument("--test-limit", type=int, default=TEST_LIMIT, help="0 means all chunks")
    parser.add_argument("--no-mp3", action="store_true")
    parser.add_argument("--rerender-chunks", default="", help="Chunk numbers/ranges to regenerate, e.g. 22,41-43")
    parser.add_argument("--chunk-overrides", default=None, help="JSON mapping chunk number to replacement text")
    parser.add_argument("--pronunciation-dict", default=None, help="JSON phrase-to-numbered-pinyin dictionary")
    args = parser.parse_args()

    BOOK_FILE = _resolve(args.book)
    REFERENCE_AUDIO = _resolve(args.reference_audio)
    if args.reference_text_file:
        REF_TEXT = Path(_resolve(args.reference_text_file)).read_text(encoding="utf-8").strip()
    elif args.reference_text is not None:
        REF_TEXT = args.reference_text
    OUTPUT_DIR = _resolve(args.output_dir)
    CHUNK_DIR = os.path.join(OUTPUT_DIR, "chunks")
    MAX_CHARS = args.max_chars
    TEST_LIMIT = args.test_limit
    MAKE_MP3 = not args.no_mp3
    NFE_STEP = args.nfe_step
    SPEED = args.speed
    PAGE_PAUSE = args.page_pause
    AUDIO_SIGNATURE = f"ref={REFERENCE_AUDIO}|ref_text={REF_TEXT}|nfe={NFE_STEP}|speed={SPEED}|chars={MAX_CHARS}|page_pause={PAGE_PAUSE}"
    if args.pronunciation_dict:
        sys.path.insert(0, ROOT)
        from src.pronunciation import pypinyin_phrases, read_pronunciation_file

        pronunciation_entries = read_pronunciation_file(Path(_resolve(args.pronunciation_dict)))
        if pronunciation_entries:
            from pypinyin import load_phrases_dict

            load_phrases_dict(pypinyin_phrases(pronunciation_entries), style="tone2")
            pronunciation_hash = hashlib.sha256(
                json.dumps(pronunciation_entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            AUDIO_SIGNATURE += f"|pronunciation={pronunciation_hash}"

    def selected_chunks(spec: str) -> set[int]:
        selected = set()
        for part in spec.split(","):
            if not part.strip():
                continue
            bounds = [int(value) for value in part.split("-", 1)]
            selected.update(range(bounds[0], bounds[-1] + 1))
        return selected

    rerender = selected_chunks(args.rerender_chunks)
    overrides = {}
    if args.chunk_overrides:
        raw = json.loads(Path(_resolve(args.chunk_overrides)).read_text(encoding="utf-8"))
        overrides = {int(key): value for key, value in raw.get("chunks", raw).items()}

    if not os.path.isfile(BOOK_FILE):
        sys.exit(f"[error] {BOOK_FILE} not found.")
    os.makedirs(CHUNK_DIR, exist_ok=True)
    with open(BOOK_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = build_chunks(text, page_pause=args.page_pause)
    if not chunks:
        sys.exit(f"[error] no text found in {BOOK_FILE}.")
    chars = sum(len(c) for c, _ in chunks)
    print(f"[plan] {len(chunks)} chunks, ~{chars:,} chars.")

    todo = chunks if TEST_LIMIT <= 0 else chunks[:TEST_LIMIT]
    todo = [(overrides.get(index, text), pause) for index, (text, pause) in enumerate(todo, 1)]
    if TEST_LIMIT > 0:
        print(f"[plan] TEST_LIMIT={TEST_LIMIT} -> first {len(todo)} chunks only. Set 0 for the whole book.")

    f5, ref_audio, ref_text = load_model()

    start, done = time.time(), 0
    for idx, (chunk_text, pause_after) in enumerate(todo, 1):
        out_path = os.path.join(CHUNK_DIR, f"chunk_{idx:05d}.wav")
        side_path = os.path.join(CHUNK_DIR, f"chunk_{idx:05d}.txt")
        # content-aware resume: reuse only if the audio exists AND its saved text matches this chunk
        expected_side = AUDIO_SIGNATURE + "\n" + chunk_text
        if (idx not in rerender and os.path.isfile(out_path) and os.path.getsize(out_path) > 0
            and os.path.isfile(side_path)
            and open(side_path, encoding="utf-8").read() == expected_side):
            continue
        synth_chunk(f5, ref_audio, ref_text, chunk_text, pause_after, out_path)
        with open(side_path, "w", encoding="utf-8") as f:
            f.write(expected_side)
        done += 1
        avg = (time.time() - start) / done
        print(f"[{idx}/{len(todo)}] {os.path.basename(out_path)} "
              f"({len(chunk_text)} chars, {avg:.0f}s/chunk, ETA {avg*(len(todo)-idx)/60:.1f} min)")

    # delete stale chunks beyond the current length (left over from a previous, longer/different book)
    for p in glob.glob(os.path.join(CHUNK_DIR, "chunk_*.wav")):
        if int(os.path.basename(p)[6:11]) > len(todo):
            os.remove(p)
            if os.path.exists(p[:-4] + ".txt"):
                os.remove(p[:-4] + ".txt")

    # concat ONLY the current range (explicit order, not a glob) so nothing stale sneaks in
    chunk_paths = [os.path.join(CHUNK_DIR, f"chunk_{i:05d}.wav") for i in range(1, len(todo) + 1)]
    concat_audio(chunk_paths)
    print(f"[all done] {len(chunk_paths)} chunks in {(time.time()-start)/60:.1f} min.")


if __name__ == "__main__":
    main()
