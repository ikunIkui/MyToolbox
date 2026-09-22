from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve, QAbstractAnimation,
    QSequentialAnimationGroup, QPauseAnimation, QPoint, QTimer,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QWidget,
)
from PySide6.QtGui import QColor


def fade_in(widget: QWidget, duration: int = 220, delay: int = 0):
    """
    安全淡入：
    - 如果 widget 还没显示，直接跳过，避免“空白”
    - 用 QTimer.singleShot(0) 等一帧，避免布局未完成
    - 动画结束后清除 effect，避免影响子控件
    """
    def _start():
        if not widget.isVisible():
            widget.setGraphicsEffect(None)
            return

        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            try:
                widget.setGraphicsEffect(None)
            except RuntimeError:
                pass

        if delay > 0:
            group = QSequentialAnimationGroup(widget)
            group.addAnimation(QPauseAnimation(delay, widget))
            group.addAnimation(anim)
            group.finished.connect(_cleanup)
            group.start(QAbstractAnimation.DeleteWhenStopped)
            widget._anim_group = group
        else:
            anim.finished.connect(_cleanup)
            anim.start(QAbstractAnimation.DeleteWhenStopped)
            widget._anim = anim

    QTimer.singleShot(0, _start)


def slide_in_from_right(widget: QWidget, duration: int = 260):
    """从右滑入 + 淡入。只在 widget 可见时播。"""
    def _start():
        if not widget.isVisible():
            return
        start = widget.pos() + QPoint(60, 0)
        end = widget.pos()

        anim = QPropertyAnimation(widget, b"pos", widget)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        widget._slide_anim = anim

        fade_in(widget, duration)

    QTimer.singleShot(0, _start)


def slide_in_from_left(widget: QWidget, duration: int = 260):
    """从左滑入 + 淡入。只在 widget 可见时播。"""
    def _start():
        if not widget.isVisible():
            return
        start = widget.pos() - QPoint(60, 0)
        end = widget.pos()

        anim = QPropertyAnimation(widget, b"pos", widget)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        widget._slide_anim = anim

        fade_in(widget, duration)

    QTimer.singleShot(0, _start)


def apply_hover_shadow(widget: QWidget, color: str = "#5a6bff", blur: int = 18):
    """给控件加一层静态阴影（可配合 hover 使用）"""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setColor(QColor(color))
    effect.setOffset(0, 0)
    widget.setGraphicsEffect(effect)
    return effect