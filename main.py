import os
import sys

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from PySide6.QtCore import QSharedMemory, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

from scheduler import TaskScheduler
from main_window import MainWindow
from theme import ThemeManager


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    shared = QSharedMemory("MyToolbox-SingleInstance")
    if not shared.create(1):
        QMessageBox.information(None, "MyToolbox", "程序已在运行，请查看系统托盘。")
        return 0

    theme = ThemeManager()
    theme.apply(app)

    scheduler = TaskScheduler()
    win = MainWindow(scheduler, theme)
    win.show()
    win.startup_post()   # ← 新增
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())