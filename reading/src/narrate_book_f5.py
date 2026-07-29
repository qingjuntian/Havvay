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
import subprocess

# ----------------------------- CONFIG -----------------------------
BOOK_FILE       = "data/book.txt"   # UTF-8 text to narrate
REFERENCE_AUDIO = "data/reference/ref_f5.wav" # 10s trim of ref_enhanced.wav, matched to REF_TEXT (F5 clips refs to 12s)
# Transcript of REFERENCE_AUDIO. Providing it skips the Whisper transcription (faster, no ffmpeg-for-ASR).
# Set to "" to auto-transcribe (needs Whisper + ffmpeg on PATH). MUST match ref.wav if you change it.
REF_TEXT        = "孩子的成长之路是风雨交加的事实上青春期出现极端情绪是正常的。"
OUTPUT_DIR      = "output/f5"
MAX_CHARS       = 200              # F5-TTS handles longer chunks than XTTS
SENTENCE_PAUSE  = 0.30
PARAGRAPH_PAUSE = 0.65
TEST_LIMIT      = 3                # 0 = whole book; N>0 = first N chunks (smoke test)
MAKE_MP3        = True
NFE_STEP        = 32               # denoising steps: higher = better/slower (16 is ~2x faster, lower quality)
SPEED           = 1.0
# ------------------------------------------------------------------

SAMPLE_RATE = 24000

# Resolve relative paths against the PROJECT ROOT (parent of this src/ folder).
_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
ROOT = os.path.dirname(_HERE)
def _resolve(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)
BOOK_FILE = _resolve(BOOK_FILE)
REFERENCE_AUDIO = _resolve(REFERENCE_AUDIO)
OUTPUT_DIR = _resolve(OUTPUT_DIR)
CHUNK_DIR = os.path.join(OUTPUT_DIR, "chunks")

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
    return [s.strip() for s in re.split(r"(?<=[.!?…。！？])\s*", paragraph) if s.strip()]


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


def build_chunks(text: str):
    chunks = []
    for para in [p for p in re.split(r"\n\s*\n", text) if p.strip()]:
        buf, para_chunks = "", []
        for sentence in split_sentences(para):
            for piece in split_long(sentence, MAX_CHARS):
                if len(buf) + len(piece) + 1 > MAX_CHARS and buf:
                    para_chunks.append(buf.strip())
                    buf = ""
                buf += piece + " "
        if buf.strip():
            para_chunks.append(buf.strip())
        for i, c in enumerate(para_chunks):
            chunks.append((c, PARAGRAPH_PAUSE if i == len(para_chunks) - 1 else SENTENCE_PAUSE))
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
    if not os.path.isfile(BOOK_FILE):
        sys.exit(f"[error] {BOOK_FILE} not found.")
    os.makedirs(CHUNK_DIR, exist_ok=True)
    with open(BOOK_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = build_chunks(text)
    if not chunks:
        sys.exit(f"[error] no text found in {BOOK_FILE}.")
    chars = sum(len(c) for c, _ in chunks)
    print(f"[plan] {len(chunks)} chunks, ~{chars:,} chars.")

    todo = chunks if TEST_LIMIT <= 0 else chunks[:TEST_LIMIT]
    if TEST_LIMIT > 0:
        print(f"[plan] TEST_LIMIT={TEST_LIMIT} -> first {len(todo)} chunks only. Set 0 for the whole book.")

    f5, ref_audio, ref_text = load_model()

    start, done = time.time(), 0
    for idx, (chunk_text, pause_after) in enumerate(todo, 1):
        out_path = os.path.join(CHUNK_DIR, f"chunk_{idx:05d}.wav")
        side_path = os.path.join(CHUNK_DIR, f"chunk_{idx:05d}.txt")
        # content-aware resume: reuse only if the audio exists AND its saved text matches this chunk
        if (os.path.isfile(out_path) and os.path.getsize(out_path) > 0
                and os.path.isfile(side_path)
                and open(side_path, encoding="utf-8").read() == chunk_text):
            continue
        synth_chunk(f5, ref_audio, ref_text, chunk_text, pause_after, out_path)
        with open(side_path, "w", encoding="utf-8") as f:
            f.write(chunk_text)
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
