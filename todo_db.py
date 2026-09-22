import sqlite3
from datetime import datetime

from app_paths import get_data_dir


class TodoDB:
    def __init__(self):
        self.db_path = get_data_dir() / "notes.db"   # 跟笔记同库，方便 JOIN
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    due_at TEXT,
                    created_at TEXT NOT NULL,
                    done_at TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_todos_status "
                "ON todos(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_todos_note "
                "ON todos(note_id)"
            )
            conn.commit()

    # ---------- 写入 ----------
    def add_from_note(self, note_id: int, due_at: str | None = None) -> int | None:
        """
        把一条笔记加入待办。
        如果该笔记已经在待办里（不论状态），返回 None 不重复插。
        """
        if self.has_todo(note_id):
            return None
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO todos (note_id, status, due_at, created_at) "
                "VALUES (?, 'pending', ?, ?)",
                (note_id, due_at, now),
            )
            conn.commit()
            return cur.lastrowid

    def has_todo(self, note_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT 1 FROM todos WHERE note_id = ? LIMIT 1", (note_id,)
            )
            return cur.fetchone() is not None

    # ---------- 查询 ----------
    def list_pending(self) -> list[tuple]:
        """
        返回：[(todo_id, note_id, title, body, category, due_at, created_at), ...]
        排序规则：
          - 有 due_at 的按 due_at 升序排前面
          - 无 due_at 的按 created_at 降序排后面
        """
        sql = """
            SELECT t.id, t.note_id, n.title, n.body, n.category,
                   t.due_at, t.created_at
            FROM todos t
            JOIN notes n ON n.id = t.note_id
            WHERE t.status = 'pending'
            ORDER BY
                CASE WHEN t.due_at IS NULL THEN 1 ELSE 0 END,
                t.due_at ASC,
                t.created_at DESC
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(sql)
            return cur.fetchall()

    def list_done(self, limit: int = 50) -> list[tuple]:
        sql = """
            SELECT t.id, t.note_id, n.title, n.body, n.category,
                   t.due_at, t.done_at
            FROM todos t
            JOIN notes n ON n.id = t.note_id
            WHERE t.status = 'done'
            ORDER BY t.done_at DESC
            LIMIT ?
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(sql, (limit,))
            return cur.fetchall()

    # ---------- 状态变更 ----------
    def mark_done(self, todo_id: int):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE todos SET status='done', done_at=? WHERE id=?",
                (now, todo_id),
            )
            conn.commit()

    def mark_pending(self, todo_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE todos SET status='pending', done_at=NULL WHERE id=?",
                (todo_id,),
            )
            conn.commit()

    def remove(self, todo_id: int):
        """把笔记移出待办（删 todos 记录，不删笔记）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
            conn.commit()

    def clear_done(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM todos WHERE status='done'")
            conn.commit()

    # ---------- 清理：笔记删了，待办也清 ----------
    def cleanup_orphans(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM todos
                WHERE note_id NOT IN (SELECT id FROM notes)
            """)
            conn.commit()