import os
import sys

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from PySide6.QtCore import QSharedMemory, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

from scheduler import TaskScheduler
from main_window import MainWindow
from theme import ThemeManager


def main() -> int:
    # 判断是否开机自启
    is_autostart = "--autostart" in sys.argv

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    shared = QSharedMemory("MyToolbox-SingleInstance")
    if not shared.create(1):
        # 已经在运行：如果这次是自启触发的，就静默退出
        if not is_autostart:
            QMessageBox.information(
                None, "MyToolbox", "程序已在运行，请查看系统托盘。"
            )
        return 0

    theme = ThemeManager()
    theme.apply(app)

    scheduler = TaskScheduler()
    win = MainWindow(scheduler, theme)

    if is_autostart:
        # 开机自启：不显示主窗口，只留托盘
        win.hide()
        # 托盘气泡提示
        QTimer.singleShot(1500, lambda: win.tray.showMessage(
            "MyToolbox 已启动",
            "程序在后台运行，双击托盘图标可打开",
            QSystemTrayIcon.Information,
            3000,
        ))
        # 开机自启也弹欢迎卡片（可选）
        # QTimer.singleShot(3000, win._show_welcome)
    else:
        # 手动启动：显示主窗口 + 启动动画 + 欢迎卡片
        win.show()
        win.startup_post()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())