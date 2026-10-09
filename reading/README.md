# reading — voice-cloned audiobook toolkit

For the complete AutoDL installation and PDF-to-MP4 deployment guide, see
[README_AUTODL.md](README_AUTODL.md).

Turn a text file (`data/book.txt`) into an audiobook narrated in a **cloned voice**, using free/open-source TTS. Three engines are provided; **CosyVoice** (Colab) currently gives the best Chinese quality.

> 📐 See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the full technique map and pipeline diagram.

## Structure
```
reading/
├── ARCHITECTURE.md              # technique map + pipeline diagram (Mermaid)
├── src/                         # local Python scripts
│   ├── narrate_book.py          #   XTTS-v2 pipeline (local, CPU-friendly)
│   ├── narrate_book_f5.py       #   F5-TTS pipeline (local; run with the F5 venv)
│   └── demo.py                  #   ElevenLabs TTS quick demo (needs .env API key)
├── notebooks/                   # Colab notebooks (GPU)
│   ├── CosyVoice_Audiobook_Colab.ipynb   # best Chinese quality; two-phase CPU/GPU, resumable
│   └── F5_TTS_Audiobook_Colab.ipynb
├── data/
│   ├── book.txt                 # input text to narrate (UTF-8)
│   ├── samples/                 # raw voice samples (sample.mp3, sample2.mp4)
│   └── reference/               # processed reference clips
│       ├── ref.wav              #   cleaned/normalized (24 kHz)
│       └── ref_enhanced.wav     #   VoiceFixer-enhanced (denoised, 44.1 kHz) -- the one scripts use
├── output/                      # generated audio (git-ignored)
└── .env                         # ELEVENLABS_API_KEY (git-ignored -- never commit)
```

## Quick start

### Colab (recommended, GPU) — CosyVoice
1. Upload `notebooks/CosyVoice_Audiobook_Colab.ipynb` to https://colab.research.google.com.
2. Follow the in-notebook steps: Part 1 (CPU) downloads the model to Drive; Part 2 (GPU) generates.
3. Upload `data/reference/ref_enhanced.wav` and `data/book.txt` when prompted.

### Local — XTTS-v2
```powershell
pip install coqui-tts soundfile pypinyin jieba
python src/narrate_book.py            # writes output/xtts/audiobook.mp3
```

### Local — F5-TTS (separate venv, needs transformers 5.x)
F5-TTS needs `transformers 5.x`, which conflicts with the XTTS/coqui stack in your system Python.
Keep it isolated in its own virtual environment (`.venv-f5`):
```powershell
cd D:\workspace\Havvay\reading

# 1. Create the venv (one-time)
python -m venv .venv-f5

# 2. Install F5 into it (use the venv's own python)
.venv-f5\Scripts\python.exe -m pip install "torch==2.11.0" "torchaudio==2.11.0"
.venv-f5\Scripts\python.exe -m pip install f5-tts soundfile

# 3. Run the pipeline with the venv's python
.venv-f5\Scripts\python.exe src/narrate_book_f5.py   # writes output/f5/audiobook.mp3
```
> Note: F5 on CPU is ~16× realtime (slow). It's here for quality comparison; use the CosyVoice Colab notebook for the full book.

## Virtual environments (venv)
A **venv** is an isolated Python environment — its own `python.exe` and its own `site-packages` —
so one project's dependencies can't clash with another's. This repo uses two environments:

| Environment | Used by | Key dependency |
|-------------|---------|----------------|
| System Python | XTTS-v2 (`narrate_book.py`), ElevenLabs demo | `transformers 4.57.6`, `coqui-tts` |
| `.venv-f5` (in-project, git-ignored) | F5-TTS (`narrate_book_f5.py`) | `transformers 5.x`, `f5-tts` |

The whole trick is **which `python.exe` you call**:
- `python …` → system Python (XTTS env)
- `.venv-f5\Scripts\python.exe …` → the F5 env

Create → install → run (all with the venv's own python — see the F5 section above).
Optionally **activate** it instead, so plain `python` maps to the venv for the shell session:
```powershell
.venv-f5\Scripts\Activate.ps1     # prompt shows (.venv-f5); "python" now = venv python
python src/narrate_book_f5.py
deactivate                        # exit when done
```
(If PowerShell blocks activation: `Set-ExecutionPolicy -Scope Process RemoteSigned` once.)

> A venv **can't be moved** after creation (it bakes in absolute paths). If you relocate the
> project, delete `.venv-f5` and recreate it with the 3 steps above. Venvs are git-ignored on
> purpose — they're rebuilt from the install commands, not stored in git.

## Notes
- Scripts resolve `data/` and `output/` relative to the **project root**, so run them from anywhere.
- All pipelines **chunk** the book, generate each piece, and **stitch** to one `audiobook.mp3`. Resume is content-aware: edit `data/book.txt` and re-run — only changed chunks regenerate.
- Reference-audio quality drives clone quality far more than quantity; a clean ~15 s clip is ideal.

### Laid-out PDF -> page-aligned audiobook video

Export the document to PDF from the Word/WPS installation that defines its final pagination and
fonts. The pipeline renders page images and extracts page text from that same PDF, so the AutoDL
renderer does not reflow the document. Install the Python dependencies first:

```bash
brew install ffmpeg
python3 -m pip install -r requirements-video.txt
```

Run the end-to-end pipeline with the PDF and voice sample:

```bash
python3 src/build_book_video.py \
	--pdf data/第一章社会工作服务的内涵.pdf \
    --voice data/voice.mp3 \
    --ref-text "填写 voice.mp3 中实际说出的完整内容" \
    --f5-python .venv-f5/bin/python \
    --speed 1.2 \
    --output output/book.mp4
```

The PDF route creates page PNGs, normalized page text, F5 chunks, page timing data, and the final
video under `output/book_build/`. The uploaded PDF remains the source of page layout and fonts.

For existing audio and a page-image directory, the lower-level video workflow remains available. First
prepare page text from the authoritative PDF, then generate timings and video:

```bash
python3 src/page_timings.py \
	--pdf data/第一章社会工作服务的内涵.pdf \
	--pages-json output/book_build/book_pages.json \
	--chunks-dir output/f5/chunks \
	--output output/page_timings.json

python3 src/book_video.py \
	--audio data/audiobook.mp3 \
	--images-dir data/第一章第一节 \
	--timings output/page_timings.json \
	--output output/第一章第一节-精确翻页.mp4
```

The timings mode is fully local and does not use Whisper. Page changes use a short paper-like
fold and shadow transition; adjust it with `--transition`, in seconds.

The PDF route places explicit page markers in the TTS input, so chunks do not cross page
boundaries. Page timing sums complete chunk WAV durations rather than proportionally estimating
audio time from character counts. Ordinary page-end padding is removed; heading pauses are kept.

The script writes `reading.mp4`, `reading.srt`, and `reading.json`. The `small` Whisper model is a reasonable starting point for Chinese; use `--model base` for a faster first test or `--model medium` for better recognition if the machine has enough memory. Pass `--font` if the automatic macOS CJK font is not suitable.

For a first run on a long MP3, keep the model in a local directory and increase the download timeout:

```bash
python3 src/book_video.py \
	--audio data/audiobook.mp3 \
	--model base \
	--model-dir .models \
	--download-timeout 600 \
	--output output/reading.mp4
```

The model is downloaded only once. A network timeout during model download does not mean the 50-minute audio is too large; rerun after the model download succeeds.

On Linux, install a Chinese font before rendering, otherwise Pillow will draw Chinese characters as boxes:

```bash
apt-get update
apt-get install -y fonts-noto-cjk
fc-list :lang=zh family | head
```

If you cannot install system packages, upload a Chinese `.ttf`, `.ttc`, or `.otf` file and pass it explicitly:

```bash
python3 src/book_video.py ... --font /root/autodl-tmp/fonts/NotoSansCJK-Regular.ttc
```
- `.env`, `output/`, and virtual-envs are git-ignored.

## Voice-clone quality ranking (Chinese, observed)
CosyVoice 3 ≥ F5-TTS > XTTS-v2. All are zero-shot; for a bigger jump, fine-tune (e.g. GPT-SoVITS).

### One-command PDF to MP4 pipeline

The automated pipeline extracts and normalizes the PDF, trims the voice reference, accepts the
exact `REF_TEXT`, generates F5-TTS chunks, computes page timings, and renders a vertical MP4:

```bash
python3 src/build_book_video.py \
	--pdf data/第一章社会工作服务的内涵.pdf \
	--images-dir data/第一章第一节 \
	--voice data/reference/919.wav \
	--ref-text "第一章 社会工作的内涵，原则及主要领域。随着社会现代化的发展，各种社会问题变得越来越复杂。" \
	--f5-python .venv-f5/bin/python \
	--speed 1.2 \
	--output output/book.mp4
```

Use `--speed 1.0` for the original pace, or any other value supported by F5-TTS. Intermediate
artifacts are stored under `output/book_build/`, and existing F5 chunks are reused when their
text and settings match.

The PDF preparation also writes `book_checklist.json`. It lists explicit figure/table captions
that were skipped from narration for manual review. A page can still contain an undetected table
when the PDF extractor exposes only ordinary text; those cases remain intentionally conservative.

### Manual correction and selective rereading

`page_timings.json` lists the chunks used by each page. To replace only selected chunk text, create
a JSON file such as:

```json
{"chunks": {"22": "四、增进社会关系。"}}
```

Then rerun only that chunk while reusing all other WAV files:

```bash
python src/build_book_video.py ... \
	--chunk-overrides output/chunk_overrides.json \
	--rerender-chunks 22
```

For a page-level correction, inspect that page's `chunks` entries in `page_timings.json` and
include all affected chunk numbers in `--rerender-chunks`; this preserves the rest of the book.

For AutoDL, create or activate a GPU environment first. Keep the image/video dependencies in
the environment that runs the pipeline, and install [requirements-f5-autodl.txt](requirements-f5-autodl.txt)
in the F5 environment:

```bash
python3 -m venv .venv-f5
source .venv-f5/bin/activate
python -m pip install -r requirements-f5-autodl.txt
python -c "import torch; print(torch.cuda.is_available())"
```

Install the pipeline dependencies with `python -m pip install -r requirements-video.txt` in the
environment used to launch `build_book_video.py`. Pass that F5 interpreter with `--f5-python`
when the two environments are separate.
