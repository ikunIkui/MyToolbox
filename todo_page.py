from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMenu, QMessageBox, QScrollArea,
    QFrame, QCheckBox, QProgressBar,
)

from todo_db import TodoDB
from anim import fade_in


MEANINGLESS_TITLES = {"提醒", "记录", "笔记", "待办", "无标题", "（无标题）"}


def _pick_display_title(title: str, body: str) -> str:
    """标题优先；标题空或为无意义词时，取正文第一行前 30 字"""
    t = (title or "").strip()
    if t and t not in MEANINGLESS_TITLES:
        return t
    for line in (body or "").splitlines():
        line = line.strip()
        if line:
            return line[:30] + ("…" if len(line) > 30 else "")
    return t or "（无标题）"


# ==================== 撤销提示条（悬浮） ====================
class UndoBar(QFrame):
    UNDO_MS = 5500
    TICK_MS = 50

    def __init__(self, colors: dict, on_undo, on_timeout, parent=None):
        super().__init__(parent)
        self.colors = colors
        self._on_undo = on_undo
        self._on_timeout = on_timeout
        self._elapsed = 0

        self.setFixedHeight(48)
        self.setStyleSheet(f"""
            UndoBar {{
                background: {colors['bg_card']};
                border: 1px solid {colors['accent']};
                border-radius: 8px;
            }}
        """)

        h = QHBoxLayout(self)
        h.setContentsMargins(14, 8, 10, 8)
        h.setSpacing(10)

        self.label = QLabel("")
        self.label.setStyleSheet(
            f"color: {colors['text']}; font-size: 13px; background: transparent;"
        )

        self.undo_btn = QPushButton("撤销")
        self.undo_btn.setFixedSize(60, 28)
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.setStyleSheet(f"""
            QPushButton {{
                background: {colors['accent']};
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #5f7cff; }}
            QPushButton:pressed {{ background: #3b57d6; }}
        """)
        self.undo_btn.clicked.connect(self._do_undo)

        self.progress = QProgressBar()
        self.progress.setRange(0, self.UNDO_MS)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(180)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background: {colors['bg']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {colors['accent']};
                border-radius: 3px;
            }}
        """)

        h.addWidget(self.label, 1)
        h.addWidget(self.undo_btn)
        h.addWidget(self.progress)

        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)

    def show_undo(self, text: str):
        self.label.setText(text)
        self._elapsed = 0
        self.progress.setValue(0)
        self._timer.start()

    def _tick(self):
        self._elapsed += self.TICK_MS
        self.progress.setValue(min(self._elapsed, self.UNDO_MS))
        if self._elapsed >= self.UNDO_MS:
            self._timer.stop()
            self._on_timeout()

    def _do_undo(self):
        self._timer.stop()
        self._on_undo()


# ==================== 待办页 ====================
class TodoPage(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.db = TodoDB()
        self._first_show = True
        self._pending_remove_id: int | None = None
        self._hidden_ids: set[int] = set()

        self.colors = getattr(win, "colors", None) or {
            "bg": "#1e2128",
            "bg_card": "#2b2f3a",
            "border": "#3a3f4b",
            "text": "#e8eaed",
            "text_dim": "#9aa2b1",
            "accent": "#4a6bff",
            "success": "#7ed08a",
            "warn": "#e6c46a",
            "error": "#e07a7a",
        }

        self._build_ui()
        self._refresh()

        # 悬浮撤销条（不放进布局，absolute 定位）
        self.undo_bar = UndoBar(
            self.colors,
            on_undo=self._on_undo_remove,
            on_timeout=self._on_undo_timeout,
            parent=self,
        )
        self.undo_bar.setVisible(False)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(3000)

    # ---------- UI ----------
    def _build_ui(self):
        c = self.colors
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        title = QLabel("待办清单")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {c['text']};"
        )
        root.addWidget(title)

        tip = QLabel("来自你的笔记（待办分类 或 含提醒时间）\n\n您可以在待办笔记右键进行详细操作")
        tip.setStyleSheet(f"color: {c['text_dim']}; font-size: 12px;")
        root.addWidget(tip)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(12)

        head1 = QHBoxLayout()
        lbl1 = QLabel("进行中")
        lbl1.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {c['text']};"
        )
        clear_done_btn = QPushButton("清空已完成")
        clear_done_btn.setFixedWidth(110)
        clear_done_btn.clicked.connect(self._clear_done)
        head1.addWidget(lbl1)
        head1.addStretch()
        head1.addWidget(clear_done_btn)
        v.addLayout(head1)

        self._pending_layout = QVBoxLayout()
        self._pending_layout.setSpacing(6)
        self._pending_layout.setAlignment(Qt.AlignTop)
        v.addLayout(self._pending_layout)

        lbl2 = QLabel("已完成")
        lbl2.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {c['text']}; "
            f"margin-top: 8px;"
        )
        v.addWidget(lbl2)

        self._done_layout = QVBoxLayout()
        self._done_layout.setSpacing(4)
        self._done_layout.setAlignment(Qt.AlignTop)
        v.addLayout(self._done_layout)

        v.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

    # ---------- 悬浮撤销条定位 ----------
    def _position_undo_bar(self):
        if not self.undo_bar.isVisible():
            return
        margin = 12
        bar_h = self.undo_bar.height()
        w = self.width() - margin * 2
        x = margin
        y = self.height() - bar_h - margin
        self.undo_bar.setGeometry(x, y, w, bar_h)
        self.undo_bar.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._position_undo_bar()

    # ---------- 刷新 ----------
    def _refresh(self):
        self._refresh_pending()
        self._refresh_done()

    def _refresh_pending(self):
        while self._pending_layout.count():
            item = self._pending_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        rows = self.db.list_pending()
        visible_rows = [r for r in rows if r[0] not in self._hidden_ids]

        if not visible_rows:
            empty = QLabel("暂无待办")
            empty.setStyleSheet(f"color: {self.colors['text_dim']};")
            self._pending_layout.addWidget(empty)
            return

        now = datetime.now()
        for row in visible_rows:
            todo_id, note_id, title, body, category, due_at, created_at = row
            w = self._make_pending_row(
                todo_id, note_id, title, body, category, due_at, now
            )
            self._pending_layout.addWidget(w)

    def _make_pending_row(self, todo_id, note_id, title, body,
                          category, due_at, now):
        c = self.colors
        display_title = _pick_display_title(title, body)

        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(10)

        cb = QCheckBox()
        cb.setCursor(Qt.PointingHandCursor)
        cb.stateChanged.connect(
            lambda _=0, tid=todo_id: self._on_check(tid)
        )

        info = QVBoxLayout()
        info.setSpacing(2)

        title_lbl = QLabel(display_title)
        title_lbl.setStyleSheet(
            f"font-size: 13px; background: transparent; color: {c['text']};"
        )
        title_lbl.setWordWrap(True)

        sub_parts = []
        if category:
            sub_parts.append(f"[{category}]")
        if due_at:
            sub_parts.append(self._fmt_due(due_at, now))
        else:
            sub_parts.append("无时间")
        sub_lbl = QLabel("  ".join(sub_parts))
        sub_lbl.setStyleSheet(
            f"color: {c['text_dim']}; font-size: 11px; background: transparent;"
        )

        info.addWidget(title_lbl)
        info.addWidget(sub_lbl)

        view_btn = QPushButton("查看")
        view_btn.setFixedSize(52, 26)
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['accent']};
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: #5f7cff; }}
        """)
        view_btn.clicked.connect(
            lambda _=False, t=title, b=body: self._view_note(t, b)
        )

        h.addWidget(cb, 0, Qt.AlignTop)
        h.addLayout(info, 1)
        h.addWidget(view_btn, 0, Qt.AlignVCenter)

        row.setContextMenuPolicy(Qt.CustomContextMenu)
        row.customContextMenuRequested.connect(
            lambda pos, tid=todo_id, nid=note_id, t=title:
                self._show_menu(pos, row, tid, nid, t)
        )

        return row

    def _refresh_done(self):
        while self._done_layout.count():
            item = self._done_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        rows = self.db.list_done(50)
        if not rows:
            empty = QLabel("暂无已完成")
            empty.setStyleSheet(f"color: {self.colors['text_dim']};")
            self._done_layout.addWidget(empty)
            return

        for row_data in rows:
            todo_id, note_id, title, body, category, due_at, done_at = row_data
            display_title = _pick_display_title(title, body)

            row = QFrame()
            row.setStyleSheet("QFrame { background: transparent; border: none; }")
            h = QHBoxLayout(row)
            h.setContentsMargins(10, 4, 10, 4)
            h.setSpacing(10)

            cb = QCheckBox()
            cb.setChecked(True)
            cb.setCursor(Qt.PointingHandCursor)
            cb.stateChanged.connect(
                lambda _=0, tid=todo_id: self._on_uncheck(tid)
            )

            line = QLabel(f"✅ {display_title}    {done_at}")
            line.setStyleSheet(
                f"color: {self.colors['success']}; font-size: 12px; "
                f"background: transparent;"
            )
            line.setWordWrap(True)

            view_btn = QPushButton("查看")
            view_btn.setFixedSize(52, 24)
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.colors['text_dim']};
                    border: 1px solid {self.colors['border']};
                    border-radius: 5px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    color: {self.colors['text']};
                    border: 1px solid {self.colors['accent']};
                }}
            """)
            view_btn.clicked.connect(
                lambda _=False, t=title, b=body: self._view_note(t, b)
            )

            h.addWidget(cb, 0, Qt.AlignTop)
            h.addWidget(line, 1)
            h.addWidget(view_btn, 0, Qt.AlignVCenter)

            row.setContextMenuPolicy(Qt.CustomContextMenu)
            row.customContextMenuRequested.connect(
                lambda pos, tid=todo_id, nid=note_id:
                    self._show_menu(pos, row, tid, nid, title)
            )

            self._done_layout.addWidget(row)

    # ---------- 查看原文 ----------
    def _view_note(self, title: str, body: str):
        box = QMessageBox(self)
        box.setWindowTitle(title or "（无标题）")
        box.setText(title or "（无标题）")
        box.setDetailedText(body or "（空）")
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    # ---------- 时间格式 ----------
    @staticmethod
    def _fmt_due(due_at: str, now: datetime) -> str:
        try:
            dt = datetime.strptime(due_at, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return due_at

        diff = (dt - now).total_seconds()
        if diff < 0:
            return f"⚠️ 已过期 {dt:%m-%d %H:%M}"
        if diff < 3600:
            return f"⏰ {int(diff // 60)} 分钟后"
        if diff < 86400:
            return f"⏰ {int(diff // 3600)} 小时后（{dt:%H:%M}）"
        return f"⏰ {dt:%m-%d %H:%M}"

    # ---------- 事件 ----------
    def _on_check(self, todo_id: int):
        self.db.mark_done(todo_id)
        self.win._append("待办已完成", level="success", source="待办")
        self._refresh()

    def _on_uncheck(self, todo_id: int):
        self.db.mark_pending(todo_id)
        self.win._append("待办已恢复", level="info", source="待办")
        self._refresh()

    def _show_menu(self, pos, row, todo_id, note_id, title=""):
        menu = QMenu(self)
        act_open = menu.addAction("📝 打开笔记")
        act_remove = menu.addAction("🚫 移出待办")
        menu.addSeparator()
        act_delete = menu.addAction("🗑 删除笔记")

        action = menu.exec(row.mapToGlobal(pos))
        if action == act_open:
            self._open_note(note_id)
        elif action == act_remove:
            self._schedule_remove(todo_id, title)
        elif action == act_delete:
            self._delete_note(note_id, todo_id)

    # ---------- 撤销移除 ----------
    def _schedule_remove(self, todo_id: int, title: str):
        if self._pending_remove_id is not None:
            self._commit_remove()

        self._pending_remove_id = todo_id
        self._hidden_ids.add(todo_id)
        self._refresh()

        self.undo_bar.show_undo(f"已移出待办：{title or '（无标题）'}")
        self.undo_bar.setVisible(True)
        self._position_undo_bar()

    def _on_undo_remove(self):
        if self._pending_remove_id is None:
            return
        self._hidden_ids.discard(self._pending_remove_id)
        self._pending_remove_id = None
        self.undo_bar.setVisible(False)
        self.win._append("已撤销移出", level="info", source="待办")
        self._refresh()

    def _on_undo_timeout(self):
        self._commit_remove()
        self.undo_bar.setVisible(False)

    def _commit_remove(self):
        if self._pending_remove_id is None:
            return
        tid = self._pending_remove_id
        self.db.remove(tid)
        self._hidden_ids.discard(tid)
        self._pending_remove_id = None
        self.win._append("已移出待办", level="warn", source="待办")
        self._refresh()

    # ---------- 打开笔记 ----------
    def _open_note(self, note_id: int):
        try:
            self.win.nav.setCurrentRow(0)
            self.win.features_page._open_feature("note")
            from note_page import NotePage
            detail = self.win.features_page._detail_cache.get("note")
            if detail:
                for child in detail.findChildren(NotePage):
                    child.select_note(note_id)
                    break
        except Exception as e:
            print(f"[todo] 打开笔记失败: {e}")

    def _delete_note(self, note_id: int, todo_id: int):
        if QMessageBox.question(self, "确认", "删除这条笔记（及其待办）？") != QMessageBox.Yes:
            return
        import sqlite3
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
                conn.execute("DELETE FROM todos WHERE id=?", (todo_id,))
                conn.commit()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        self.win._append("笔记及待办已删除", level="warn", source="待办")
        self._refresh()

    def _clear_done(self):
        if QMessageBox.question(self, "确认", "清空所有已完成的待办？") != QMessageBox.Yes:
            return
        self.db.clear_done()
        self.win._append("已清空完成记录", level="warn", source="待办")
        self._refresh()

    def showEvent(self, e):
        super().showEvent(e)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(30, lambda: fade_in(self, duration=220))