"""
Narrate a book with your own cloned voice using XTTS-v2 (coqui-tts) — free.

WHAT IT DOES
  1. Loads XTTS-v2 and clones the voice from REFERENCE_AUDIO (your sample.mp3).
  2. Splits BOOK_FILE into small chunks (sentence-packed, <= MAX_CHARS).
  3. Generates each chunk, saving output/chunks/chunk_00001.wav ... (RESUMABLE:
     re-running skips chunks that already exist, so a crash/disconnect is safe).
  4. Concatenates every chunk into output/audiobook.wav (+ .mp3) via ffmpeg.

RUN
  Local (CPU, slow -> overnight):   python narrate_book.py
  Colab (free GPU, ~1-3h):          upload this file + sample.mp3 + book.txt, then
                                    !pip -q install coqui-tts soundfile
                                    !python narrate_book.py
  First run downloads the ~1.8GB XTTS-v2 model (one time).

TIP: set TEST_LIMIT = 3 for a quick smoke test, then TEST_LIMIT = 0 for the full book.
NOTE: XTTS-v2 is non-commercial (Coqui Public Model License); clone only voices you may use.
"""

import os
import re
import sys
import glob
import time
import subprocess

# ----------------------------- CONFIG -----------------------------
BOOK_FILE       = "data/book.txt"   # UTF-8 text of the book to narrate
REFERENCE_AUDIO = "data/reference/ref_enhanced.wav" # VoiceFixer-enhanced (denoised + de-muffled, 44.1kHz). From ref.wav
LANGUAGE        = "zh-cn"           # your book is Chinese. Use "en" for English, "ja", "ko", etc.
OUTPUT_DIR      = "output/xtts"
MAX_CHARS       = 80               # per-chunk cap: ~80 for zh-cn/ja/ko (XTTS limit), up to ~220 for en
SENTENCE_PAUSE  = 0.30            # seconds of silence inserted between chunks
PARAGRAPH_PAUSE = 0.65           # seconds of silence at the end of a paragraph
TEST_LIMIT      = 0               # 0 = whole book; N>0 = only the first N chunks (smoke test)
MAKE_MP3        = True            # also encode output/audiobook.mp3
TEMPERATURE     = 0.65           # XTTS sampling temperature (lower = steadier, higher = more expressive)
# ------------------------------------------------------------------

SAMPLE_RATE = 24000  # XTTS-v2 output sample rate

# Resolve relative paths against the PROJECT ROOT (parent of this src/ folder), so
# data/ and output/ live at the project root regardless of where you launch from.
_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
ROOT = os.path.dirname(_HERE)
def _resolve(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)
BOOK_FILE = _resolve(BOOK_FILE)
REFERENCE_AUDIO = _resolve(REFERENCE_AUDIO)
OUTPUT_DIR = _resolve(OUTPUT_DIR)
CHUNK_DIR = os.path.join(OUTPUT_DIR, "chunks")

# ffmpeg executable for the final concat. Prefer the trusted static build by full path.
_FFMPEG_BIN = r"C:\Program Files\ffmpeg-master-latest-win64-gpl\bin"
if os.path.isdir(_FFMPEG_BIN):
    os.environ["PATH"] = _FFMPEG_BIN + os.pathsep + os.environ["PATH"]
_FFMPEG_EXE = os.path.join(_FFMPEG_BIN, "ffmpeg.exe")
if not os.path.isfile(_FFMPEG_EXE):
    _FFMPEG_EXE = "ffmpeg"  # fall back to PATH (Colab/Linux)

# coqui-tts (torch>=2.9) uses torchcodec for audio IO, which needs FFmpeg *shared* libraries
# (avutil-59/avcodec-61/avformat-61 = FFmpeg 7.1). The "-gpl" build is static (no DLLs), so we
# register a shared build's DLLs for torchcodec. NOTE: we deliberately do NOT add this to PATH,
# so the concat below keeps using the trusted static ffmpeg.exe -- a freshly-downloaded shared
# ffmpeg.exe can trip Windows Defender (WinError 225).
_FFMPEG_SHARED_BIN = r"C:\Users\qitia\ffmpeg-shared-7.1\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\bin"
if os.name == "nt" and os.path.isdir(_FFMPEG_SHARED_BIN):
    try:
        os.add_dll_directory(_FFMPEG_SHARED_BIN)
    except (AttributeError, OSError):
        pass


# ----------------------------- TEXT CHUNKING -----------------------------
def split_sentences(paragraph: str):
    """Split a paragraph into sentences on . ! ? … (English) and 。！？ (Chinese)."""
    paragraph = re.sub(r"\s+", " ", paragraph).strip()
    if not paragraph:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?…。！？])\s*", paragraph) if s.strip()]


def split_long(sentence: str, max_chars: int):
    """Break an over-long sentence on clause punctuation (EN + CJK), then hard-wrap."""
    if len(sentence) <= max_chars:
        return [sentence]
    pieces, buf = [], ""
    for part in re.split(r"(?<=[,;:，；：、])\s*", sentence):
        if len(part) > max_chars:  # still too long
            if " " in part:                       # space-delimited (English): wrap on words
                for word in part.split(" "):
                    if len(buf) + len(word) + 1 > max_chars and buf:
                        pieces.append(buf.strip())
                        buf = ""
                    buf += word + " "
            else:                                 # CJK (no spaces): fixed-width slicing
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
    """Return a list of (text, pause_after) chunks, sentence-packed up to MAX_CHARS."""
    chunks = []
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    for para in paragraphs:
        buf = ""
        para_chunks = []
        for sentence in split_sentences(para):
            for piece in split_long(sentence, MAX_CHARS):
                if len(buf) + len(piece) + 1 > MAX_CHARS and buf:
                    para_chunks.append(buf.strip())
                    buf = ""
                buf += piece + " "
        if buf.strip():
            para_chunks.append(buf.strip())
        for i, c in enumerate(para_chunks):
            last_in_para = (i == len(para_chunks) - 1)
            chunks.append((c, PARAGRAPH_PAUSE if last_in_para else SENTENCE_PAUSE))
    return chunks


# ----------------------------- AUDIO -----------------------------
def load_model():
    """Load XTTS-v2 and return the underlying model plus precomputed speaker latents."""
    import torch
    from TTS.api import TTS

    os.environ.setdefault("COQUI_TOS_AGREED", "1")  # auto-accept XTTS non-commercial license
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[model] device = {device}")
    if device == "cpu":
        print("[model] CPU detected -> generation will be slow. A full book may take many hours.")

    api = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    model = api.synthesizer.tts_model  # underlying Xtts instance

    if not os.path.isfile(REFERENCE_AUDIO):
        sys.exit(f"[error] reference audio not found: {REFERENCE_AUDIO}")
    print(f"[model] computing voice latents from {REFERENCE_AUDIO} ...")
    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
        audio_path=[REFERENCE_AUDIO], gpt_cond_len=30, max_ref_length=60
    )
    return model, gpt_cond_latent, speaker_embedding


def synth_chunk(model, gpt_cond_latent, speaker_embedding, text, pause_after, out_path):
    import numpy as np
    import soundfile as sf

    out = model.inference(
        text=text,
        language=LANGUAGE,
        gpt_cond_latent=gpt_cond_latent,
        speaker_embedding=speaker_embedding,
        temperature=TEMPERATURE,
        length_penalty=1.0,
        repetition_penalty=2.0,
        top_k=50,
        top_p=0.85,
        enable_text_splitting=True,
    )
    wav = np.asarray(out["wav"], dtype=np.float32)
    if pause_after > 0:
        wav = np.concatenate([wav, np.zeros(int(SAMPLE_RATE * pause_after), dtype=np.float32)])
    sf.write(out_path, wav, SAMPLE_RATE, subtype="PCM_16")  # PCM_16 so ffmpeg concat -c copy works


def concat_audio(chunk_paths):
    list_path = os.path.join(OUTPUT_DIR, "_concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in chunk_paths:
            rel = os.path.relpath(p, OUTPUT_DIR).replace("\\", "/")
            f.write(f"file '{rel}'\n")

    print("[concat] building audiobook.wav ...")
    subprocess.run(
        [_FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", "-i", "_concat_list.txt", "-c", "copy", "audiobook.wav"],
        cwd=OUTPUT_DIR, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"[done] {os.path.join(OUTPUT_DIR, 'audiobook.wav')}")

    if MAKE_MP3:
        print("[concat] encoding audiobook.mp3 ...")
        subprocess.run(
            [_FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0", "-i", "_concat_list.txt",
             "-c:a", "libmp3lame", "-q:a", "4", "audiobook.mp3"],
            cwd=OUTPUT_DIR, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"[done] {os.path.join(OUTPUT_DIR, 'audiobook.mp3')}")


# ----------------------------- MAIN -----------------------------
def main():
    if not os.path.isfile(BOOK_FILE):
        sys.exit(f"[error] {BOOK_FILE} not found. Put your book text (UTF-8) there and re-run.")
    os.makedirs(CHUNK_DIR, exist_ok=True)

    with open(BOOK_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = build_chunks(text)
    total = len(chunks)
    if total == 0:
        sys.exit(f"[error] no text found in {BOOK_FILE}.")
    chars = sum(len(c) for c, _ in chunks)
    print(f"[plan] {total} chunks, ~{chars:,} chars, est. ~{chars/1000:.0f} min of audio.")

    todo = chunks if TEST_LIMIT <= 0 else chunks[:TEST_LIMIT]
    if TEST_LIMIT > 0:
        print(f"[plan] TEST_LIMIT={TEST_LIMIT} -> generating only the first {len(todo)} chunks. "
              f"Set TEST_LIMIT=0 for the whole book.")

    model, gpt_cond_latent, speaker_embedding = load_model()

    start = time.time()
    done = 0
    for idx, (chunk_text, pause_after) in enumerate(todo, 1):
        out_path = os.path.join(CHUNK_DIR, f"chunk_{idx:05d}.wav")
        side_path = os.path.join(CHUNK_DIR, f"chunk_{idx:05d}.txt")
        # content-aware resume: reuse only if the audio exists AND its saved text matches this chunk
        if (os.path.isfile(out_path) and os.path.getsize(out_path) > 0
                and os.path.isfile(side_path)
                and open(side_path, encoding="utf-8").read() == chunk_text):
            continue
        synth_chunk(model, gpt_cond_latent, speaker_embedding, chunk_text, pause_after, out_path)
        with open(side_path, "w", encoding="utf-8") as f:
            f.write(chunk_text)
        done += 1
        elapsed = time.time() - start
        avg = elapsed / done
        remaining = avg * (len(todo) - idx)
        print(f"[{idx}/{len(todo)}] wrote {os.path.basename(out_path)} "
              f"({len(chunk_text)} chars, {avg:.1f}s/chunk, ETA {remaining/60:.1f} min)")

    # delete stale chunks beyond the current length (left over from a previous, longer/different book)
    for p in glob.glob(os.path.join(CHUNK_DIR, "chunk_*.wav")):
        if int(os.path.basename(p)[6:11]) > len(todo):
            os.remove(p)
            if os.path.exists(p[:-4] + ".txt"):
                os.remove(p[:-4] + ".txt")

    # concat ONLY the current range (explicit order, not a glob) so nothing stale sneaks in
    chunk_paths = [os.path.join(CHUNK_DIR, f"chunk_{i:05d}.wav") for i in range(1, len(todo) + 1)]
    concat_audio(chunk_paths)
    print(f"[all done] {len(chunk_paths)} chunks in {(time.time()-start)/60:.1f} min total.")


if __name__ == "__main__":
    main()
