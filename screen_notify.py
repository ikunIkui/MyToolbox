from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QAbstractAnimation,
    QPoint, Signal, QObject,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QGraphicsDropShadowEffect, QApplication,
)


# ==================== 时长策略 ====================
AUTO_DURATION = True
BASE_MS = 3000
PER_CHAR_MS = 120
MAX_MS = 10000


def calc_duration(msg: str) -> int:
    if not msg:
        return BASE_MS
    return min(MAX_MS, max(BASE_MS, BASE_MS + len(msg) * PER_CHAR_MS))


# ==================== 单个通知卡片 ====================
class ToastWidget(QWidget):
    closed = Signal()
    action = Signal(str)

    CARD_W = 320
    CARD_W_BIG = 380
    CARD_H = 100
    CARD_H_WITH_BUTTONS = 140
    CARD_H_BIG = 130
    MARGIN = 20

    def __init__(self, title: str, msg: str,
                 duration: int = 3000,
                 colors: dict | None = None,
                 position: str = "bottom-right",
                 buttons: list[tuple[str, str]] | None = None,
                 big: bool = False,
                 parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._duration = duration
        self._position = position
        self._buttons = buttons or []
        self._big = big
        self._colors = colors or {
            "bg_card": "#2b2f3a",
            "border": "#3a3f4b",
            "text": "#e8eaed",
            "text_dim": "#9aa2b1",
            "accent": "#4a6bff",
        }

        if big:
            w, h = self.CARD_W_BIG, self.CARD_H_BIG
        elif self._buttons:
            w, h = self.CARD_W, self.CARD_H_WITH_BUTTONS
        else:
            w, h = self.CARD_W, self.CARD_H
        self.setFixedSize(w, h)

        self._build_ui(title, msg)
        self._position_to(self._position)
        self._setup_animations()

    # ---------- UI ----------
    def _build_ui(self, title: str, msg: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QWidget(self)
        card.setObjectName("toastCard")
        card.setStyleSheet(f"""
            QWidget#toastCard {{
                background: {self._colors['bg_card']};
                border: 1px solid {self._colors['border']};
                border-radius: 10px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        cv = QVBoxLayout(card)
        cv.setContentsMargins(14, 10, 10, 10)
        cv.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(6)

        self.title_label = QLabel(title)
        title_size = "16px" if self._big else "14px"
        self.title_label.setStyleSheet(
            f"color:{self._colors['text']}; "
            f"font-size: {title_size}; font-weight: bold; background: transparent;"
        )

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {self._colors['text_dim']};
                background: transparent;
                border: none;
                font-size: 18px;
                font-weight: bold;
                padding: 0;
                min-height: 0;
            }}
            QPushButton:hover {{
                color: {self._colors['text']};
                background: rgba(255,255,255,0.10);
                border-radius: 12px;
            }}
            QPushButton:pressed {{
                background: rgba(255,255,255,0.18);
            }}
        """)
        self.close_btn.clicked.connect(self._on_close_clicked)

        head.addWidget(self.title_label, 1)
        head.addWidget(self.close_btn, 0, Qt.AlignTop | Qt.AlignRight)

        self.msg_label = QLabel(msg)
        msg_size = "13px" if self._big else "12px"
        self.msg_label.setStyleSheet(
            f"color:{self._colors['text_dim']}; "
            f"font-size: {msg_size}; background: transparent;"
        )
        self.msg_label.setWordWrap(True)

        cv.addLayout(head)
        cv.addWidget(self.msg_label)

        if self._buttons:
            btn_row = QHBoxLayout()
            btn_row.setSpacing(6)
            btn_row.addStretch()
            for text, key in self._buttons:
                b = QPushButton(text)
                b.setCursor(Qt.PointingHandCursor)
                b.setFixedHeight(26)
                b.setStyleSheet(f"""
                    QPushButton {{
                        background: {self._colors['accent']};
                        color: white;
                        border: none;
                        border-radius: 5px;
                        padding: 0 12px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{ background: #5f7cff; }}
                    QPushButton:pressed {{ background: #3b57d6; }}
                """)
                b.clicked.connect(
                    lambda _=False, k=key: self._on_button_clicked(k)
                )
                btn_row.addWidget(b)
            cv.addLayout(btn_row)

        cv.addStretch()
        root.addWidget(card)

    # ---------- 位置 ----------
    def _position_to(self, pos: str):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        w, h = self.width(), self.height()
        m = self.MARGIN

        if pos == "bottom-right":
            x = geo.right() - w - m
            y = geo.bottom() - h - m
        elif pos == "bottom-left":
            x = geo.left() + m
            y = geo.bottom() - h - m
        elif pos == "top-right":
            x = geo.right() - w - m
            y = geo.top() + m
        elif pos == "top-left":
            x = geo.left() + m
            y = geo.top() + m
        else:
            x = geo.right() - w - m
            y = geo.bottom() - h - m

        self.move(x, y)

    # ---------- 动画 ----------
    def _setup_animations(self):
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setDuration(260)
        self._slide.setEasingCurve(QEasingCurve.OutCubic)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(220)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.InCubic)
        self._fade.finished.connect(self._finish)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade_out)

    def start(self):
        end = self.pos()
        if "left" in self._position:
            start = QPoint(end.x() - 80, end.y())
        else:
            start = QPoint(end.x() + 80, end.y())

        self._slide.setStartValue(start)
        self._slide.setEndValue(end)
        self._slide.start(QAbstractAnimation.DeleteWhenStopped)

        self.setWindowOpacity(0.0)
        self.show()

        self._fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in.setDuration(180)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start(QAbstractAnimation.DeleteWhenStopped)

        if self._duration > 0 and not self._buttons:
            if AUTO_DURATION:
                d = calc_duration(self.msg_label.text())
            else:
                d = self._duration
            # 欢迎卡片（big）固定停 5 秒
            if self._big:
                d = 5000
            self._timer.start(d)

    # ---------- 关闭 ----------
    def _on_close_clicked(self):
        self._timer.stop()
        self._start_fade_out()

    def _on_button_clicked(self, key: str):
        self._timer.stop()
        self.action.emit(key)
        self._start_fade_out()

    def _start_fade_out(self):
        try:
            self._fade.start(QAbstractAnimation.DeleteWhenStopped)
        except Exception:
            self._finish()

    def _finish(self):
        self.closed.emit()
        self.close()
        self.deleteLater()


# ==================== 队列管理器 ====================
class ToastManager(QObject):
    _instance = None

    @classmethod
    def instance(cls) -> "ToastManager":
        if cls._instance is None:
            cls._instance = ToastManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._queue: list[tuple] = []
        self._current: ToastWidget | None = None
        self._colors: dict | None = None
        self._position: str = "bottom-right"

    def set_colors(self, colors: dict):
        self._colors = colors

    def set_position(self, pos: str):
        if pos in ("bottom-right", "bottom-left", "top-right", "top-left"):
            self._position = pos

    def show(self, title: str, msg: str, duration: int = 3000,
             buttons: list[tuple[str, str]] | None = None,
             on_action=None,
             big: bool = False):
        self._queue.append((title, msg, duration, buttons, on_action, big))
        self._maybe_show_next()

    def _maybe_show_next(self):
        if self._current is not None:
            return
        if not self._queue:
            return

        title, msg, duration, buttons, on_action, big = self._queue.pop(0)
        toast = ToastWidget(
            title, msg, duration,
            colors=self._colors,
            position=self._position,
            buttons=buttons,
            big=big,
        )
        toast.closed.connect(self._on_toast_closed)
        if on_action is not None:
            toast.action.connect(on_action)
        self._current = toast
        toast.start()

    def _on_toast_closed(self):
        self._current = None
        QTimer.singleShot(120, self._maybe_show_next)


# ==================== 对外入口 ====================
def show_toast(title: str, msg: str,
               duration: int = 3000,
               colors: dict | None = None,
               position: str | None = None,
               buttons: list[tuple[str, str]] | None = None,
               on_action=None,
               big: bool = False):
    mgr = ToastManager.instance()
    if colors:
        mgr.set_colors(colors)
    if position:
        mgr.set_position(position)
    mgr.show(title, msg, duration,
             buttons=buttons, on_action=on_action, big=big)