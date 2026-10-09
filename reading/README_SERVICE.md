# Reading Studio Service

The service workflow covers laid-out PDF upload and preparation, page/text review, reference-audio preprocessing and review, first-five-page audio/video preview, and full audiobook/video generation. Validate each stage on AutoDL before treating the service as production-ready.

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

## Restore After AutoDL Restart

After uploading `scripts/autodl_reading_service.sh` into the project directory, start the services with:

```bash
cd /root/autodl-tmp/reading-service-dev
bash scripts/autodl_reading_service.sh start
```

The script validates the F5/CUDA and PDF/media dependencies, checks SQLite integrity when a database exists, starts Redis with AOF under the data volume, starts one RQ worker, and starts the API on `127.0.0.1:8000`. It is safe to rerun: it checks API health and the Redis RQ worker registry before starting duplicate processes.

GPU is required by default. If AutoDL has temporarily restarted the container without attaching its GPU, the normal start command stops at the CUDA check. To bring up the API in degraded mode, explicitly opt into CPU fallback:

```bash
READING_ALLOW_CPU=1 bash scripts/autodl_reading_service.sh start
```

F5 synthesis can then run on CPU but will be very slow. Restore GPU access from the AutoDL console and run the normal `start` command before generating long previews/books.

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
- Review page images and normalized text, provide the exact voice transcript, and approve each audio/video stage. TTS text remains editable whenever the book has no active job.
- If audio already exists, saving edited TTS text automatically queues a preview/full audio update. Existing chunk WAVs are reused when their text and pause match; changed chunk positions are re-synthesized and the audiobook is rebuilt. Old audio/video artifacts remain in history but are marked stale; video must be regenerated and reviewed again.
- TTS normalization strips quotation glyphs and Markdown bold markers while preserving the quoted words and sentence punctuation, and converts common dates, ranges, percentages, counts, ages, and centuries to Chinese spoken forms. Figure/table captions are excluded by default but are listed in review and can be added to their page's TTS text; the original PDF remains the layout reference.
- Generate the first five complete pages as audio and video before generating final full-book media.
- Book state, immutable artifact versions, SHA-256 values, jobs, and approval events are stored in SQLite.
- Redis/RQ runs background jobs. Run exactly one `rq worker reading` process to keep GPU inference sequential.

Image rendering requires PyMuPDF, and PDF text extraction requires `pypdf`. The uploaded PDF is the layout authority; text extraction quality may vary for scanned PDFs or PDFs with unusual text encoding, and the review screen allows manual correction.