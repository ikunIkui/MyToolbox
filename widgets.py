from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox,
    QLineEdit, QFrame,
)


class HintBar(QFrame):
    """底部提示：没有你想选的？试试输入绝对指令：xxx"""
    use_command = Signal(str)

    def __init__(self, example: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            HintBar {
                background: #232734;
                border: 1px solid #3a3f4b;
                border-radius: 8px;
            }
            QLabel { color: #9aa2b1; }
        """)
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(6)

        h.addWidget(QLabel("没有你想选的？试试输入绝对指令："))

        btn = QPushButton(example)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #7aa2ff;
                border: none;
                text-decoration: underline;
                padding: 0;
            }
            QPushButton:hover { color: #a8c0ff; }
        """)
        btn.clicked.connect(lambda: self.use_command.emit(example))
        h.addWidget(btn)
        h.addStretch()


class ShortcutLabel(QLabel):
    """灰色小字，用于显示快捷键提示"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("color:#7d8493; font-size: 12px;")
        self.setWordWrap(True)


class DurationPicker(QWidget):
    """时长选择：数字 + 单位下拉"""
    def __init__(self, units=("分钟", "小时", "秒"), default=30, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self.spin = QSpinBox()
        self.spin.setRange(1, 9999)
        self.spin.setValue(default)
        self.spin.setFixedWidth(100)

        self.unit = QComboBox()
        self.unit.addItems(list(units))
        self.unit.setFixedWidth(90)

        h.addWidget(self.spin)
        h.addWidget(self.unit)
        h.addStretch()

    def value(self) -> tuple[int, str]:
        return self.spin.value(), self.unit.currentText()


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: #4a6bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 18px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5f7cff; }
            QPushButton:pressed { background: #3b57d6; }
        """)