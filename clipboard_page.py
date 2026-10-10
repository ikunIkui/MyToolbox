from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QMessageBox, QApplication,
    QCheckBox, QProgressBar,
)

from clipboard_db import ClipboardDB
from app_paths import load_config, save_config


_FALLBACK = {
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


# ==================== 撤销条（悬浮） ====================
class UndoBar(QFrame):
    UNDO_MS = 5000
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


# ==================== 主页面 ====================
class ClipboardPage(QWidget):
    REFRESH_MS = 1500

    def __init__(self, win, colors: dict | None = None, parent=None):
        super().__init__(parent)
        self.win = win
        self.colors = colors or getattr(win, "colors", None) or _FALLBACK
        self.db = ClipboardDB()
        self._timer: QTimer | None = None
        self._last_count = -1

        # 撤销相关
        self._pending_del_id: int | None = None
        self._hidden_ids: set[int] = set()

        self._build_ui()

        # 悬浮撤销条
        self.undo_bar = UndoBar(
            self.colors,
            on_undo=self._on_undo_del,
            on_timeout=self._on_undo_timeout,
            parent=self,
        )
        self.undo_bar.setVisible(False)

    # ---------- UI ----------
    def _build_ui(self):
        c = self.colors

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        title = QLabel("📋 剪贴板历史")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {c['text']};"
        )
        root.addWidget(title)

        tip = QLabel(
            "自动记录复制的文本，关机/重启不丢。"
            "最多保留 500 条，可在设置页清空。删除后 5 秒内可撤销。"
        )
        tip.setStyleSheet(f"color: {c['text_dim']}; font-size: 12px;")
        tip.setWordWrap(True)
        root.addWidget(tip)

        # 顶部：搜索 + 清空
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索历史…")
        self.search.textChanged.connect(self._refresh)
        self.clear_btn = QPushButton("清空全部")
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self._clear_all)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.clear_btn)
        root.addLayout(bar)

        # 监听开关
        self.enable_check = QCheckBox("启用剪贴板监听")
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        root.addWidget(self.enable_check)

        # 计数
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(
            f"color: {c['text_dim']}; font-size: 11px;"
        )
        root.addWidget(self.count_label)

        # 滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        self._list_layout = QVBoxLayout(inner)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(6)
        self._list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        cfg = load_config()
        self.enable_check.blockSignals(True)
        self.enable_check.setChecked(bool(cfg.get("clipboard_enabled", True)))
        self.enable_check.blockSignals(False)

    # ---------- 撤销条定位 ----------
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

    # ---------- 刷新列表 ----------
    def _refresh(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        keyword = self.search.text().strip()
        rows = self.db.list(keyword, limit=200)
        visible = [r for r in rows if r[0] not in self._hidden_ids]

        total = self.db.count()
        self.count_label.setText(f"共 {total} 条，显示 {len(visible)} 条")

        if not visible:
            empty = QLabel("暂无历史")
            empty.setStyleSheet(f"color: {self.colors['text_dim']};")
            self._list_layout.addWidget(empty)
            return

        for item_id, content, created_at in visible:
            card = self._make_card(item_id, content, created_at)
            self._list_layout.addWidget(card)

    def _make_card(self, item_id: int, content: str, created_at: str) -> QFrame:
        c = self.colors

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            QLabel {{ background: transparent; }}
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)

        # 时间行
        head = QHBoxLayout()
        time_lbl = QLabel(created_at)
        time_lbl.setStyleSheet(
            f"color: {c['text_dim']}; font-size: 11px; background: transparent;"
        )
        head.addWidget(time_lbl)
        head.addStretch()
        v.addLayout(head)

        # 内容预览
        preview = content
        lines = preview.splitlines()
        if len(lines) > 5:
            preview = "\n".join(lines[:5]) + "\n…"
        if len(preview) > 300:
            preview = preview[:300] + "…"

        content_lbl = QLabel(preview)
        # 关键：按纯文本显示，避免 HTML 标签被解析
        content_lbl.setTextFormat(Qt.PlainText)
        content_lbl.setStyleSheet(
            f"color: {c['text']}; font-size: 12px; background: transparent;"
        )
        content_lbl.setWordWrap(True)
        content_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(content_lbl)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(60, 26)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(self._btn_style("accent"))
        copy_btn.clicked.connect(lambda _=False, t=content: self._copy(t))

        del_btn = QPushButton("删除")
        del_btn.setFixedSize(60, 26)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(self._btn_style("danger"))
        del_btn.clicked.connect(lambda _=False, i=item_id: self._schedule_del(i))

        btn_row.addWidget(copy_btn)
        btn_row.addWidget(del_btn)
        v.addLayout(btn_row)

        return card

    def _btn_style(self, kind: str) -> str:
        c = self.colors
        if kind == "accent":
            bg = c["accent"]
            hover = "#5f7cff"
            press = "#3b57d6"
        else:
            bg = "#e07a7a"
            hover = "#ea8d8d"
            press = "#c96a6a"
        return f"""
            QPushButton {{
                background: {bg};
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:pressed {{ background: {press}; }}
        """

    # ---------- 操作 ----------
    def _copy(self, text: str):
        try:
            QApplication.clipboard().setText(text)
            if hasattr(self.win, "_append"):
                self.win._append("已复制到剪贴板", level="success", source="剪贴板")
        except Exception as e:
            QMessageBox.warning(self, "复制失败", str(e))

    # ---------- 删除（带撤销） ----------
    def _schedule_del(self, item_id: int):
        if self._pending_del_id is not None:
            self._commit_del()

        preview = ""
        try:
            for i, cont, _ in self.db.list("", limit=500):
                if i == item_id:
                    preview = cont.splitlines()[0] if cont else ""
                    break
        except Exception:
            pass
        if len(preview) > 30:
            preview = preview[:30] + "…"

        self._pending_del_id = item_id
        self._hidden_ids.add(item_id)
        self._refresh()

        self.undo_bar.show_undo(f"已删除：{preview or '（无内容）'}")
        self.undo_bar.setVisible(True)
        self._position_undo_bar()

    def _on_undo_del(self):
        if self._pending_del_id is None:
            return
        self._hidden_ids.discard(self._pending_del_id)
        self._pending_del_id = None
        self.undo_bar.setVisible(False)
        if hasattr(self.win, "_append"):
            self.win._append("已撤销删除", level="info", source="剪贴板")
        self._refresh()

    def _on_undo_timeout(self):
        self._commit_del()
        self.undo_bar.setVisible(False)

    def _commit_del(self):
        if self._pending_del_id is None:
            return
        tid = self._pending_del_id
        self.db.delete(tid)
        self._hidden_ids.discard(tid)
        self._pending_del_id = None
        if hasattr(self.win, "_append"):
            self.win._append("已删除剪贴板记录", level="warn", source="剪贴板")
        self._refresh()

    # ---------- 清空全部 ----------
    def _clear_all(self):
        box = QMessageBox(self)
        box.setWindowTitle("确认清空")
        box.setIcon(QMessageBox.Warning)
        box.setText("确定要清空所有剪贴板历史吗？")
        box.setInformativeText(
            "⚠️ 建议先打开数据目录备份 clipboard.db，此操作不可恢复。"
        )
        yes_btn = box.addButton("确认清空", QMessageBox.YesRole)
        open_btn = box.addButton("打开数据目录", QMessageBox.ActionRole)
        cancel_btn = box.addButton("取消", QMessageBox.RejectRole)
        box.setDefaultButton(cancel_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked is open_btn:
            self._open_data_dir()
            return
        if clicked is not yes_btn:
            return

        self.db.clear()
        self._hidden_ids.clear()
        self._pending_del_id = None
        self.undo_bar.setVisible(False)
        self._refresh()
        if hasattr(self.win, "_append"):
            self.win._append("剪贴板历史已清空", level="warn", source="剪贴板")

    def _open_data_dir(self):
        import os
        import subprocess
        from app_paths import get_data_dir
        path = str(get_data_dir())
        try:
            os.startfile(path)
        except Exception:
            subprocess.Popen(f'explorer "{path}"', shell=True)

    def _on_enable_changed(self, state):
        cfg = load_config()
        cfg["clipboard_enabled"] = bool(state)
        save_config(cfg)

    # ---------- 外部（设置页）调用：强制重拉 ----------
    def reload_from_db(self):
        """设置页清空后调用，或任何外部改动后调用"""
        self._hidden_ids.clear()
        self._pending_del_id = None
        self.undo_bar.setVisible(False)
        self._last_count = self.db.count()
        self._refresh()

    # ---------- 定时刷新（外部新增） ----------
    def _start_timer(self):
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
        self._timer.start(self.REFRESH_MS)

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.stop()

    def _tick(self):
        if self._pending_del_id is not None:
            return
        cur = self.db.count()
        if cur != self._last_count:
            self._last_count = cur
            self._refresh()

    # ---------- 生命周期 ----------
    def showEvent(self, e):
        super().showEvent(e)
        # 每次切回来都强制重拉，避免设置页清空后不同步
        self._hidden_ids.clear()
        self._pending_del_id = None
        self.undo_bar.setVisible(False)
        self._last_count = self.db.count()
        self._refresh()
        self._start_timer()

    def hideEvent(self, e):
        super().hideEvent(e)
        if self._pending_del_id is not None:
            self._commit_del()
        self.undo_bar.setVisible(False)
        self._stop_timer()

    def cleanup(self):
        if self._pending_del_id is not None:
            self._commit_del()
        self._stop_timer()