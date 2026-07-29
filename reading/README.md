# reading — voice-cloned audiobook toolkit

Turn a text file (`data/book.txt`) into an audiobook narrated in a **cloned voice**, using free/open-source TTS. Three engines are provided; **CosyVoice** (Colab) currently gives the best Chinese quality.

## Structure
```
reading/
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
```powershell
.venv-f5\Scripts\python.exe src/narrate_book_f5.py   # writes output/f5/audiobook.mp3
```

## Notes
- Scripts resolve `data/` and `output/` relative to the **project root**, so run them from anywhere.
- All pipelines **chunk** the book, generate each piece, and **stitch** to one `audiobook.mp3`. Resume is content-aware: edit `data/book.txt` and re-run — only changed chunks regenerate.
- Reference-audio quality drives clone quality far more than quantity; a clean ~15 s clip is ideal.
- `.env`, `output/`, and virtual-envs are git-ignored.

## Voice-clone quality ranking (Chinese, observed)
CosyVoice 3 ≥ F5-TTS > XTTS-v2. All are zero-shot; for a bigger jump, fine-tune (e.g. GPT-SoVITS).
