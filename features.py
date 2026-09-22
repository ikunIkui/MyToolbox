from dataclasses import dataclass
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QComboBox,
)

from widgets import HintBar, DurationPicker, PrimaryButton, ShortcutLabel
from note_page import NotePage
from todo_page import TodoPage
from doc_convert import md_to_docx, docx_to_md, images_to_pdf, merge_pdfs, split_pdf
from pathlib import Path


@dataclass
class Feature:
    key: str
    title: str
    icon: str
    desc: str
    factory: Callable[[], QWidget]
    example: str = ""
    category: str = "其他"


def feature_shell(title, subtitle, body, example, shortcut=""):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(12)

    t = QLabel(title)
    t.setStyleSheet("font-size: 16px; font-weight: bold;")
    s = QLabel(subtitle)
    s.setStyleSheet("color:#9aa2b1;")
    v.addWidget(t)
    v.addWidget(s)
    v.addWidget(body)

    if shortcut:
        v.addWidget(ShortcutLabel(shortcut))
    if example:
        hint = HintBar(example)
        w._hint_bar = hint
        v.addWidget(hint)
    v.addStretch()
    return w


# ==================== 时间管理 ====================

def make_timer_page(on_run, on_hint):
    def _factory():
        picker = DurationPicker(units=("分钟", "小时", "秒"), default=20)
        btn = PrimaryButton("开始倒计时")
        btn.clicked.connect(lambda: on_run(*picker.value()))
        row = QHBoxLayout()
        row.addWidget(QLabel("时长："))
        row.addWidget(picker)
        row.addWidget(btn)
        row.addStretch()
        body = QWidget(); body.setLayout(row)
        page = feature_shell("⏰ 倒计时", "选择一个时长，到点后会弹出通知。",
                             body, "倒计时 20 分钟",
                             "也可以直接输入：倒计时 20 分钟")
        page._hint_bar.use_command.connect(on_hint)
        return page
    return _factory


def make_placeholder(title, hint, example="", shortcut=""):
    def _factory():
        body = QWidget()
        v = QVBoxLayout(body)
        v.addWidget(QLabel(hint))
        v.addStretch()
        return feature_shell(title, "功能开发中…", body, example, shortcut)
    return _factory


# ==================== 系统工具 ====================

def make_shutdown_page(on_run, on_hint):
    def _factory():
        picker = DurationPicker(units=("分钟", "小时"), default=30)
        btn = PrimaryButton("定时关机")
        cancel_btn = QPushButton("取消所有关机任务")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #3a3f4b; color: #e8eaed;
                border: none; border-radius: 6px; padding: 0 16px;
            }
            QPushButton:hover { background: #4a5060; }
        """)
        btn.clicked.connect(lambda: on_run(*picker.value()))
        cancel_btn.clicked.connect(lambda: on_hint("取消关机"))
        row = QHBoxLayout()
        row.addWidget(QLabel("时长："))
        row.addWidget(picker)
        row.addWidget(btn)
        row.addWidget(cancel_btn)
        row.addStretch()
        body = QWidget(); body.setLayout(row)
        page = feature_shell("🔌 定时关机", "到达时间后自动关机，关机前 1 分钟会提醒。",
                             body, "关机 30 分钟",
                             "也可以直接输入：关机 30 分钟")
        page._hint_bar.use_command.connect(on_hint)
        return page
    return _factory


def make_lock_page(on_run, on_hint):
    def _factory():
        btn = PrimaryButton("立即锁屏")
        btn.clicked.connect(on_run)
        row = QHBoxLayout()
        row.addWidget(btn)
        row.addStretch()
        body = QWidget(); body.setLayout(row)
        page = feature_shell("🔒 锁屏", "一键锁定当前屏幕。",
                             body, "锁屏",
                             "也可以尝试使用电脑快捷键：Win + L 哦~\n\n小提示：您可以去设置中调整锁屏延时时长哦~")
        page._hint_bar.use_command.connect(on_hint)
        return page
    return _factory


# ==================== 内容创作 ====================

def make_note_page_factory(win, scheduler):
    def _factory():
        return NotePage(win, scheduler)
    return _factory


def make_todo_page_factory(win):
    def _factory():
        return TodoPage(win)
    return _factory


# ==================== 文档互转 ====================

def make_doc_convert_page(on_hint):
    def _factory():
        body = QWidget()
        v = QVBoxLayout(body)
        v.setSpacing(10)

        # 操作选择
        op_row = QHBoxLayout()
        op_row.addWidget(QLabel("操作："))
        combo = QComboBox()
        combo.addItems([
            "Markdown → Word",
            "Word → Markdown",
            "图片 → PDF",
            "PDF 合并",
            "PDF 拆分",
        ])
        combo.setFixedWidth(220)
        op_row.addWidget(combo)
        op_row.addStretch()
        v.addLayout(op_row)

        # 文件选择区
        file_row = QHBoxLayout()
        file_label = QLabel("未选择文件")
        file_label.setStyleSheet("color:#9aa2b1;")
        pick_btn = QPushButton("选择文件")
        pick_btn.setFixedWidth(100)

        state = {"files": []}

        def pick():
            op = combo.currentText()
            if op == "图片 → PDF":
                paths, _ = QFileDialog.getOpenFileNames(
                    None, "选择图片", "",
                    "图片 (*.png *.jpg *.jpeg *.bmp *.webp)"
                )
            elif op == "PDF 合并":
                paths, _ = QFileDialog.getOpenFileNames(
                    None, "选择 PDF", "", "PDF (*.pdf)"
                )
            elif op == "PDF 拆分":
                path, _ = QFileDialog.getOpenFileName(
                    None, "选择 PDF", "", "PDF (*.pdf)"
                )
                paths = [path] if path else []
            elif op == "Markdown → Word":
                path, _ = QFileDialog.getOpenFileName(
                    None, "选择 Markdown", "", "Markdown (*.md)"
                )
                paths = [path] if path else []
            else:  # Word → Markdown
                path, _ = QFileDialog.getOpenFileName(
                    None, "选择 Word", "", "Word (*.docx)"
                )
                paths = [path] if path else []

            state["files"] = [Path(p) for p in paths if p]
            if state["files"]:
                if len(state["files"]) == 1:
                    file_label.setText(state["files"][0].name)
                else:
                    file_label.setText(f"{len(state['files'])} 个文件")
            else:
                file_label.setText("未选择文件")

        pick_btn.clicked.connect(pick)
        file_row.addWidget(file_label, 1)
        file_row.addWidget(pick_btn)
        v.addLayout(file_row)

        # 执行
        run_btn = PrimaryButton("开始转换")

        def run():
            op = combo.currentText()
            files = state["files"]
            if not files:
                QMessageBox.information(None, "提示", "请先选择文件")
                return

            try:
                if op == "Markdown → Word":
                    out, _ = QFileDialog.getSaveFileName(
                        None, "保存 Word", files[0].stem + ".docx", "Word (*.docx)"
                    )
                    if not out:
                        return
                    md_to_docx(files[0], Path(out))
                    result = out

                elif op == "Word → Markdown":
                    out, _ = QFileDialog.getSaveFileName(
                        None, "保存 Markdown", files[0].stem + ".md", "Markdown (*.md)"
                    )
                    if not out:
                        return
                    docx_to_md(files[0], Path(out))
                    result = out

                elif op == "图片 → PDF":
                    out, _ = QFileDialog.getSaveFileName(
                        None, "保存 PDF", "合并.pdf", "PDF (*.pdf)"
                    )
                    if not out:
                        return
                    images_to_pdf(files, Path(out))
                    result = out

                elif op == "PDF 合并":
                    out, _ = QFileDialog.getSaveFileName(
                        None, "保存 PDF", "合并.pdf", "PDF (*.pdf)"
                    )
                    if not out:
                        return
                    merge_pdfs(files, Path(out))
                    result = out

                elif op == "PDF 拆分":
                    out_dir = QFileDialog.getExistingDirectory(None, "选择输出文件夹")
                    if not out_dir:
                        return
                    outputs = split_pdf(files[0], Path(out_dir))
                    result = f"{len(outputs)} 个文件 → {out_dir}"

                else:
                    return

                on_hint(f"__log__导出成功：{result}")
                QMessageBox.information(None, "成功", f"已完成：\n{result}")

            except Exception as e:
                QMessageBox.warning(None, "失败", str(e))
                on_hint(f"__log__转换失败：{e}")

        run_btn.clicked.connect(run)
        v.addWidget(run_btn)
        v.addStretch()

        page = feature_shell(
            "🔄 文档互转",
            "支持 Markdown ⇄ Word、图片 → PDF、PDF 合并 / 拆分。",
            body, "",
        )
        return page
    return _factory


# ==================== 系统信息 ====================

def make_weather_page(on_set_city, on_auto, on_hint):
    def _factory():
        city_edit = QLineEdit()
        city_edit.setPlaceholderText("城市名，例如 上海")
        set_btn = PrimaryButton("切换城市")
        auto_btn = QPushButton("自动定位")
        auto_btn.setFixedHeight(34)
        auto_btn.setStyleSheet("""
            QPushButton {
                background: #3a3f4b; color: #e8eaed;
                border: none; border-radius: 6px; padding: 0 16px;
            }
            QPushButton:hover { background: #4a5060; }
        """)
        def _set():
            c = city_edit.text().strip()
            if c:
                on_set_city(c)
        set_btn.clicked.connect(_set)
        city_edit.returnPressed.connect(_set)
        auto_btn.clicked.connect(on_auto)
        row = QHBoxLayout()
        row.addWidget(QLabel("城市："))
        row.addWidget(city_edit, 1)
        row.addWidget(set_btn)
        row.addWidget(auto_btn)
        body = QWidget(); body.setLayout(row)
        page = feature_shell("🌤️ 天气城市", "手动指定城市，或恢复自动定位。",
                             body, "天气 上海",
                             "也可以直接输入：天气 上海")
        page._hint_bar.use_command.connect(on_hint)
        return page
    return _factory


# ==================== 注册表（带分类） ====================

CATEGORIES = ["时间管理", "系统工具", "内容创作", "系统信息"]


def get_features(ctx) -> list[Feature]:
    return [
        # 时间管理
        Feature("timer", "倒计时", "⏰", "选择时长，到点提醒",
                make_timer_page(ctx.add_timer, ctx.run_command),
                "倒计时 20 分钟", category="时间管理"),
        Feature("todo", "待办清单", "✅", "从笔记提取的待办事项",
                make_todo_page_factory(ctx.win),
                "", category="时间管理"),

        # 系统工具
        Feature("shutdown", "定时关机", "🔌", "N 分钟后自动关机",
                make_shutdown_page(ctx.add_shutdown, ctx.run_command),
                "关机 30 分钟", category="系统工具"),
        Feature("lock", "锁屏", "🔒", "立即锁定屏幕",
                make_lock_page(ctx.do_lock, ctx.run_command),
                "锁屏", category="系统工具"),

        # 内容创作
        Feature("note", "笔记", "📝", "Markdown 笔记与搜索",
                make_note_page_factory(ctx.win, ctx.win.scheduler),
                "笔记", category="内容创作"),
        Feature("docconvert", "文档互转", "🔄", "Word / PDF / Markdown 互转",
                make_doc_convert_page(ctx.run_command),
                "", category="内容创作"),

        # 系统信息
        Feature("weather", "天气城市", "🌤️", "手动指定或自动定位",
                make_weather_page(ctx.set_weather_city, ctx.weather_auto,
                                  ctx.run_command),
                "天气 上海", category="系统信息"),

        # 占位
        Feature("sysmon", "系统监控", "📊", "CPU / 内存 / 网速",
                make_placeholder("📊 系统监控", "系统监控开发中…", ""),
                "", category="系统信息"),
        Feature("colorpicker", "取色器", "🎨", "屏幕取色",
                make_placeholder("🎨 取色器", "取色器开发中…", ""),
                "", category="系统工具"),
    ]