# Review archive

These files were moved out of the active project paths because they belong to earlier standalone or Colab experiments, not the current PDF/image-book service workflow. Nothing here has been deleted.

- `legacy/CosyVoice/`: vendored CosyVoice source tree.
- `legacy/notebooks/`: CosyVoice and standalone F5 Colab notebooks.
- `legacy/src/narrate_book.py`: XTTS-v2 standalone runner.
- `legacy/src/demo.py`: ElevenLabs demo.
- `legacy/src/narrate_book_f5_autodl.py`: earlier standalone AutoDL F5 runner.
- `legacy/ARCHITECTURE.md`: overview of the earlier multi-engine audiobook pipeline.

The active service uses `service/worker.py` and `src/narrate_book_f5.py` for F5 synthesis, along with the PDF/image preparation and video modules under `src/`. Review these archived files before deciding whether to delete or restore any of them.
