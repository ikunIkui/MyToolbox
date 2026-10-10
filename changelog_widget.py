from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout,
    QPushButton, QLineEdit,
)

from changelog import CHANGELOG
from anim import fade_in


# 默认深色（拿不到主题时兜底）
_FALLBACK = {
    "bg_card": "#2b2f3a",
    "border": "#3a3f4b",
    "text": "#e8eaed",
    "text_dim": "#9aa2b1",
    "accent": "#4a6bff",
}


class ChangelogPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[dict] = []      # 每项：{"release": rel, "frame": QFrame, "body": QWidget, "expanded": bool}
        self._first_show = True

        # 从主窗口拿主题色
        self.colors = _FALLBACK
        w = self
        while w is not None and not hasattr(w, "colors"):
            w = w.parent() if hasattr(w, "parent") else None
        if w is not None and hasattr(w, "colors"):
            self.colors = w.colors

        c = self.colors
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ===== 标题行 =====
        head = QHBoxLayout()
        title = QLabel("更新日志")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {c['text']};"
        )

        # 当前版本
        latest = CHANGELOG[0] if CHANGELOG else None
        if latest:
            ver_lbl = QLabel(f"当前版本：v{latest.version}")
            ver_lbl.setStyleSheet(
                f"font-size: 12px; color: {c['text_dim']};"
            )
        else:
            ver_lbl = QLabel("")

        head.addWidget(title)
        head.addSpacing(12)
        head.addWidget(ver_lbl)
        head.addStretch()
        root.addLayout(head)

        # ===== 搜索 =====
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索更新内容…")
        self.search.textChanged.connect(self._on_search)
        root.addWidget(self.search)

        # ===== 滚动区 =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(4, 4, 4, 4)
        self._inner_layout.setSpacing(10)

        # 只显示有 items 的版本；跳过 admin 那条
        for rel in CHANGELOG:
            if not rel.items:
                continue
            # 跳过内部备注 v0.0.0 admin
            if rel.version == "0.0.0":
                continue

            card = self._build_release(rel, is_latest=(rel is latest))
            self._inner_layout.addWidget(card["frame"])
            self._cards.append(card)

        self._inner_layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

    # ---------- 单个版本卡片 ----------
    def _build_release(self, rel, is_latest: bool) -> dict:
        c = self.colors

        box = QFrame()
        border = c["accent"] if is_latest else c["border"]
        box.setStyleSheet(f"""
            QFrame {{
                background: {c['bg_card']};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)

        v = QVBoxLayout(box)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)

        # ===== 头部：版本 + 日期 + 展开/收起 =====
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

        if is_latest:
            new_tag = QLabel("最新")
            new_tag.setStyleSheet(f"""
                QLabel {{
                    background: {c['accent']};
                    color: white;
                    border-radius: 4px;
                    padding: 1px 8px;
                    font-size: 11px;
                }}
            """)
            head.addSpacing(8)
            head.addWidget(new_tag)

        head.addStretch()

        toggle_btn = QPushButton("收起 ▲" if is_latest else "展开 ▼")
        toggle_btn.setFixedWidth(80)
        toggle_btn.setFixedHeight(24)
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {c['accent']};
                border: 1px solid {c['border']};
                border-radius: 5px;
                font-size: 11px;
                padding: 0;
            }}
            QPushButton:hover {{
                border: 1px solid {c['accent']};
                color: {c['accent']};
            }}
        """)
        head.addWidget(toggle_btn)
        v.addLayout(head)

        # ===== 内容区 =====
        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(0, 4, 0, 0)
        bv.setSpacing(3)

        for item in rel.items:
            line = QLabel(f"•  {item}")
            line.setWordWrap(True)
            line.setStyleSheet(
                f"color:{c['text']}; font-size: 13px; background: transparent;"
            )
            bv.addWidget(line)

        v.addWidget(body)

        # 默认：最新版展开，其他折叠
        body.setVisible(is_latest)

        # 点头部或按钮都能折叠
        card_info = {
            "release": rel,
            "frame": box,
            "body": body,
            "toggle": toggle_btn,
            "expanded": is_latest,
            "header_widgets": [ver, date],
        }

        def _toggle(_=False, info=card_info):
            self._toggle_card(info)

        toggle_btn.clicked.connect(_toggle)

        return card_info

    def _toggle_card(self, info: dict):
        info["expanded"] = not info["expanded"]
        info["body"].setVisible(info["expanded"])
        info["toggle"].setText("收起 ▲" if info["expanded"] else "展开 ▼")

    # ---------- 搜索 ----------
    def _on_search(self, text: str):
        kw = text.strip().lower()

        if not kw:
            # 恢复默认：最新版展开、其他折叠
            latest = CHANGELOG[0] if CHANGELOG else None
            for info in self._cards:
                is_latest = info["release"] is latest
                info["frame"].setVisible(True)
                info["expanded"] = is_latest
                info["body"].setVisible(is_latest)
                info["toggle"].setText("收起 ▲" if is_latest else "展开 ▼")
            return

        # 有搜索词：只显示包含的版本，全部展开
        for info in self._cards:
            rel = info["release"]
            hit = any(kw in item.lower() for item in rel.items)
            if hit:
                info["frame"].setVisible(True)
                info["expanded"] = True
                info["body"].setVisible(True)
                info["toggle"].setText("收起 ▲")
            else:
                info["frame"].setVisible(False)

    # ---------- 首次显示才播动画 ----------
    def showEvent(self, e):
        super().showEvent(e)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(30, self._play_anim)

    def _play_anim(self):
        for i, info in enumerate(self._cards):
            if info["frame"].isVisible():
                fade_in(info["frame"], duration=240, delay=i * 40)