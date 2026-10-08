"""SQLite persistence for books, immutable artifacts, jobs, and review events."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
PAGE_BREAK_TOKEN = "<<<BOOK_PAGE_BREAK>>>"


def service_home() -> Path:
    configured = os.environ.get("READING_SERVICE_HOME")
    return Path(configured).expanduser().resolve() if configured else ROOT / "output/reading_service"


def database_path() -> Path:
    configured = os.environ.get("READING_SERVICE_DB")
    return Path(configured).expanduser().resolve() if configured else service_home() / "service.sqlite3"


def book_directory(book_id: str) -> Path:
    return service_home() / "books" / book_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                current_stage TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                stage TEXT NOT NULL,
                kind TEXT NOT NULL,
                version INTEGER NOT NULL,
                path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(book_id, stage, kind, version)
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                queue_id TEXT,
                progress REAL NOT NULL DEFAULT 0,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                stage TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                note TEXT NOT NULL,
                artifact_version INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS artifacts_book_idx ON artifacts(book_id, created_at);
            CREATE INDEX IF NOT EXISTS jobs_book_idx ON jobs(book_id, created_at);
            CREATE INDEX IF NOT EXISTS events_book_idx ON events(book_id, id);
            """
        )


def create_book(book_id: str, title: str) -> None:
    now = _now()
    with connect() as db:
        db.execute(
            "INSERT INTO books(id, title, current_stage, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (book_id, title, "document", "uploaded", now, now),
        )
    add_event(book_id, "document", "book_created", "user", "DOCX uploaded")


def get_book(book_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row is None:
            return None
        book = dict(row)
        book["artifacts"] = [
            _artifact_dict(item)
            for item in db.execute(
                "SELECT * FROM artifacts WHERE book_id = ? ORDER BY created_at, kind, version", (book_id,)
            ).fetchall()
        ]
        book["jobs"] = [
            dict(item)
            for item in db.execute("SELECT * FROM jobs WHERE book_id = ? ORDER BY created_at", (book_id,)).fetchall()
        ]
        book["events"] = [
            dict(item)
            for item in db.execute("SELECT * FROM events WHERE book_id = ? ORDER BY id", (book_id,)).fetchall()
        ]
        book.update(_text_stats(db, book_id))
        return book


def delete_book(book_id: str) -> str:
    home = service_home().resolve()
    books_root = (home / "books").resolve()
    book_path = book_directory(book_id).resolve()
    try:
        book_path.relative_to(books_root)
    except ValueError as exc:
        raise ValueError("Book path resolves outside the books directory") from exc

    trash_path: Path | None = None
    try:
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            exists = db.execute("SELECT 1 FROM books WHERE id = ?", (book_id,)).fetchone()
            if exists is None:
                return "not_found"
            active_job = db.execute(
                "SELECT 1 FROM jobs WHERE book_id = ? AND status IN ('queued', 'running') LIMIT 1",
                (book_id,),
            ).fetchone()
            if active_job is not None:
                return "active_jobs"

            if book_path.exists():
                trash_root = home / ".trash"
                trash_root.mkdir(parents=True, exist_ok=True)
                trash_path = trash_root / f"{book_id}-{uuid.uuid4().hex}"
                os.replace(book_path, trash_path)
            db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    except Exception:
        if trash_path is not None and trash_path.exists() and not book_path.exists():
            book_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(trash_path, book_path)
        raise

    if trash_path is not None:
        shutil.rmtree(trash_path, ignore_errors=True)
    return "deleted"


def list_books() -> list[dict[str, Any]]:
    with connect() as db:
        books = [dict(row) for row in db.execute("SELECT * FROM books ORDER BY updated_at DESC").fetchall()]
        for book in books:
            book.update(_text_stats(db, book["id"]))
        return books


def _text_stats(db: sqlite3.Connection, book_id: str) -> dict[str, Any]:
    artifact = db.execute(
        "SELECT path, version FROM artifacts "
        "WHERE book_id = ? AND stage = 'text' AND kind = 'normalized_text' "
        "ORDER BY version DESC LIMIT 1",
        (book_id,),
    ).fetchone()
    if artifact is None:
        return {"text_char_count": None, "page_count": None, "text_version": None}

    text_path = (service_home() / artifact["path"]).resolve()
    try:
        text_path.relative_to(service_home().resolve())
    except ValueError:
        return {"text_char_count": None, "page_count": None, "text_version": artifact["version"]}
    if not text_path.is_file():
        return {"text_char_count": None, "page_count": None, "text_version": artifact["version"]}

    text = text_path.read_text(encoding="utf-8")
    page_count = text.count(PAGE_BREAK_TOKEN) + 1
    text = text.replace(PAGE_BREAK_TOKEN, "")
    return {
        "text_char_count": sum(not character.isspace() for character in text),
        "page_count": page_count,
        "text_version": artifact["version"],
    }


def set_book_state(book_id: str, stage: str, status: str) -> None:
    with connect() as db:
        db.execute(
            "UPDATE books SET current_stage = ?, status = ?, updated_at = ? WHERE id = ?",
            (stage, status, _now(), book_id),
        )


def add_artifact(
    book_id: str,
    stage: str,
    kind: str,
    path: Path,
    sha256: str,
    mime_type: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    home = service_home()
    resolved_path = path.resolve()
    relative_path = resolved_path.relative_to(home).as_posix()
    with connect() as db:
        version = db.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM artifacts WHERE book_id = ? AND stage = ? AND kind = ?",
            (book_id, stage, kind),
        ).fetchone()[0]
        artifact = {
            "id": str(uuid.uuid4()),
            "book_id": book_id,
            "stage": stage,
            "kind": kind,
            "version": version,
            "path": relative_path,
            "sha256": sha256,
            "mime_type": mime_type,
            "metadata": json.dumps(metadata or {}, ensure_ascii=False),
            "created_at": _now(),
        }
        db.execute(
            "INSERT INTO artifacts(id, book_id, stage, kind, version, path, sha256, mime_type, metadata, created_at) "
            "VALUES (:id, :book_id, :stage, :kind, :version, :path, :sha256, :mime_type, :metadata, :created_at)",
            artifact,
        )
    return _artifact_dict(artifact)


def _artifact_dict(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    artifact = dict(row)
    artifact["metadata"] = json.loads(artifact["metadata"])
    artifact["url"] = f"/api/artifacts/{artifact['id']}"
    return artifact


def add_event(
    book_id: str,
    stage: str,
    event_type: str,
    actor: str = "system",
    note: str = "",
    artifact_version: int | None = None,
) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO events(book_id, stage, event_type, actor, note, artifact_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (book_id, stage, event_type, actor, note, artifact_version, _now()),
        )
        db.execute("UPDATE books SET updated_at = ? WHERE id = ?", (_now(), book_id))


def approve_if_current(
    book_id: str,
    current_stage: str,
    current_status: str,
    next_stage: str,
    next_status: str,
    event_stage: str,
    actor: str,
    note: str,
    artifact_version: int | None,
) -> bool:
    now = _now()
    with connect() as db:
        updated = db.execute(
            "UPDATE books SET current_stage = ?, status = ?, updated_at = ? "
            "WHERE id = ? AND current_stage = ? AND status = ?",
            (next_stage, next_status, now, book_id, current_stage, current_status),
        )
        if updated.rowcount != 1:
            return False
        db.execute(
            "INSERT INTO events(book_id, stage, event_type, actor, note, artifact_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (book_id, event_stage, "approved", actor, note, artifact_version, now),
        )
        return True


def create_job(job_id: str, book_id: str, stage: str) -> None:
    now = _now()
    with connect() as db:
        db.execute(
            "INSERT INTO jobs(id, book_id, stage, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, book_id, stage, "queued", now, now),
        )


def get_active_job(book_id: str, stage: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute(
            "SELECT * FROM jobs WHERE book_id = ? AND stage = ? AND status IN ('queued', 'running') "
            "ORDER BY created_at DESC LIMIT 1",
            (book_id, stage),
        ).fetchone()
        return dict(row) if row else None


def get_job(job_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def update_job(
    job_id: str,
    status: str,
    progress: float | None = None,
    error: str | None = None,
    queue_id: str | None = None,
) -> None:
    with connect() as db:
        db.execute(
            "UPDATE jobs SET status = ?, progress = COALESCE(?, progress), error = ?, "
            "queue_id = COALESCE(?, queue_id), updated_at = ? WHERE id = ?",
            (status, progress, error, queue_id, _now(), job_id),
        )