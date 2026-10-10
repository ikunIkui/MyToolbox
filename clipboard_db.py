import sqlite3
from datetime import datetime

from app_paths import get_data_dir


MAX_ITEMS = 500          # 最多存 500 条
MAX_LEN = 10000          # 单条最长 10000 字符


class ClipboardDB:
    def __init__(self):
        self.db_path = get_data_dir() / "clipboard.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clipboard (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_clip_created "
                "ON clipboard(created_at DESC)"
            )
            conn.commit()

    # ---------- 写入 ----------
    def add(self, content: str) -> bool:
        """
        存一条。返回 True 表示真的存了。
        - 空内容不存
        - 和最新一条相同不存（去重）
        - 超过 MAX_LEN 截断
        """
        if not content:
            return False
        content = content.strip()
        if not content:
            return False
        if len(content) > MAX_LEN:
            content = content[:MAX_LEN]

        with sqlite3.connect(self.db_path) as conn:
            # 和最新一条比
            cur = conn.execute(
                "SELECT content FROM clipboard ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row and row[0] == content:
                return False

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO clipboard (content, created_at) VALUES (?, ?)",
                (content, now),
            )
            conn.commit()

            # 超量删最旧
            conn.execute("""
                DELETE FROM clipboard
                WHERE id NOT IN (
                    SELECT id FROM clipboard ORDER BY id DESC LIMIT ?
                )
            """, (MAX_ITEMS,))
            conn.commit()
        return True

    # ---------- 查询 ----------
    def list(self, keyword: str = "", limit: int = 200) -> list[tuple]:
        """返回 [(id, content, created_at), ...]"""
        with sqlite3.connect(self.db_path) as conn:
            if keyword.strip():
                cur = conn.execute(
                    "SELECT id, content, created_at FROM clipboard "
                    "WHERE content LIKE ? "
                    "ORDER BY id DESC LIMIT ?",
                    (f"%{keyword}%", limit),
                )
            else:
                cur = conn.execute(
                    "SELECT id, content, created_at FROM clipboard "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
            return cur.fetchall()

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM clipboard")
            return cur.fetchone()[0]

    # ---------- 删除 ----------
    def delete(self, item_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM clipboard WHERE id=?", (item_id,))
            conn.commit()

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM clipboard")
            conn.commit()