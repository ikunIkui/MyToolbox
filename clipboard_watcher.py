from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from clipboard_db import ClipboardDB
from app_paths import load_config


class ClipboardWatcher(QObject):
    """
    全局剪贴板监听。
    挂在 QApplication.clipboard().dataChanged 上。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = ClipboardDB()
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_changed)
        self._enabled = bool(load_config().get("clipboard_enabled", True))

    def set_enabled(self, on: bool):
        self._enabled = on

    def _on_changed(self):
        # 实时读配置，让设置页改完立刻生效
        try:
            if not load_config().get("clipboard_enabled", True):
                return
        except Exception:
            pass

        try:
            text = self._clipboard.text()
        except Exception:
            return
        if not text:
            return
        try:
            self.db.add(text)
        except Exception as e:
            print(f"[clipboard] 保存失败: {e}")