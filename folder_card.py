from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsDropShadowEffect,
)


# 每个分类的默认皮肤（emoji + 颜色）
DEFAULT_SKINS = {
    "时间管理": {"icon": "⏰", "icon_bg": "#4a6bff", "accent": "#4a6bff"},
    "系统工具": {"icon": "🔧", "icon_bg": "#7ed08a", "accent": "#7ed08a"},
    "内容创作": {"icon": "📝", "icon_bg": "#e6c46a", "accent": "#e6c46a"},
    "系统信息": {"icon": "📊", "icon_bg": "#7aa2ff", "accent": "#7aa2ff"},
    "自动化":   {"icon": "🎯", "icon_bg": "#e07a7a", "accent": "#e07a7a"},
    "其他":     {"icon": "📁", "icon_bg": "#9aa2b1", "accent": "#9aa2b1"},
}


class FolderCard(QFrame):
    """
    文件夹卡片：点击进入分类。
    """
    clicked = Signal(str)   # 参数：category 名

    CARD_W = 240
    CARD_H = 180

    def __init__(self, category: str, count: int,
                 colors: dict = None, skin: dict = None, parent=None):
        super().__init__(parent)
        self.category = category
        self.count = count
        self.colors = colors or {}
        self.skin = skin or DEFAULT_SKINS.get(category, DEFAULT_SKINS["其他"])

        self.setObjectName("folderCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedSize(self.CARD_W, self.CARD_H)
        self.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(10)

        # ===== 图标圆底 =====
        icon_wrap = QFrame()
        icon_wrap.setObjectName("folderIconWrap")
        icon_wrap.setFixedSize(64, 64)
        icon_wrap.setStyleSheet(f"""
            QFrame#folderIconWrap {{
                background: {self.skin['icon_bg']};
                border-radius: 16px;
            }}
        """)

        iv = QVBoxLayout(icon_wrap)
        iv.setContentsMargins(0, 0, 0, 0)

        self.icon_label = QLabel(self.skin["icon"])
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet(
            "font-size: 34px; background: transparent;"
        )
        iv.addWidget(self.icon_label)

        # ===== 标题 =====
        self.title_label = QLabel(category)
        self.title_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; "
            f"color: {self.colors.get('text', '#e8eaed')}; "
            f"background: transparent;"
        )

        # ===== 副标题：X 个工具 =====
        self.sub_label = QLabel(f"{count} 个工具")
        self.sub_label.setStyleSheet(
            f"font-size: 12px; "
            f"color: {self.colors.get('text_dim', '#9aa2b1')}; "
            f"background: transparent;"
        )

        v.addWidget(icon_wrap)
        v.addWidget(self.title_label)
        v.addWidget(self.sub_label)
        v.addStretch()

        # ===== 阴影 =====
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(self.skin["accent"]))
        self._shadow.setOffset(0, 4)
        self.setGraphicsEffect(self._shadow)

        self._shadow_anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._shadow_anim.setDuration(180)
        self._shadow_anim.setEasingCurve(QEasingCurve.OutCubic)

        # ===== 样式 =====
        self._apply_style()

    def _apply_style(self):
        bg = self.colors.get("bg_card", "#2b2f3a")
        border = self.colors.get("border", "#3a3f4b")
        hover_border = self.skin["accent"]

        self.setStyleSheet(f"""
            QFrame#folderCard {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QFrame#folderCard:hover {{
                border: 2px solid {hover_border};
            }}
        """)

    def _animate_shadow(self, target_blur: int):
        try:
            self._shadow_anim.stop()
            self._shadow_anim.setStartValue(self._shadow.blurRadius())
            self._shadow_anim.setEndValue(target_blur)
            self._shadow_anim.start()
        except RuntimeError:
            pass

    def enterEvent(self, e):
        self._animate_shadow(24)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._animate_shadow(0)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self.clicked.emit(self.category)
        super().mousePressEvent(e)