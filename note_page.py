from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QPlainTextEdit, QFileDialog, QMessageBox,
    QSplitter, QLabel,
)

from note_db import NoteDB
from nlp_reminder import scan_note_for_reminder
from note_classifier import classify
from exporter import export_markdown, export_docx, export_pdf
from anim import fade_in
from app_paths import load_config
from todo_db import TodoDB


HINT_TEXT = (
    "支持 Markdown，例：# 标题 / - 列表 / 30 分钟后提醒我喝水 / 明天下午 3 点开会"
)


class NotePage(QWidget):
    def __init__(self, win, scheduler, parent=None):
        super().__init__(parent)
        self.win = win
        self.scheduler = scheduler
        self.db = NoteDB()
        self.todo_db = TodoDB()
        self.current_id: int | None = None

        self._build_ui()
        self._reload_list()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # 搜索 + 新建
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索笔记（FTS5 全文）…")
        self.search.textChanged.connect(self._reload_list)
        new_btn = QPushButton("新建")
        new_btn.setFixedWidth(70)
        new_btn.clicked.connect(self._new_note)
        bar.addWidget(self.search, 1)
        bar.addWidget(new_btn)
        root.addLayout(bar)

        # 常驻提示
        self.hint_label = QLabel(HINT_TEXT)
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(
            "font-size: 12px; padding: 2px 4px; background: transparent;"
        )
        root.addWidget(self.hint_label)

        splitter = QSplitter(Qt.Horizontal)

        # 左：列表
        self.list = QListWidget()
        self.list.setFixedWidth(240)
        self.list.currentItemChanged.connect(self._on_select)
        splitter.addWidget(self.list)

        # 右：编辑区
        editor_wrap = QWidget()
        ev = QVBoxLayout(editor_wrap)
        ev.setContentsMargins(0, 0, 0, 0)
        ev.setSpacing(6)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("标题")
        ev.addWidget(self.title_edit)

        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet(
            'font-family: Consolas, "Microsoft YaHei", monospace;'
        )
        ev.addWidget(self.editor, 1)

        # 分类显示
        self.category_label = QLabel("分类：—")
        self.category_label.setStyleSheet("font-size: 12px;")
        ev.addWidget(self.category_label)

        # 按钮行
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self._save)

        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._delete)

        exp_md = QPushButton("导出 MD")
        exp_md.clicked.connect(lambda: self._export("md"))
        exp_docx = QPushButton("导出 Word")
        exp_docx.clicked.connect(lambda: self._export("docx"))
        exp_pdf = QPushButton("导出 PDF")
        exp_pdf.clicked.connect(lambda: self._export("pdf"))

        for b in (self.save_btn, del_btn, exp_md, exp_docx, exp_pdf):
            b.setFixedHeight(30)
            btn_row.addWidget(b)
        btn_row.addStretch()

        ev.addLayout(btn_row)
        splitter.addWidget(editor_wrap)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

    # ---------- 列表 ----------
    def _reload_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        keyword = self.search.text().strip()
        for nid, title, category, updated in self.db.list_notes(keyword):
            cat = category or "其他"
            item = QListWidgetItem(f"[{cat}] {title or '（无标题）'}\n{updated}")
            item.setData(Qt.UserRole, nid)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _on_select(self, cur, _prev):
        if not cur:
            return
        nid = cur.data(Qt.UserRole)
        row = self.db.get(nid)
        if not row:
            return
        self.current_id, title, body, category = row
        self.title_edit.setText(title)
        self.editor.setPlainText(body)
        self.category_label.setText(f"分类：{category or '其他'}")

        fade_in(self.title_edit, duration=180)
        fade_in(self.editor, duration=220)

    def select_note(self, note_id: int) -> bool:
        """在列表中选中指定 id 的笔记"""
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == note_id:
                self.list.setCurrentItem(item)
                return True
        return False

    # ---------- 增删改 ----------
    def _new_note(self):
        self.current_id = None
        self.title_edit.clear()
        self.editor.clear()
        self.category_label.setText("分类：—")
        self.title_edit.setFocus()
        self.list.blockSignals(True)
        self.list.clearSelection()
        self.list.blockSignals(False)

    def _save(self):
        title = self.title_edit.text().strip() or "（无标题）"
        body = self.editor.toPlainText()

        if not body.strip() and not self.title_edit.text().strip():
            QMessageBox.information(self, "提示", "内容为空，无法保存")
            return

        cfg = load_config()
        smart_category = bool(cfg.get("note_smart_category", True))
        smart_reminder = bool(cfg.get("note_smart_reminder", True))

        # 智能分类
        category = "其他"
        if smart_category:
            try:
                category = classify(title, body)
            except Exception:
                category = "其他"

        # 保存
        saved_id = None
        if self.current_id is None:
            saved_id = self.db.add(title, body, category)
        else:
            self.db.update(self.current_id, title, body, category)
            saved_id = self.current_id

        self.win._append(f"笔记已保存：{title}", level="success", source="笔记")
        if smart_category:
            self.win._append(f"智能分类：{category}", level="info", source="笔记")
        self.category_label.setText(f"分类：{category}")
        self._flash_save_btn()
        self._reload_list()

        # 智能提醒识别（提前算一次，入待办和建定时器都用）
        intent = None
        if smart_reminder:
            try:
                intent = scan_note_for_reminder(body)
            except Exception:
                intent = None

        # 建定时器
        if intent:
            secs = int((intent.when - datetime.now()).total_seconds())
            if secs > 0:
                self.scheduler.add_timer(secs, f"笔记提醒：{intent.what}")
                self.win._append(
                    f"检测到提醒：{intent.when:%m-%d %H:%M} {intent.what}",
                    level="action", source="笔记",
                )
                self.win._do_notify(
                    "⏰ 已从笔记创建提醒",
                    f"{intent.when:%H:%M}  {intent.what}",
                )
            else:
                self.win._append(
                    f"提醒时间已过，未创建：{intent.when:%m-%d %H:%M}",
                    level="warn", source="笔记",
                )

        # 入待办判断
        if saved_id is not None:
            should_todo = (category == "待办") or (intent is not None)
            if should_todo and not self.todo_db.has_todo(saved_id):
                due_str = (
                    intent.when.strftime("%Y-%m-%d %H:%M:%S")
                    if intent else None
                )
                self.todo_db.add_from_note(saved_id, due_str)
                self.win._append(
                    f"已加入待办：{title}", level="action", source="待办"
                )

        # 保存后进入新草稿
        self.current_id = None
        self.title_edit.clear()
        self.editor.clear()
        self.category_label.setText("分类：—")
        self.title_edit.setFocus()
        self.list.blockSignals(True)
        self.list.clearSelection()
        self.list.blockSignals(False)

    def _delete(self):
        if self.current_id is None:
            return
        if QMessageBox.question(self, "确认", "删除这条笔记？") != QMessageBox.Yes:
            return
        self.db.delete(self.current_id)
        self.todo_db.cleanup_orphans()
        self.current_id = None
        self.title_edit.clear()
        self.editor.clear()
        self.category_label.setText("分类：—")
        self._reload_list()
        self.win._append("笔记已删除", level="warn", source="笔记")

    def _flash_save_btn(self):
        self.save_btn.setText("已保存 ✓")
        QTimer.singleShot(900, lambda: self.save_btn.setText("保存"))

    # ---------- 导出 ----------
    def _export(self, fmt: str):
        text = self.editor.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "提示", "内容为空，无法导出")
            return

        title = self.title_edit.text().strip() or "笔记"
        default = f"{title}.{fmt}"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出", default, f"{fmt.upper()} (*.{fmt})"
        )
        if not path:
            return
        p = Path(path)

        try:
            if fmt == "docx":
                export_docx(text, p, title)
            elif fmt == "pdf":
                export_pdf(text, p, title)
            else:
                export_markdown(text, p, title)
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
            self.win._append(f"导出失败：{e}", level="error", source="笔记")
            return

        self.win._append(f"已导出：{p.name}", level="success", source="笔记")
        QMessageBox.information(self, "导出成功", f"已保存到：\n{p}")

    # ---------- 清理 ----------
    def cleanup(self):
        try:
            self.editor.clearFocus()
            self.list.clear()
        except Exception:
            pass