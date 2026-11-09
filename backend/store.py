"""SQLite persistence for invoice-analysis run history."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.config import RUNS_DB_PATH
from utils.logger import logger


def init_db(db_path: str | Path = RUNS_DB_PATH) -> None:
    """Create the database directory and run-history table when needed."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS invoice_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )"""
            )


def get_next_case_reference(
    db_path: str | Path = RUNS_DB_PATH,
    session_offset: int = 0,
) -> str:
    """Generate a dynamic, unique sequential enterprise Case ID (e.g. AP-2026-1041)."""
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        row = connection.execute("SELECT MAX(run_id) FROM invoice_runs").fetchone()
        max_run_id = row[0] if (row and row[0] is not None) else 0
    year = datetime.now(timezone.utc).year
    next_seq = 1040 + max_run_id + session_offset + 1
    return f"AP-{year}-{next_seq:04d}"


def save_run(
    filename: str,
    result: dict[str, Any],
    db_path: str | Path = RUNS_DB_PATH,
) -> int:
    """Persist a result record (metadata only, not the uploaded PDF) and return run ID."""
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """INSERT INTO invoice_runs (created_at, filename, status, summary, result_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    filename,
                    str(result.get("status", "UNKNOWN")),
                    str(result.get("summary", "")),
                    json.dumps(result, ensure_ascii=True),
                ),
            )
            run_id = cursor.lastrowid
    logger.info("Saved review run #%s for file %s with status %s", run_id, filename, result.get("status"))
    return int(run_id)


def update_run(
    run_id: int,
    result: dict[str, Any],
    db_path: str | Path = RUNS_DB_PATH,
) -> None:
    """Update an existing analysis run record in place (e.g. status transition, approval voucher, notes)."""
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute(
                """UPDATE invoice_runs
                   SET status = ?, summary = ?, result_json = ?
                   WHERE run_id = ?""",
                (
                    str(result.get("status", "UNKNOWN")),
                    str(result.get("summary", "")),
                    json.dumps(result, ensure_ascii=True),
                    run_id,
                ),
            )
    logger.info("Updated review run #%s with status %s", run_id, result.get("status"))


def list_runs(
    db_path: str | Path = RUNS_DB_PATH,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return the most recent analysis runs, newest first."""
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT run_id, created_at, filename, status, summary, result_json
               FROM invoice_runs ORDER BY run_id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "run_id": row["run_id"],
            "created_at": row["created_at"],
            "filename": row["filename"],
            "status": row["status"],
            "summary": row["summary"],
            "result": json.loads(row["result_json"]),
        }
        for row in rows
    ]

