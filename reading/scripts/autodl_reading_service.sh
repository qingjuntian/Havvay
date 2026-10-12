#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${READING_APP_DIR:-/root/autodl-tmp/reading-service-dev}"
SERVICE_HOME="${READING_SERVICE_HOME:-$APP_DIR/state}"
CONDA_PYTHON="${READING_CONDA_PYTHON:-/root/miniconda3/envs/f5/bin/python}"
RQ_CLI="${READING_RQ_CLI:-$(dirname "$CONDA_PYTHON")/rq}"
REDIS_URL="${READING_REDIS_URL:-redis://127.0.0.1:6389/0}"
REDIS_PORT="${READING_REDIS_PORT:-6389}"
API_PORT="${READING_API_PORT:-8000}"
ALLOW_CPU="${READING_ALLOW_CPU:-0}"
REDIS_DIR="$APP_DIR/redis"
LOG_DIR="$SERVICE_HOME/logs"
PID_DIR="$SERVICE_HOME/pids"
BACKUP_DIR="$APP_DIR/backups"
AUTODL_HOOK="${READING_AUTODL_HOOK:-/etc/autodl.sh}"
WATCHDOG_INTERVAL="${READING_WATCHDOG_INTERVAL:-60}"
PYTHONPATH="$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
SCRIPT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")"

export READING_SERVICE_HOME="$SERVICE_HOME"
export READING_REDIS_URL="$REDIS_URL"
export READING_ALLOW_CPU="$ALLOW_CPU"
export READING_VIDEO_PYTHON="${READING_VIDEO_PYTHON:-$CONDA_PYTHON}"
export READING_F5_PYTHON="${READING_F5_PYTHON:-$CONDA_PYTHON}"
export PYTHONPATH

API_PID_FILE="$PID_DIR/api.pid"
WORKER_PID_FILE="$PID_DIR/worker.pid"
WATCHDOG_PID_FILE="$PID_DIR/watchdog.pid"
WATCHDOG_LOG_FILE="$LOG_DIR/watchdog.log"

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
    [[ -f "$APP_DIR/src/prepare_book.py" ]] || { log "PDF pipeline not found under $APP_DIR/src"; return 1; }
    [[ -x "$CONDA_PYTHON" ]] || { log "F5 Python not executable: $CONDA_PYTHON"; return 1; }
    [[ -x "$RQ_CLI" ]] || { log "RQ command not executable: $RQ_CLI"; return 1; }
    require_command redis-server
    require_command redis-cli
    require_command curl
    require_command ffmpeg

    "$CONDA_PYTHON" -c 'import os, fastapi, fitz, f5_tts, moviepy, pypdf, redis, rq, torch, uvicorn; cuda=torch.cuda.is_available(); print("CUDA available:",cuda); assert cuda or os.environ.get("READING_ALLOW_CPU") == "1", "CUDA is unavailable; set READING_ALLOW_CPU=1 only to start in degraded CPU mode"'
    if [[ "$ALLOW_CPU" == "1" ]]; then
        log "CPU fallback enabled; F5 synthesis will be very slow until the GPU is available"
    fi
    "$CONDA_PYTHON" -c 'import sqlite3,sys; print("Python",sys.version.split()[0],"SQLite",sqlite3.sqlite_version,"service/F5 imports OK")'

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

pid_matches_command() {
    local pid="$1"
    local expected="$2"
    local command_line
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    [[ -r "/proc/$pid/cmdline" ]] || return 1
    command_line="$(tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null)"
    [[ "$command_line" == *"$expected"* ]]
}

terminate_managed_process() {
    local pid="$1"
    local expected="$2"
    local attempt
    pid_matches_command "$pid" "$expected" || return 0
    kill -TERM "$pid" 2>/dev/null || true
    for attempt in {1..10}; do
        pid_matches_command "$pid" "$expected" || return 0
        sleep 1
    done
    if pid_matches_command "$pid" "$expected"; then
        kill -KILL "$pid" 2>/dev/null || true
    fi
}

rq_worker_active() {
    "$CONDA_PYTHON" - <<'PY' >/dev/null 2>&1
import os
from pathlib import Path

from redis import Redis
from rq import Worker

connection = Redis.from_url(os.environ["READING_REDIS_URL"])
for worker in Worker.all(connection=connection):
    if not any(queue.name == "reading" for queue in worker.queues):
        continue
    if worker.get_state() not in {"idle", "busy"} or connection.ttl(worker.key) <= 0:
        continue
    cmdline = Path(f"/proc/{worker.pid}/cmdline")
    try:
        command = cmdline.read_bytes().replace(b"\0", b" ").lower()
    except OSError:
        continue
    if b"rq" in command and b"worker" in command and b"reading" in command:
        raise SystemExit(0)
raise SystemExit(1)
PY
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
    if pid_is_running "$WORKER_PID_FILE" && pid_matches_command "$(<"$WORKER_PID_FILE")" "rq worker reading"; then
        if rq_worker_active; then
            log "RQ worker already running (PID $(<"$WORKER_PID_FILE"))"
            return
        fi
        log "RQ worker PID $(<"$WORKER_PID_FILE") has no live Redis heartbeat; restarting it"
        terminate_managed_process "$(<"$WORKER_PID_FILE")" "rq worker reading"
    fi
    if rq_worker_active; then
        log "An RQ worker is already registered for the reading queue"
        return
    fi
    rm -f "$WORKER_PID_FILE"
    nohup "$RQ_CLI" worker reading --url "$REDIS_URL" \
        >>"$LOG_DIR/worker.log" 2>&1 < /dev/null &
    echo "$!" > "$WORKER_PID_FILE"
    local attempt
    for attempt in {1..15}; do
        if rq_worker_active; then
            log "RQ worker started (PID $(<"$WORKER_PID_FILE")); log: $LOG_DIR/worker.log"
            return
        fi
        if ! kill -0 "$(<"$WORKER_PID_FILE")" 2>/dev/null; then
            log "RQ worker exited during startup; inspect $LOG_DIR/worker.log"
            return 1
        fi
        sleep 1
    done
    log "RQ worker process exists but has not registered a live heartbeat; inspect $LOG_DIR/worker.log"
    return 1
}

start_api() {
    if curl --silent --fail "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then
        log "API already healthy on 127.0.0.1:$API_PORT"
        return
    fi
    if pid_is_running "$API_PID_FILE" && pid_matches_command "$(<"$API_PID_FILE")" "uvicorn service.app:app"; then
        log "API PID $(<"$API_PID_FILE") is not healthy; restarting it"
        terminate_managed_process "$(<"$API_PID_FILE")" "uvicorn service.app:app"
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
    if pid_is_running "$WORKER_PID_FILE" && pid_matches_command "$(<"$WORKER_PID_FILE")" "rq worker reading"; then
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
    if pid_is_running "$WATCHDOG_PID_FILE" && pid_matches_command "$(<"$WATCHDOG_PID_FILE")" "$SCRIPT_PATH watch"; then
        kill "$(<"$WATCHDOG_PID_FILE")" 2>/dev/null || true
        rm -f "$WATCHDOG_PID_FILE"
        log "Health watchdog stopped"
    else
        rm -f "$WATCHDOG_PID_FILE"
    fi
    if pid_is_running "$API_PID_FILE" && pid_matches_command "$(<"$API_PID_FILE")" "uvicorn service.app:app"; then
        kill "$(<"$API_PID_FILE")" 2>/dev/null || true
        rm -f "$API_PID_FILE"
        log "API stopped"
    else
        rm -f "$API_PID_FILE"
    fi
    if pid_is_running "$WORKER_PID_FILE" && pid_matches_command "$(<"$WORKER_PID_FILE")" "rq worker reading"; then
        kill "$(<"$WORKER_PID_FILE")" 2>/dev/null || true
        rm -f "$WORKER_PID_FILE"
        log "RQ worker stopped"
    else
        rm -f "$WORKER_PID_FILE"
    fi
    if redis-cli -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; then
        redis-cli -p "$REDIS_PORT" shutdown nosave
        log "Redis stopped; AOF data remains in $REDIS_DIR"
    fi
}

start_all() {
    mkdir -p "$SERVICE_HOME" "$LOG_DIR" "$PID_DIR" "$REDIS_DIR"
    check_environment
    start_redis
    start_worker
    start_api
    status
}

watch_services() {
    [[ "$WATCHDOG_INTERVAL" =~ ^[0-9]+$ ]] && ((WATCHDOG_INTERVAL >= 10)) || {
        log "READING_WATCHDOG_INTERVAL must be an integer of at least 10 seconds"
        return 2
    }
    while true; do
        if ! redis-cli -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG \
            || ! curl --silent --fail "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1 \
            || ! rq_worker_active; then
            log "Watchdog detected an unhealthy service; attempting recovery" >>"$WATCHDOG_LOG_FILE"
            if ! "$SCRIPT_PATH" start >>"$WATCHDOG_LOG_FILE" 2>&1; then
                log "Recovery failed; will retry in ${WATCHDOG_INTERVAL}s" >>"$WATCHDOG_LOG_FILE"
            fi
        fi
        sleep "$WATCHDOG_INTERVAL"
    done
}

start_watchdog() {
    if pid_is_running "$WATCHDOG_PID_FILE" && pid_matches_command "$(<"$WATCHDOG_PID_FILE")" "$SCRIPT_PATH watch"; then
        log "Watchdog already running (PID $(<"$WATCHDOG_PID_FILE"))"
        return
    fi
    rm -f "$WATCHDOG_PID_FILE"
    nohup "$SCRIPT_PATH" watch >>"$WATCHDOG_LOG_FILE" 2>&1 < /dev/null &
    echo "$!" > "$WATCHDOG_PID_FILE"
    if ! pid_matches_command "$(<"$WATCHDOG_PID_FILE")" "$SCRIPT_PATH watch"; then
        log "Watchdog failed to start; inspect $WATCHDOG_LOG_FILE"
        rm -f "$WATCHDOG_PID_FILE"
        return 1
    fi
    log "Watchdog started (PID $(<"$WATCHDOG_PID_FILE")); checking every ${WATCHDOG_INTERVAL}s"
}

install_autostart() {
    local boot_allow_cpu="${READING_BOOT_ALLOW_CPU:-1}"
    [[ "$boot_allow_cpu" == "0" || "$boot_allow_cpu" == "1" ]] || {
        log "READING_BOOT_ALLOW_CPU must be 0 or 1"
        return 2
    }
    "$CONDA_PYTHON" - "$AUTODL_HOOK" "$APP_DIR" "$SERVICE_HOME" "$CONDA_PYTHON" "$REDIS_URL" "$REDIS_PORT" "$API_PORT" "$boot_allow_cpu" <<'PY'
import os
import shlex
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

hook = Path(sys.argv[1])
app_dir, service_home, python, redis_url, redis_port, api_port, allow_cpu = sys.argv[2:]
begin = "# BEGIN READING SERVICE AUTOSTART"
end = "# END READING SERVICE AUTOSTART"
script = Path(app_dir) / "scripts" / "autodl_reading_service.sh"
log = Path(service_home) / "logs" / "autostart.log"
exports = {
    "READING_APP_DIR": app_dir,
    "READING_SERVICE_HOME": service_home,
    "READING_CONDA_PYTHON": python,
    "READING_REDIS_URL": redis_url,
    "READING_REDIS_PORT": redis_port,
    "READING_API_PORT": api_port,
    "READING_ALLOW_CPU": allow_cpu,
}
block = "\n".join([
    begin,
    "(",
    *(f"  export {key}={shlex.quote(value)}" for key, value in exports.items()),
    f"  nohup bash {shlex.quote(str(script))} autostart >>{shlex.quote(str(log))} 2>&1 </dev/null &",
    ")",
    end,
])
hook.parent.mkdir(parents=True, exist_ok=True)
original = hook.read_text(encoding="utf-8") if hook.exists() else "#!/bin/bash\n"
if (begin in original) != (end in original):
    raise SystemExit(f"Incomplete Reading autostart markers in {hook}; refusing to overwrite it")
if begin in original:
    prefix, remainder = original.split(begin, 1)
    _, suffix = remainder.split(end, 1)
    updated = prefix.rstrip() + "\n\n" + block + suffix
else:
    updated = original.rstrip() + "\n\n" + block + "\n"
if updated != original:
    if hook.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = hook.with_name(f"{hook.name}.reading-backup-{timestamp}")
        shutil.copy2(hook, backup)
        print(f"AutoDL hook backup: {backup}")
        mode = hook.stat().st_mode
    else:
        mode = 0o755
    temporary = hook.with_name(f".{hook.name}.reading-tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.chmod(mode & 0o777)
    os.replace(temporary, hook)
print(f"AutoDL startup hook installed: {hook}")
PY
}

uninstall_autostart() {
    "$CONDA_PYTHON" - "$AUTODL_HOOK" <<'PY'
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

hook = Path(sys.argv[1])
begin = "# BEGIN READING SERVICE AUTOSTART"
end = "# END READING SERVICE AUTOSTART"
if not hook.exists():
    print(f"AutoDL startup hook not found: {hook}")
    raise SystemExit(0)
original = hook.read_text(encoding="utf-8")
if (begin in original) != (end in original):
    raise SystemExit(f"Incomplete Reading autostart markers in {hook}; refusing to modify it")
if begin not in original:
    print("Reading service autostart is not installed")
    raise SystemExit(0)
prefix, remainder = original.split(begin, 1)
_, suffix = remainder.split(end, 1)
updated = prefix.rstrip() + "\n" + suffix.lstrip("\n")
timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup = hook.with_name(f"{hook.name}.reading-backup-{timestamp}")
shutil.copy2(hook, backup)
temporary = hook.with_name(f".{hook.name}.reading-tmp")
temporary.write_text(updated, encoding="utf-8")
temporary.chmod(hook.stat().st_mode & 0o777)
os.replace(temporary, hook)
print(f"Removed Reading autostart block; backup: {backup}")
PY
}

check_autostart() {
    [[ -f "$AUTODL_HOOK" ]] || { log "AutoDL startup hook missing: $AUTODL_HOOK"; return 1; }
    grep -Fq "# BEGIN READING SERVICE AUTOSTART" "$AUTODL_HOOK" \
        && grep -Fq "# END READING SERVICE AUTOSTART" "$AUTODL_HOOK" \
        || { log "Reading service boot block is not installed in $AUTODL_HOOK"; return 1; }
    log "AutoDL boot hook installed in $AUTODL_HOOK"
    if pid_is_running "$WATCHDOG_PID_FILE" && pid_matches_command "$(<"$WATCHDOG_PID_FILE")" "$SCRIPT_PATH watch"; then
        log "Health watchdog running (PID $(<"$WATCHDOG_PID_FILE"))"
    else
        log "Health watchdog not running"
        return 1
    fi
}

case "${1:-start}" in
    start)
        start_all
        ;;
    autostart)
        start_all
        start_watchdog
        ;;
    watch)
        watch_services
        ;;
    install-autostart)
        ALLOW_CPU="${READING_BOOT_ALLOW_CPU:-1}"
        [[ "$ALLOW_CPU" == "0" || "$ALLOW_CPU" == "1" ]] || { log "READING_BOOT_ALLOW_CPU must be 0 or 1"; exit 2; }
        export READING_ALLOW_CPU="$ALLOW_CPU"
        mkdir -p "$SERVICE_HOME" "$LOG_DIR" "$PID_DIR" "$REDIS_DIR"
        check_environment
        install_autostart
        start_all
        start_watchdog
        check_autostart
        ;;
    uninstall-autostart)
        uninstall_autostart
        ;;
    check-autostart)
        check_autostart
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
        printf 'Usage: %s {start|autostart|watch|install-autostart|uninstall-autostart|check-autostart|stop|status|check|backup}\n' "$0" >&2
        exit 2
        ;;
esac