import sqlite3
from datetime import datetime

from app_paths import get_data_dir


class TaskHistory:
    def __init__(self):
        self.db_path = get_data_dir() / "task_history.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    label TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_ended "
                "ON task_history(ended_at DESC)"
            )
            conn.commit()

    def add(self, kind: str, label: str, status: str,
            created_at: str | None = None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO task_history "
                "(kind, label, status, created_at, ended_at) "
                "VALUES (?,?,?,?,?)",
                (kind, label, status, created_at or now, now),
            )
            conn.commit()

    def recent(self, limit: int = 50) -> list[tuple]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT id, kind, label, status, created_at, ended_at "
                "FROM task_history ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return cur.fetchall()

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM task_history")
            conn.commit()