from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout,
)

from changelog import CHANGELOG
from anim import fade_in


# 默认深色（拿不到主题时兜底）
_FALLBACK = {
    "bg_card": "#2b2f3a",
    "border": "#3a3f4b",
    "text": "#e8eaed",
    "text_dim": "#9aa2b1",
}


class ChangelogPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[QFrame] = []
        self._first_show = True

        # 从主窗口拿主题色
        self.colors = _FALLBACK
        win = parent
        # 向上找 MainWindow
        w = self
        while w is not None and not hasattr(w, "colors"):
            w = w.parent() if hasattr(w, "parent") else None
        if w is not None and hasattr(w, "colors"):
            self.colors = w.colors

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        c = self.colors
        title = QLabel("更新日志")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {c['text']};"
        )
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(14)

        for rel in CHANGELOG:
            card = self._build_release(rel)
            v.addWidget(card)
            self._cards.append(card)

        v.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

    # ---------- 单个版本卡片 ----------
    def _build_release(self, rel) -> QWidget:
        c = self.colors
        box = QFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 10px;
            }}
        """)
        v = QVBoxLayout(box)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)

        head = QHBoxLayout()
        ver = QLabel(f"v{rel.version}")
        ver.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color:{c['text']}; "
            f"background: transparent;"
        )
        date = QLabel(rel.date)
        date.setStyleSheet(
            f"color:{c['text_dim']}; font-size: 12px; background: transparent;"
        )
        head.addWidget(ver)
        head.addSpacing(10)
        head.addWidget(date)
        head.addStretch()
        v.addLayout(head)

        for item in rel.items:
            line = QLabel(f"•  {item}")
            line.setWordWrap(True)
            line.setStyleSheet(
                f"color:{c['text']}; font-size: 13px; background: transparent;"
            )
            v.addWidget(line)

        return box

    # ---------- 首次显示才播动画 ----------
    def showEvent(self, e):
        super().showEvent(e)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(30, self._play_anim)

    def _play_anim(self):
        for i, card in enumerate(self._cards):
            fade_in(card, duration=260, delay=i * 50)