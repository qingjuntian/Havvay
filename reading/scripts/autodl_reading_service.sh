#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${READING_APP_DIR:-/root/autodl-tmp/reading-service-dev}"
SERVICE_HOME="${READING_SERVICE_HOME:-$APP_DIR/state}"
CONDA_PYTHON="${READING_CONDA_PYTHON:-/root/miniconda3/envs/f5/bin/python}"
REDIS_URL="${READING_REDIS_URL:-redis://127.0.0.1:6389/0}"
REDIS_PORT="${READING_REDIS_PORT:-6389}"
API_PORT="${READING_API_PORT:-8000}"
REDIS_DIR="$APP_DIR/redis"
LOG_DIR="$SERVICE_HOME/logs"
PID_DIR="$SERVICE_HOME/pids"
BACKUP_DIR="$APP_DIR/backups"
PYTHONPATH="$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"

export READING_SERVICE_HOME="$SERVICE_HOME"
export READING_REDIS_URL="$REDIS_URL"
export READING_VIDEO_PYTHON="${READING_VIDEO_PYTHON:-$CONDA_PYTHON}"
export READING_F5_PYTHON="${READING_F5_PYTHON:-$CONDA_PYTHON}"
export PYTHONPATH

API_PID_FILE="$PID_DIR/api.pid"
WORKER_PID_FILE="$PID_DIR/worker.pid"

log() {
    printf '[reading-service] %s\n' "$*"
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        log "Missing command: $1"
        return 1
    }
}

check_environment() {
    [[ -d "$APP_DIR/service" ]] || { log "Service code not found: $APP_DIR/service"; return 1; }
    [[ -f "$APP_DIR/src/prepare_docx.py" ]] || { log "DOCX pipeline not found under $APP_DIR/src"; return 1; }
    [[ -x "$CONDA_PYTHON" ]] || { log "F5 Python not executable: $CONDA_PYTHON"; return 1; }
    require_command redis-server
    require_command redis-cli
    require_command curl
    require_command libreoffice
    require_command ffmpeg

    "$CONDA_PYTHON" -c 'import fastapi, fitz, f5_tts, moviepy, pypdf, redis, rq, torch, uvicorn; assert torch.cuda.is_available(), "CUDA is not available"'
    "$CONDA_PYTHON" -c 'import sqlite3,sys; print("Python",sys.version.split()[0],"SQLite",sqlite3.sqlite_version,"CUDA/F5 imports OK")'

    if [[ -f "$SERVICE_HOME/service.sqlite3" ]]; then
        "$CONDA_PYTHON" -c 'import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); result=db.execute("PRAGMA integrity_check").fetchone()[0]; print("SQLite integrity:",result); sys.exit(result != "ok")' "$SERVICE_HOME/service.sqlite3"
    fi
}

pid_is_running() {
    local pid_file="$1"
    [[ -s "$pid_file" ]] || return 1
    local pid
    pid="$(<"$pid_file")"
    [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

rq_worker_active() {
    "$CONDA_PYTHON" -c 'import os; from redis import Redis; from rq import Worker; connection=Redis.from_url(os.environ["READING_REDIS_URL"]); workers=Worker.all(connection=connection); active=[worker for worker in workers if any(queue.name == "reading" for queue in worker.queues) and worker.get_state() in {"idle", "busy"}]; raise SystemExit(not bool(active))' >/dev/null 2>&1
}

start_redis() {
    if redis-cli -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; then
        log "Redis already responds on 127.0.0.1:$REDIS_PORT"
        return
    fi
    mkdir -p "$REDIS_DIR" "$LOG_DIR" "$PID_DIR"
    redis-server \
        --bind 127.0.0.1 \
        --port "$REDIS_PORT" \
        --daemonize yes \
        --dir "$REDIS_DIR" \
        --appendonly yes \
        --pidfile "$PID_DIR/redis.pid" \
        --logfile "$LOG_DIR/redis.log"
    redis-cli -p "$REDIS_PORT" ping | grep -q PONG
    log "Redis started with AOF persistence in $REDIS_DIR"
}

start_worker() {
    if pid_is_running "$WORKER_PID_FILE"; then
        log "RQ worker already running (PID $(<"$WORKER_PID_FILE"))"
        return
    fi
    if rq_worker_active; then
        log "An RQ worker is already registered for the reading queue"
        return
    fi
    rm -f "$WORKER_PID_FILE"
    nohup "$CONDA_PYTHON" -m rq worker reading --url "$REDIS_URL" \
        >>"$LOG_DIR/worker.log" 2>&1 < /dev/null &
    echo "$!" > "$WORKER_PID_FILE"
    log "RQ worker started (PID $(<"$WORKER_PID_FILE")); log: $LOG_DIR/worker.log"
}

start_api() {
    if curl --silent --fail "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then
        log "API already healthy on 127.0.0.1:$API_PORT"
        return
    fi
    if pid_is_running "$API_PID_FILE"; then
        log "API PID $(<"$API_PID_FILE") exists but health check failed"
        return 1
    fi
    rm -f "$API_PID_FILE"
    cd "$APP_DIR"
    nohup "$CONDA_PYTHON" -m uvicorn service.app:app \
        --host 127.0.0.1 --port "$API_PORT" \
        >>"$LOG_DIR/api.log" 2>&1 < /dev/null &
    echo "$!" > "$API_PID_FILE"

    if curl --silent --fail --retry 15 --retry-delay 1 --retry-connrefused \
        "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then
        log "API healthy on 127.0.0.1:$API_PORT; log: $LOG_DIR/api.log"
        return
    fi
    kill -0 "$(<"$API_PID_FILE")" 2>/dev/null || log "API process exited; inspect $LOG_DIR/api.log"
    log "API did not become healthy; inspect $LOG_DIR/api.log"
    return 1
}

backup_state() {
    local timestamp destination
    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    destination="$BACKUP_DIR/$timestamp"
    mkdir -p "$destination"

    if redis-cli -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; then
        if ! "$CONDA_PYTHON" -c 'import os,sys; from redis import Redis; from rq import Queue; from rq.registry import StartedJobRegistry; c=Redis.from_url(os.environ["READING_REDIS_URL"]); q=Queue("reading",connection=c); queued=q.count; started=StartedJobRegistry(queue=q,connection=c).get_job_ids(); print(f"queued={queued}, running={len(started)}"); sys.exit(1 if queued or started else 0)'; then
            log "Backup/stop cancelled: RQ has queued or running jobs; wait for them to finish and retry"
            rmdir "$destination" 2>/dev/null || true
            return 1
        fi
        redis-cli -p "$REDIS_PORT" SAVE >/dev/null
        local redis_dir redis_db
        redis_dir="$(redis-cli -p "$REDIS_PORT" --raw CONFIG GET dir | tail -n 1)"
        redis_db="$(redis-cli -p "$REDIS_PORT" --raw CONFIG GET dbfilename | tail -n 1)"
        [[ -f "$redis_dir/$redis_db" ]] || { log "Redis snapshot not found: $redis_dir/$redis_db"; return 1; }
        cp "$redis_dir/$redis_db" "$destination/redis.rdb"
    fi

    if [[ -f "$SERVICE_HOME/service.sqlite3" ]]; then
        "$CONDA_PYTHON" - "$SERVICE_HOME/service.sqlite3" "$destination/service.sqlite3" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
target = sqlite3.connect(sys.argv[2])
try:
    source.backup(target)
    result = target.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise SystemExit(f"SQLite backup integrity check failed: {result}")
finally:
    target.close()
    source.close()
PY
    fi

    if [[ -d "$SERVICE_HOME/books" ]]; then
        tar -czf "$destination/books.tar.gz" -C "$SERVICE_HOME" books
    fi
    local source_paths=()
    for path in service src tests scripts requirements-service.txt requirements-video.txt; do
        [[ -e "$APP_DIR/$path" ]] && source_paths+=("$path")
    done
    if ((${#source_paths[@]})); then
        tar -czf "$destination/app-source.tar.gz" -C "$APP_DIR" "${source_paths[@]}"
    fi
    printf 'created_utc=%s\napp_dir=%s\nservice_home=%s\n' "$timestamp" "$APP_DIR" "$SERVICE_HOME" > "$destination/manifest.txt"
    log "Backup created: $destination"

    "$CONDA_PYTHON" - "$BACKUP_DIR" <<'PY'
import shutil
import sys
from pathlib import Path

backup_root = Path(sys.argv[1])
backups = sorted(path for path in backup_root.iterdir() if path.is_dir())
for old_backup in backups[:-7]:
    shutil.rmtree(old_backup)
    print(f"Removed expired backup: {old_backup}")
PY
}

status() {
    printf 'App directory: %s\nService data:  %s\n' "$APP_DIR" "$SERVICE_HOME"
    if redis-cli -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; then
        printf 'Redis:         running on 127.0.0.1:%s\n' "$REDIS_PORT"
    else
        printf 'Redis:         stopped\n'
    fi
    if curl --silent --fail "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then
        printf 'API:           healthy on 127.0.0.1:%s\n' "$API_PORT"
    else
        printf 'API:           stopped/unhealthy\n'
    fi
    if pid_is_running "$WORKER_PID_FILE"; then
        printf 'RQ worker:     running (PID %s)\n' "$(<"$WORKER_PID_FILE")"
    elif rq_worker_active; then
        printf 'RQ worker:     active in Redis registry (started outside this script)\n'
    else
        printf 'RQ worker:     stopped\n'
    fi
    if [[ -f "$SERVICE_HOME/service.sqlite3" ]]; then
        ls -lh "$SERVICE_HOME/service.sqlite3"
    else
        printf 'SQLite:        database will be created at first API startup\n'
    fi
}

stop() {
    backup_state
    if pid_is_running "$API_PID_FILE"; then
        kill "$(<"$API_PID_FILE")" 2>/dev/null || true
        rm -f "$API_PID_FILE"
        log "API stopped"
    fi
    if pid_is_running "$WORKER_PID_FILE"; then
        kill "$(<"$WORKER_PID_FILE")" 2>/dev/null || true
        rm -f "$WORKER_PID_FILE"
        log "RQ worker stopped"
    fi
    if redis-cli -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; then
        redis-cli -p "$REDIS_PORT" shutdown nosave
        log "Redis stopped; AOF data remains in $REDIS_DIR"
    fi
}

case "${1:-start}" in
    start)
        mkdir -p "$SERVICE_HOME" "$LOG_DIR" "$PID_DIR" "$REDIS_DIR"
        check_environment
        start_redis
        start_worker
        start_api
        status
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    check)
        check_environment
        log "Environment and persistent state checks passed"
        ;;
    backup)
        check_environment
        backup_state
        ;;
    *)
        printf 'Usage: %s {start|stop|status|check|backup}\n' "$0" >&2
        exit 2
        ;;
esac