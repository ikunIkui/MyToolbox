import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal

from app_paths import get_data_dir

LogLevel = Literal["info", "success", "warn", "error", "action"]


class ActionLogger:
    def __init__(self):
        self.db_path = get_data_dir() / "actions.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions(ts DESC)"
            )
            conn.commit()

    def log(self, message: str, level: LogLevel = "info", source: str = "命令"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO actions (ts, level, source, message) VALUES (?,?,?,?)",
                (ts, level, source, message),
            )
            conn.commit()
        return ts

    def recent(self, limit: int = 200) -> list[tuple[str, str, str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT ts, level, source, message FROM actions "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return cur.fetchall()

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM actions")
            conn.commit()