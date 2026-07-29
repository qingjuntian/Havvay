# reading — voice-cloned audiobook toolkit

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
- `.env`, `output/`, and virtual-envs are git-ignored.

## Voice-clone quality ranking (Chinese, observed)
CosyVoice 3 ≥ F5-TTS > XTTS-v2. All are zero-shot; for a bigger jump, fine-tune (e.g. GPT-SoVITS).
