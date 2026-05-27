import sqlite3
from pathlib import Path
from typing import Iterable


class TaskStore:
    """基于 SQLite 的任务状态表，用于支持大规模采集断点续爬。"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawl_tasks (
                    url TEXT PRIMARY KEY,
                    source_key TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    http_status INTEGER,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    raw_file TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def upsert_pending(self, source_key: str, data_type: str, urls: Iterable[str]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO crawl_tasks (url, source_key, data_type, status)
                VALUES (?, ?, ?, 'pending')
                ON CONFLICT(url) DO NOTHING
                """,
                [(url, source_key, data_type) for url in urls],
            )

    def mark_success(self, url: str, http_status: int, raw_file: Path) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE crawl_tasks
                SET status='success',
                    http_status=?,
                    raw_file=?,
                    error_message=NULL,
                    updated_at=CURRENT_TIMESTAMP
                WHERE url=?
                """,
                (http_status, str(raw_file), url),
            )

    def mark_failed(self, url: str, error_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE crawl_tasks
                SET status='failed',
                    retry_count=retry_count+1,
                    error_message=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE url=?
                """,
                (error_message[:1000], url),
            )
