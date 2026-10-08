import time
from dataclasses import dataclass

import win32api
import win32con
import win32gui

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QDoubleSpinBox, QComboBox, QPlainTextEdit,
    QGroupBox, QListWidget, QDialog, QMessageBox, QFrame,
    QScrollArea,
)


# ==================== 虚拟键码表 ====================
VK_MAP = {
    # 字母
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "F": 0x46, "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F,
    "P": 0x50, "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54,
    "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59,
    "Z": 0x5A,
    # 数字
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    # 功能键
    "Space": 0x20, "Enter": 0x0D, "Tab": 0x09, "Esc": 0x1B,
    "Backspace": 0x08, "Delete": 0x2E,
    # 方向键
    "Up": 0x26, "Down": 0x28, "Left": 0x25, "Right": 0x27,
    # F1~F12
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}


def make_lparam(vk: int, keyup: bool = False) -> int:
    """构造 PostMessage 用的 lParam"""
    scan = win32api.MapVirtualKey(vk, 0)
    lparam = 1 | (scan << 16)
    if keyup:
        lparam |= (1 << 30) | (1 << 31)
    return lparam


# ==================== 任务 ====================
@dataclass
class ClickTask:
    key: str
    vk: int
    interval: float
    next_at: float


# ==================== 工作线程 ====================
class ClickerWorker(QThread):
    log = Signal(str)
    stopped = Signal()

    def __init__(self, hwnd: int, tasks: list[ClickTask], mode: str):
        super().__init__()
        self.hwnd = hwnd
        self.tasks = tasks
        self.mode = mode          # "post" | "input"
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        self.log.emit(f"开始运行（{'后台发送' if self.mode == 'post' else '模拟按键'}）")
        while self._running:
            now = time.time()
            for t in self.tasks:
                if not self._running:
                    break
                if now >= t.next_at:
                    try:
                        if self.mode == "post":
                            self._send_post(t.vk)
                        else:
                            self._send_input(t.vk)
                    except Exception as e:
                        self.log.emit(f"发送 {t.key} 失败: {e}")
                    t.next_at = now + t.interval
            time.sleep(0.001)
        self.log.emit("已停止")
        self.stopped.emit()

    def _send_post(self, vk: int):
        win32api.PostMessage(
            self.hwnd, win32con.WM_KEYDOWN, vk,
            make_lparam(vk, False),
        )
        win32api.PostMessage(
            self.hwnd, win32con.WM_KEYUP, vk,
            make_lparam(vk, True),
        )

    def _send_input(self, vk: int):
        # 先激活窗口
        try:
            if win32gui.GetForegroundWindow() != self.hwnd:
                win32gui.SetForegroundWindow(self.hwnd)
        except Exception:
            pass
        win32api.keybd_event(vk, 0, 0, 0)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)


# ==================== 窗口选择对话框 ====================
class WindowPickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择目标窗口")
        self.resize(460, 400)
        self.picked_hwnd = None
        self.picked_title = ""

        v = QVBoxLayout(self)

        tip = QLabel("选择要连点的窗口：")
        v.addWidget(tip)

        self.listbox = QListWidget()
        v.addWidget(self.listbox, 1)

        self._wins: list[tuple[int, str]] = []
        self._enum_windows()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        v.addLayout(btn_row)

    def _enum_windows(self):
        def enum_cb(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd)
                if not title.strip():
                    return True
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                if ex_style & win32con.WS_EX_TOOLWINDOW:
                    return True
                self._wins.append((hwnd, title))
                self.listbox.addItem(title)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass

    def _on_ok(self):
        row = self.listbox.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个窗口")
            return
        self.picked_hwnd, self.picked_title = self._wins[row]
        self.accept()


# ==================== 按键行控件 ====================
class KeyRow(QFrame):
    """一行：启用 + 按键下拉 + 间隔输入 + 删除按钮"""

    def __init__(self, key: str = "A", interval: float = 0.1,
                 enabled: bool = True, on_delete=None, colors: dict = None):
        super().__init__()
        self.colors = colors or {}
        self.on_delete = on_delete

        h = QHBoxLayout(self)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(8)

        self.enabled_cb = QCheckBox()
        self.enabled_cb.setChecked(enabled)

        self.key_combo = QComboBox()
        self.key_combo.addItems(list(VK_MAP.keys()))
        self.key_combo.setCurrentText(key)
        self.key_combo.setFixedWidth(100)

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.01, 60.0)
        self.interval_spin.setSingleStep(0.05)
        self.interval_spin.setDecimals(2)
        self.interval_spin.setValue(interval)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setFixedWidth(110)

        del_btn = QPushButton("删除")
        del_btn.setFixedWidth(60)
        del_btn.clicked.connect(self._on_delete)

        h.addWidget(self.enabled_cb)
        h.addWidget(self.key_combo)
        h.addWidget(self.interval_spin)
        h.addStretch()
        h.addWidget(del_btn)

    def _on_delete(self):
        if self.on_delete:
            self.on_delete(self)

    def get_config(self) -> dict | None:
        """返回 {key, interval} 或 None（未启用）"""
        if not self.enabled_cb.isChecked():
            return None
        return {
            "key": self.key_combo.currentText(),
            "interval": float(self.interval_spin.value()),
        }


# ==================== 主页面 ====================
class ClickerPage(QWidget):
    log_signal = Signal(str)

    def __init__(self, win, colors: dict = None, parent=None):
        super().__init__(parent)
        self.win = win
        self.colors = colors or {}
        self.target_hwnd: int | None = None
        self.worker: ClickerWorker | None = None
        self.key_rows: list[KeyRow] = []

        self.log_signal.connect(self._append_log)

        self._build_ui()
        self._add_key_row("A", 0.1, True)
        self._add_key_row("J", 0.1, True)

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        title = QLabel("键盘连点器")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        tip = QLabel("自动按键工具，支持自定义按键和间隔")
        tip.setStyleSheet("color: #9aa2b1; font-size: 12px;")
        root.addWidget(tip)

        # ===== 目标窗口 =====
        g1 = QGroupBox("目标窗口")
        g1v = QVBoxLayout(g1)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("当前："))
        self.target_label = QLabel("（未选择）")
        self.target_label.setStyleSheet("color: #4a6bff;")
        row1.addWidget(self.target_label, 1)
        g1v.addLayout(row1)

        row2 = QHBoxLayout()
        pick_btn = QPushButton("选择窗口")
        pick_btn.clicked.connect(self._pick_window)
        pick_cur_btn = QPushButton("用当前窗口（3 秒后）")
        pick_cur_btn.clicked.connect(self._pick_current_after_delay)
        row2.addWidget(pick_btn)
        row2.addWidget(pick_cur_btn)
        row2.addStretch()
        g1v.addLayout(row2)

        root.addWidget(g1)

        # ===== 发送模式 =====
        g2 = QGroupBox("发送模式")
        g2v = QVBoxLayout(g2)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "后台发送（PostMessage，不抢焦点）",
            "模拟按键（SendInput，兼容性好）",
        ])
        g2v.addWidget(self.mode_combo)

        root.addWidget(g2)

        # ===== 按键配置 =====
        g3 = QGroupBox("按键配置")
        g3v = QVBoxLayout(g3)

        head = QHBoxLayout()
        head.addWidget(QLabel("启用"))
        head.addWidget(QLabel("按键"))
        head.addWidget(QLabel("间隔"))
        head.addStretch()
        g3v.addLayout(head)

        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)
        g3v.addWidget(self.rows_container)

        add_btn = QPushButton("+ 添加按键")
        add_btn.setFixedWidth(120)
        add_btn.clicked.connect(lambda: self._add_key_row("A", 0.1, True))
        g3v.addWidget(add_btn)

        root.addWidget(g3)

        # ===== 控制 =====
        ctrl = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.start_btn.setFixedHeight(36)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50; color: white;
                border: none; border-radius: 6px;
                font-weight: bold; padding: 0 24px;
            }
            QPushButton:hover { background: #5CBF60; }
            QPushButton:disabled { background: #3a3f4b; color: #7d8493; }
        """)
        self.start_btn.clicked.connect(self._on_start)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #f44336; color: white;
                border: none; border-radius: 6px;
                font-weight: bold; padding: 0 24px;
            }
            QPushButton:hover { background: #f55a50; }
            QPushButton:disabled { background: #3a3f4b; color: #7d8493; }
        """)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)

        ctrl.addWidget(self.start_btn)
        ctrl.addWidget(self.stop_btn)
        ctrl.addStretch()
        root.addLayout(ctrl)

        self.status_label = QLabel("状态：已停止")
        self.status_label.setStyleSheet("color: #4a6bff;")
        root.addWidget(self.status_label)

        # ===== 日志 =====
        g4 = QGroupBox("日志")
        g4v = QVBoxLayout(g4)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px;"
        )
        self.log_view.setFixedHeight(120)
        g4v.addWidget(self.log_view)

        root.addWidget(g4)

        root.addStretch()

    # ---------- 按键行管理 ----------
    def _add_key_row(self, key: str, interval: float, enabled: bool):
        row = KeyRow(
            key=key, interval=interval, enabled=enabled,
            on_delete=self._remove_key_row,
            colors=self.colors,
        )
        self.key_rows.append(row)
        self.rows_layout.addWidget(row)

    def _remove_key_row(self, row: KeyRow):
        if row in self.key_rows:
            self.key_rows.remove(row)
        row.setParent(None)
        row.deleteLater()

    # ---------- 目标窗口 ----------
    def _pick_window(self):
        dlg = WindowPickerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.target_hwnd = dlg.picked_hwnd
            self.target_label.setText(
                f"{dlg.picked_title}  (HWND: {dlg.picked_hwnd})"
            )
            self._log(f"已选择目标窗口：{dlg.picked_title}")

    def _pick_current_after_delay(self):
        self._log("请在 3 秒内切换到目标窗口...")
        QTimer.singleShot(3000, self._grab_foreground)

    def _grab_foreground(self):
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        self.target_hwnd = hwnd
        self.target_label.setText(f"{title}  (HWND: {hwnd})")
        self._log(f"已选择目标窗口：{title}")

    # ---------- 开始 / 停止 ----------
    def _on_start(self):
        if self.worker and self.worker.isRunning():
            return

        if self.target_hwnd is None:
            QMessageBox.warning(self, "提示", "请先选择目标窗口")
            return

        if not win32gui.IsWindow(self.target_hwnd):
            QMessageBox.warning(self, "错误", "目标窗口已关闭，请重新选择")
            self.target_hwnd = None
            self.target_label.setText("（未选择）")
            return

        # 收集任务
        tasks: list[ClickTask] = []
        now = time.time()
        for row in self.key_rows:
            cfg = row.get_config()
            if not cfg:
                continue
            key = cfg["key"]
            vk = VK_MAP.get(key)
            if vk is None:
                continue
            tasks.append(ClickTask(
                key=key, vk=vk, interval=cfg["interval"], next_at=now,
            ))

        if not tasks:
            QMessageBox.warning(self, "提示", "请至少启用一个按键")
            return

        mode = "post" if self.mode_combo.currentIndex() == 0 else "input"

        self.worker = ClickerWorker(self.target_hwnd, tasks, mode)
        self.worker.log.connect(self._append_log)
        self.worker.stopped.connect(self._on_worker_stopped)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("状态：运行中")

    def _on_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

    def _on_worker_stopped(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("状态：已停止")
        self.worker = None

    # ---------- 日志 ----------
    def _log(self, msg: str):
        self.log_signal.emit(msg)

    def _append_log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] {msg}")
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---------- 清理 ----------
    def cleanup(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1000)