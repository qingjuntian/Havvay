# Reading Studio Service

The service workflow covers two book sources: a laid-out PDF, or user-provided images with one matching text per image. Both sources enter the same page/text review, reference-audio preprocessing and review, first-five-page audio/video preview, and full audiobook/video workflow. Validate each stage on AutoDL before treating the service as production-ready.

## AutoDL Setup

Use a persistent AutoDL data volume for both the SQLite database and book artifacts. This example uses `/root/autodl-tmp/reading-service`; verify that this location survives the instance lifecycle you use.

Install the API/video dependencies in a service environment. Keep the F5 environment separate if its PyTorch/Transformers requirements conflict with the web stack:

```bash
cd /root/autodl-tmp/reading
python3 -m venv .venv-service
source .venv-service/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-video.txt -r requirements-service.txt
apt-get update
apt-get install -y redis-server ffmpeg
```

Set persistent paths and start Redis:

```bash
export READING_SERVICE_HOME=/root/autodl-tmp/reading-service
export READING_REDIS_URL=redis://127.0.0.1:6379/0
export READING_VIDEO_PYTHON=/root/autodl-tmp/reading/.venv-service/bin/python
export READING_F5_PYTHON=/root/miniconda3/envs/f5/bin/python
mkdir -p "$READING_SERVICE_HOME/redis"
redis-server --dir "$READING_SERVICE_HOME/redis" --appendonly yes
```

Start the worker and API in separate terminals, both from the project root and with the service environment active:

```bash
cd /root/autodl-tmp/reading
source .venv-service/bin/activate
export READING_SERVICE_HOME=/root/autodl-tmp/reading-service
export READING_REDIS_URL=redis://127.0.0.1:6379/0
export READING_VIDEO_PYTHON=/root/autodl-tmp/reading/.venv-service/bin/python
export READING_F5_PYTHON=/root/miniconda3/envs/f5/bin/python
rq worker reading
```

```bash
cd /root/autodl-tmp/reading
source .venv-service/bin/activate
export READING_SERVICE_HOME=/root/autodl-tmp/reading-service
export READING_REDIS_URL=redis://127.0.0.1:6379/0
export READING_VIDEO_PYTHON=/root/autodl-tmp/reading/.venv-service/bin/python
export READING_F5_PYTHON=/root/miniconda3/envs/f5/bin/python
uvicorn service.app:app --host 127.0.0.1 --port 8000
```

For a restricted development session, forward the port over SSH:

```bash
ssh -L 8000:127.0.0.1:8000 user@autodl-host
```

Then open `http://127.0.0.1:8000`. Do not expose this unauthenticated first release to the public internet. Add authentication and TLS before wider access.

## AutoDL Boot And Recovery

Install the AutoDL custom-startup hook once from the project directory:

```bash
cd /root/autodl-tmp/reading-service-dev
bash scripts/autodl_reading_service.sh install-autostart
bash scripts/autodl_reading_service.sh check-autostart
```

AutoDL's `customer-cmd` startup process runs `/etc/autodl.sh` on each container boot. The installer adds a marked, idempotent block to that hook and creates a timestamped backup before changing an existing file. It does not replace AutoDL's Supervisor configuration. The hook starts Redis with AOF persistence, one RQ worker, the loopback-only API, and a watchdog that checks health every 60 seconds and retries recovery if any service stops.

Boot startup explicitly enables `READING_ALLOW_CPU=1`, so the service still comes up if AutoDL restarts without attaching a GPU. When CUDA is available, F5 uses it; without CUDA, synthesis is allowed on CPU and will be very slow. To require a GPU at boot instead, install with `READING_BOOT_ALLOW_CPU=0` while CUDA is available:

```bash
READING_BOOT_ALLOW_CPU=0 bash scripts/autodl_reading_service.sh install-autostart
```

The startup check validates required executables and Python imports, reports CUDA visibility, checks SQLite integrity, waits for the RQ worker to register, and verifies API health. Worker detection requires a live `rq worker reading` process and a non-expired Redis registration; stale PID files are discarded only after checking process identity, so unrelated processes are never signalled by stop.

Useful commands:

```bash
bash scripts/autodl_reading_service.sh status
bash scripts/autodl_reading_service.sh check
bash scripts/autodl_reading_service.sh check-autostart
bash scripts/autodl_reading_service.sh start
bash scripts/autodl_reading_service.sh backup
bash scripts/autodl_reading_service.sh stop
bash scripts/autodl_reading_service.sh uninstall-autostart
```

`stop` refuses to interrupt queued/running jobs, then stops the watchdog, API, worker, and Redis after creating a backup. `uninstall-autostart` removes only this script's marked block and preserves the rest of `/etc/autodl.sh`; it does not stop services already running. Startup and watchdog logs are under `$READING_SERVICE_HOME/logs/autostart.log` and `watchdog.log`.

Other commands:

```bash
bash scripts/autodl_reading_service.sh status
bash scripts/autodl_reading_service.sh check
bash scripts/autodl_reading_service.sh backup
bash scripts/autodl_reading_service.sh stop
```

`stop` first creates a timestamped backup, then stops the API, worker, and Redis. Backups are stored under `/root/autodl-tmp/reading-service-dev/backups/` and include an SQLite online snapshot, the per-book inputs/outputs, service source, and a Redis RDB snapshot. The script keeps the latest seven backups. It refuses to back up or stop while RQ has queued/running jobs; wait for those jobs to finish and retry. Use `backup` to create a snapshot without stopping services.

Logs and PID files are stored in `$READING_SERVICE_HOME/logs` and `$READING_SERVICE_HOME/pids`. The default service data directory is `/root/autodl-tmp/reading-service-dev/state`. These backups are on the same AutoDL data volume, so copy them to a separate machine/object store for protection against loss of the instance or volume. The restore script uses the existing Conda environment; it does not reinstall packages or recover data if the AutoDL data volume itself has been deleted.

## Current Scope

- Upload a Word/WPS-exported `.pdf`; the worker renders page PNGs and extracts page-level raw/normalized text from that same PDF, plus a checklist. TTS page breaks move to the nearest sentence/clause ending so F5 does not restart mid-sentence; some spoken text can therefore be assigned to an adjacent PDF page for timing. DOCX upload is not supported because server-side reflow cannot guarantee Word pagination or fonts.
- Alternatively, create an image book from the left sidebar, then add PNG/JPEG/WebP images and one non-empty TTS text per image in that book's right-side workspace. The browser sorts filenames numerically; image/text page mapping is kept exactly as submitted, so each page text should preferably end at a complete sentence. Images are normalized to PNG and the source text is retained for the book's history.
- Image books can receive more pages later from the `＋ 添加页面` control above the page preview, including after previous review approvals. New image/text pairs append without rewriting existing reviewed text; saving the combined page text confirms the review and marks dependent media stale. Use the unified 生成与更新 action when ready to regenerate.
- Page text is confirmed by default when PDF or image pages finish preparing, so the voice-reference form is available immediately. Uploading a voice sample continues to reference preprocessing without a separate page/text confirmation step. Users can still edit a page from its preview; saving that page records the review and preserves the normal changed-chunk audio update behavior. Legacy books still waiting at page/text review are automatically marked confirmed when a voice sample is uploaded.
- Saving edited TTS text, replacing a page image, updating a voice reference, or changing the 人名读音词典 does not start synthesis automatically. The unified 生成与更新 action runs only the affected stages; unchanged F5 chunks are reused when both their text/settings and pronunciation-dictionary signature match. Old media remains in history and is marked stale.
- TTS normalization strips ordinary quotation glyphs and Markdown bold markers while preserving Chinese book-title brackets (`《》`), the enclosed words, and sentence punctuation; it also converts common dates, ranges, percentages, counts, ages, and centuries to Chinese spoken forms. Figure/table captions are excluded by default but are listed in review and can be added to their page's TTS text; the original PDF remains the layout reference.
- Each book has an optional 人名读音词典 in its workspace. Enter a JSON object mapping a Chinese name/phrase to one tone-numbered pinyin syllable per character, such as `{"单于": "shan4 yu2"}`. F5 applies it during Chinese G2P; the displayed source text and page-timing alignment stay unchanged. Saving the dictionary invalidates dependent audio/video and waits for the unified 生成与更新 action.
- Generate the first five complete pages as audio and video before generating final full-book media.
- Book state, immutable artifact versions, SHA-256 values, jobs, and approval events are stored in SQLite.
- Redis/RQ runs background jobs. Run exactly one `rq worker reading` process to keep GPU inference sequential.

PDF image rendering requires PyMuPDF, PDF text extraction requires `pypdf`, and image uploads require Pillow. The uploaded PDF is the layout authority; text extraction quality may vary for scanned PDFs or PDFs with unusual text encoding, and the review screen allows manual correction.