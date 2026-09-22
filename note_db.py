import sqlite3
from datetime import datetime

from app_paths import get_data_dir


class NoteDB:
    def __init__(self):
        self.db_path = get_data_dir() / "notes.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    category TEXT DEFAULT '其他',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 兼容老库：没有 category 就补
            try:
                conn.execute("ALTER TABLE notes ADD COLUMN category TEXT DEFAULT '其他'")
            except sqlite3.OperationalError:
                pass

            # FTS5
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                    title, body, content='notes', content_rowid='id'
                )
            """)

            # 触发器
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                    INSERT INTO notes_fts(rowid, title, body)
                    VALUES (new.id, new.title, new.body);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                    INSERT INTO notes_fts(notes_fts, rowid, title, body)
                    VALUES('delete', old.id, old.title, old.body);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                    INSERT INTO notes_fts(notes_fts, rowid, title, body)
                    VALUES('delete', old.id, old.title, old.body);
                    INSERT INTO notes_fts(rowid, title, body)
                    VALUES (new.id, new.title, new.body);
                END
            """)
            conn.commit()

    def list_notes(self, keyword: str = "") -> list[tuple]:
        with sqlite3.connect(self.db_path) as conn:
            if keyword.strip():
                cur = conn.execute("""
                    SELECT n.id, n.title, n.category, n.updated_at
                    FROM notes_fts f JOIN notes n ON n.id = f.rowid
                    WHERE notes_fts MATCH ?
                    ORDER BY n.updated_at DESC
                """, (keyword + "*",))
            else:
                cur = conn.execute(
                    "SELECT id, title, category, updated_at FROM notes "
                    "ORDER BY updated_at DESC"
                )
            return cur.fetchall()

    def get(self, note_id: int) -> tuple | None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT id, title, body, category FROM notes WHERE id = ?",
                (note_id,),
            )
            return cur.fetchone()

    def add(self, title: str, body: str, category: str = "其他") -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO notes (title, body, category, created_at, updated_at) "
                "VALUES (?,?,?,?,?)",
                (title, body, category, now, now),
            )
            conn.commit()
            return cur.lastrowid

    def update(self, note_id: int, title: str, body: str, category: str = "其他"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE notes SET title=?, body=?, category=?, updated_at=? WHERE id=?",
                (title, body, category, now, note_id),
            )
            conn.commit()

    def delete(self, note_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
            conn.commit()