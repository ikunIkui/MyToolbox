import os
import subprocess
import webbrowser
from screen_notify import show_toast, ToastManager
from datetime import datetime
from settings_page import SettingsPage
from PySide6.QtCore import (
    Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QAbstractAnimation,
    QRect,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QListWidget, QStackedWidget, QLabel, QPlainTextEdit,
    QSystemTrayIcon, QMenu, QStyle, QApplication, QFrame, QScrollArea,
    QGraphicsDropShadowEffect, QTextEdit, QMessageBox,
)

from commands import CommandRegistry
from notifier import notify as send_notify
from scheduler import TaskScheduler, fmt_duration
from weather_widget import WeatherCard
from features import Feature, get_features
from changelog_widget import ChangelogPage
from anim import fade_in, slide_in_from_right, slide_in_from_left
from logger import ActionLogger
from task_history import TaskHistory
from app_paths import load_config, save_config


UNIT = {
    "秒": 1, "s": 1,
    "分钟": 60, "分": 60, "min": 60,
    "小时": 3600, "时": 3600, "h": 3600,
}

DEFAULT_COLORS = {
    "bg": "#1e2128", "bg_alt": "#232734", "bg_card": "#2b2f3a",
    "bg_card_hover": "#333846", "border": "#3a3f4b",
    "border_hover": "#5a6bff", "text": "#e8eaed", "text_dim": "#9aa2b1",
    "text_hint": "#7d8493", "accent": "#4a6bff",
    "success": "#7ed08a", "warn": "#e6c46a", "error": "#e07a7a",
    "action": "#7aa2ff", "shadow": "#5a6bff",
}

MIN_W, MIN_H = 720, 480
DEFAULT_W, DEFAULT_H = 1040, 680


# ==================== 声音辅助 ====================
def play_notify_sound():
    try:
        from sound import play_notify
        play_notify()
    except Exception as e:
        print(f"[sound] 播放失败: {e}")


# ==================== 锁屏辅助 ====================
def schedule_lock(win, source: str = "系统"):
    cfg = load_config()
    delay_ms = max(0, int(cfg.get("lock_delay_ms", 3000)))
    secs = delay_ms / 1000.0

    if delay_ms < 1000:
        msg = "即将锁定屏幕"
    else:
        msg = f"屏幕将在 {secs:g} 秒后锁定"

    win._do_notify("🔒 即将锁屏", msg)
    win._append(f"已执行锁屏（延迟 {secs:g} 秒）", level="action", source=source)

    def _do_lock_now():
        try:
            subprocess.run(
                "rundll32.exe user32.dll,LockWorkStation",
                shell=True, check=False,
            )
        except Exception as e:
            print(f"[lock] 失败: {e}")

    QTimer.singleShot(delay_ms, _do_lock_now)


# ==================== 任务面板 ====================
class TaskPanel(QWidget):
    def __init__(self, scheduler: TaskScheduler, history: TaskHistory, colors: dict = None):
        super().__init__()
        self.scheduler = scheduler
        self.history = history
        self.colors = colors or DEFAULT_COLORS

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        title1 = QLabel("进行中")
        title1.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(title1)

        self._active_layout = QVBoxLayout()
        self._active_layout.setAlignment(Qt.AlignTop)
        self._active_layout.setSpacing(6)
        root.addLayout(self._active_layout)

        hist_bar = QHBoxLayout()
        title2 = QLabel("历史记录")
        title2.setStyleSheet("font-size: 14px; font-weight: bold;")
        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self._clear_history)
        hist_bar.addWidget(title2)
        hist_bar.addStretch()
        hist_bar.addWidget(clear_btn)
        root.addLayout(hist_bar)

        self._hist_layout = QVBoxLayout()
        self._hist_layout.setAlignment(Qt.AlignTop)
        self._hist_layout.setSpacing(4)
        root.addLayout(self._hist_layout)

        root.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(1000)

        self._known_ids: set[str] = set()
        self.refresh()

    def refresh(self):
        self._refresh_active()
        self._refresh_history()

    def _refresh_active(self):
        while self._active_layout.count():
            item = self._active_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        tasks = self.scheduler.list_tasks()
        if not tasks:
            self._active_layout.addWidget(QLabel("暂无进行中的任务"))
            self._known_ids.clear()
            return

        now = datetime.now()
        current_ids = set()
        for t in tasks:
            current_ids.add(t.id)
            remain = max(0, int((t.due_at - now).total_seconds()))
            icon = "⏰" if t.kind == "timer" else "🔌"

            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)

            label = QLabel(f"{icon} {t.label}    剩余 {fmt_duration(remain)}")
            btn = QPushButton("取消")
            btn.setFixedWidth(70)
            btn.clicked.connect(lambda _=False, task=t: self._cancel_task(task))

            h.addWidget(label)
            h.addStretch()
            h.addWidget(btn)
            self._active_layout.addWidget(row)

            if t.id not in self._known_ids and row.isVisible():
                fade_in(row, duration=200)

        self._known_ids = current_ids

    def _refresh_history(self):
        while self._hist_layout.count():
            item = self._hist_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        rows = self.history.recent(50)
        if not rows:
            self._hist_layout.addWidget(QLabel("暂无历史记录"))
            return

        for _id, kind, label, status, _created, ended in rows:
            icon = "⏰" if kind == "timer" else "🔌"
            if status == "done":
                status_text = "✅ 已完成"
                color = self.colors["success"]
            elif status == "cancelled":
                status_text = "❌ 已取消"
                color = self.colors["warn"]
            else:
                status_text = "⚠️ 已中断"
                color = self.colors["text_dim"]

            line = QLabel(f"{icon} {label}    {status_text}    {ended}")
            line.setStyleSheet(f"color: {color}; font-size: 12px;")
            self._hist_layout.addWidget(line)

    def _cancel_task(self, task):
        ok = self.scheduler.cancel(task.id)
        if ok:
            win = self.window()
            if hasattr(win, "_append"):
                kind = "倒计时" if task.kind == "timer" else "定时关机"
                win._append(f"已取消{kind}任务：{task.label}",
                            level="warn", source="任务")
                win._do_notify(f"已取消{kind}", task.label)
        self.refresh()

    def _clear_history(self):
        if QMessageBox.question(self, "确认", "清空所有历史记录？") != QMessageBox.Yes:
            return
        self.history.clear()
        self.refresh()


# ==================== 功能卡片 ====================
class FeatureCard(QFrame):
    clicked = Signal(str)
    BASE_W, BASE_H = 170, 110

    def __init__(self, feature: Feature, colors: dict = None, parent=None):
        super().__init__(parent)
        self.feature = feature
        self.colors = colors or DEFAULT_COLORS

        self.setObjectName("featureCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedSize(self.BASE_W, self.BASE_H)
        self.setCursor(Qt.PointingHandCursor)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(4)

        self.icon_label = QLabel(feature.icon)
        self.icon_label.setStyleSheet("font-size: 26px; background: transparent;")

        self.title_label = QLabel(feature.title)
        self.title_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; background: transparent;"
        )

        self.desc_label = QLabel(feature.desc)
        self.desc_label.setStyleSheet("font-size: 11px; background: transparent;")
        self.desc_label.setWordWrap(True)

        v.addWidget(self.icon_label)
        v.addWidget(self.title_label)
        v.addWidget(self.desc_label)
        v.addStretch()

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(self.colors["shadow"]))
        self._shadow.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow)

        self._shadow_anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._shadow_anim.setDuration(160)
        self._shadow_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _animate_shadow(self, target_blur: int):
        try:
            self._shadow_anim.stop()
            self._shadow_anim.setStartValue(self._shadow.blurRadius())
            self._shadow_anim.setEndValue(target_blur)
            self._shadow_anim.start()
        except RuntimeError:
            pass

    def enterEvent(self, e):
        self._animate_shadow(22)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._animate_shadow(0)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self.clicked.emit(self.feature.key)
        super().mousePressEvent(e)


# ==================== 功能上下文 ====================
class FeatureContext:
    def __init__(self, window: "MainWindow"):
        self.win = window

    def run_command(self, text: str):
        self.win.run_command_text(text)

    def log_action(self, text: str, level: str = "action"):
        self.win._append(text, level=level, source="功能页")

    def add_timer(self, n: int, unit: str):
        self.win.scheduler.add_timer(n * UNIT[unit], f"{n}{unit}倒计时")
        self.win._do_notify("⏰ 已设置", f"{n}{unit} 后提醒")
        self.log_action(f"已设置倒计时：{n}{unit}")

    def add_shutdown(self, n: int, unit: str):
        self.win.scheduler.add_shutdown(n * UNIT[unit])
        self.win._do_notify("🔌 已设置", f"{n}{unit} 后自动关机")
        self.log_action(f"已设置定时关机：{n}{unit}")

    def do_lock(self):
        schedule_lock(self.win, source="功能页")

    def set_weather_city(self, city: str):
        self.win.weather_card.set_city(city)
        self.win._do_notify("🌤️ 天气城市已切换", city)

    def weather_auto(self):
        self.win.weather_card.reset_auto()
        self.win._do_notify("📍 已切换为自动定位", "正在重新获取…")


# ==================== 首页 ====================
class FeaturesPage(QWidget):
    VOLATILE_KEYS = {"note", "weather", "docconvert", "todo"}

    def go_home(self):
        self.stack.setCurrentIndex(0)
        QTimer.singleShot(0, self._play_grid_anim)

    def __init__(self, ctx: FeatureContext, colors: dict = None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.colors = colors or DEFAULT_COLORS
        self.features = get_features(ctx)
        self._feature_map = {f.key: f for f in self.features}
        self._cards: list[FeatureCard] = []
        self._first_show = True
        self._detail_cache: dict[str, QWidget] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)
        self.stack.addWidget(self._build_grid_page())
        self.stack.setCurrentIndex(0)

    def _build_grid_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        inner_v = QVBoxLayout(inner)
        inner_v.setContentsMargins(4, 4, 4, 4)
        inner_v.setSpacing(20)

        groups: dict[str, list[Feature]] = {}
        for f in self.features:
            groups.setdefault(f.category, []).append(f)

        order = ["时间管理", "系统工具", "内容创作", "系统信息", "其他"]
        ordered = [(c, groups[c]) for c in order if c in groups]

        self._cards.clear()
        cols = 4

        for cat, feats in ordered:
            title = QLabel(cat)
            title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px 0;")
            inner_v.addWidget(title)

            grid_wrap = QWidget()
            grid = QGridLayout(grid_wrap)
            grid.setSpacing(12)
            grid.setContentsMargins(0, 0, 0, 0)

            for i, f in enumerate(feats):
                card = FeatureCard(f, self.colors)
                card.clicked.connect(self._open_feature)
                grid.addWidget(card, i // cols, i % cols)
                self._cards.append(card)

            grid.setColumnStretch(cols, 1)
            inner_v.addWidget(grid_wrap)

        inner_v.addStretch()
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)
        return page

    def showEvent(self, e):
        super().showEvent(e)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(30, self._play_grid_anim)

    def _play_grid_anim(self):
        if self.stack.currentIndex() != 0:
            return
        for i, card in enumerate(self._cards):
            fade_in(card, duration=260, delay=i * 40)

    def _open_feature(self, key: str):
        feature = self._feature_map.get(key)
        if not feature:
            return

        if key in self.VOLATILE_KEYS:
            self._destroy_detail(key)

        if key in self._detail_cache:
            detail = self._detail_cache[key]
            self.stack.setCurrentWidget(detail)
            QTimer.singleShot(0, lambda: slide_in_from_right(detail, duration=240))
            return

        detail = QWidget()
        v = QVBoxLayout(detail)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        bar = QHBoxLayout()
        back = QPushButton("← 返回")
        back.setFixedWidth(80)
        back.clicked.connect(self._go_back)
        title = QLabel(f"{feature.icon}  {feature.title}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        bar.addWidget(back)
        bar.addWidget(title)
        bar.addStretch()
        v.addLayout(bar)

        try:
            body = feature.factory()
        except Exception as e:
            body = QLabel(f"⚠️ 功能加载失败：{e}")
            body.setStyleSheet("padding: 20px;")

        body_scroll = QScrollArea()
        body_scroll.setWidgetResizable(True)
        body_scroll.setFrameShape(QFrame.NoFrame)
        body_scroll.setWidget(body)
        v.addWidget(body_scroll, 1)

        self._detail_cache[key] = detail
        self.stack.addWidget(detail)
        self.stack.setCurrentWidget(detail)
        QTimer.singleShot(0, lambda: slide_in_from_right(detail, duration=240))

    def _destroy_detail(self, key: str):
        detail = self._detail_cache.pop(key, None)
        if detail is None:
            return
        if hasattr(detail, "cleanup"):
            try:
                detail.cleanup()
            except Exception:
                pass
        self.stack.removeWidget(detail)
        detail.setParent(None)
        detail.deleteLater()

    def _go_back(self):
        cur = self.stack.currentWidget()
        if cur is not None and cur is not self.stack.widget(0):
            for k, v in list(self._detail_cache.items()):
                if v is cur and k in self.VOLATILE_KEYS:
                    self._destroy_detail(k)
                    break

        self.stack.setCurrentIndex(0)
        QTimer.singleShot(0, self._play_grid_anim)


# ==================== 日志页 ====================
class LogPage(QWidget):
    def __init__(self, win: "MainWindow", colors: dict = None, parent=None):
        super().__init__(parent)
        self.win = win
        self.colors = colors or DEFAULT_COLORS

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        bar = QHBoxLayout()
        tip = QLabel("操作日志（详细记录您的时间 · 来源 · 内容）")
        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self._clear)
        bar.addWidget(tip)
        bar.addStretch()
        bar.addWidget(clear_btn)
        v.addLayout(bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px; padding: 8px;"
        )
        v.addWidget(self.log_view, 1)

    def _clear(self):
        box = QMessageBox(self)
        box.setWindowTitle("确认清空")
        box.setIcon(QMessageBox.Warning)
        box.setText("确定要清空所有操作日志吗？")
        box.setInformativeText(
            "⚠️ 建议您先打开数据目录备份文件后再清空，此操作不可恢复。"
        )

        yes_btn = box.addButton("确认清空", QMessageBox.YesRole)
        open_btn = box.addButton("打开数据目录", QMessageBox.ActionRole)
        cancel_btn = box.addButton("取消", QMessageBox.RejectRole)
        box.setDefaultButton(cancel_btn)

        box.exec()
        clicked = box.clickedButton()

        if clicked is open_btn:
            self._open_data_dir()
            return
        if clicked is not yes_btn:
            return

        self.win.logger.clear()
        self.log_view.clear()
        self.win._append("日志已清空", level="warn", source="系统")

    def _open_data_dir(self):
        from app_paths import get_data_dir
        path = str(get_data_dir())
        try:
            os.startfile(path)
        except Exception:
            subprocess.Popen(f'explorer "{path}"', shell=True)

    def append_html(self, html: str):
        self.log_view.append(html)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def load_recent(self, rows):
        for ts, level, source, message in rows:
            c = self.colors
            color = {
                "info": c["text"],
                "success": c["success"],
                "warn": c["warn"],
                "error": c["error"],
                "action": c["action"],
            }.get(level, c["text"])
            html = (
                f'<div style="margin:2px 0;">'
                f'<span style="color:{c["text_hint"]};">[{ts}]</span> '
                f'<span style="color:{c["text_dim"]};">({source})</span> '
                f'<span style="color:{color};">{self.win._escape(message)}</span>'
                f'</div>'
            )
            self.log_view.append(html)


# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    notify_signal = Signal(str, str)
    timer_done_signal = Signal(object)

    def __init__(self, scheduler: TaskScheduler, theme=None):
        super().__init__()
        self.scheduler = scheduler
        self.theme = theme
        self.colors = theme.colors if theme else DEFAULT_COLORS
        self.registry = CommandRegistry()
        self.logger = ActionLogger()
        self.history = TaskHistory()
        self.scheduler.set_history(self.history)
        self.ctx = FeatureContext(self)

        self.setWindowTitle("MyToolbox")
        self.setMinimumSize(MIN_W, MIN_H)

        self._build_ui()
        self._register_commands()
        self._build_tray()

        self._restore_geometry()

        self.notify_signal.connect(self._do_notify)
        self.timer_done_signal.connect(self._on_timer_done)
        self.scheduler.set_notify(lambda t, m: self.notify_signal.emit(t, m))
        self.scheduler.set_notify_timer_done(
            lambda task: self.timer_done_signal.emit(task)
        )

        ToastManager.instance().set_colors(self.colors)

        self._append("MyToolbox 已启动", level="info", source="系统")

        if theme is not None:
            theme.changed.connect(self._on_theme_changed)

        try:
            import autostart
            if autostart.is_enabled():
                autostart.enable()
        except Exception:
            pass

    # ---------- 窗口几何 ----------
    def _restore_geometry(self):
        cfg = load_config()
        geo = cfg.get("window_geometry", "")
        maximized = bool(cfg.get("window_maximized", False))

        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1280, 800)

        restored = False
        if geo:
            try:
                x, y, w, h = (int(v) for v in geo.split(","))
                if w >= MIN_W and h >= MIN_H:
                    if avail.intersects(QRect(x, y, w, h)):
                        self.setGeometry(x, y, w, h)
                        restored = True
            except Exception:
                restored = False

        if not restored:
            w = max(MIN_W, min(DEFAULT_W, int(avail.width() * 0.65)))
            h = max(MIN_H, min(DEFAULT_H, int(avail.height() * 0.75)))
            x = avail.left() + (avail.width() - w) // 2
            y = avail.top() + (avail.height() - h) // 2
            self.setGeometry(x, y, w, h)

        if maximized:
            self.setWindowState(Qt.WindowMaximized)

    def _save_geometry(self):
        try:
            if self.isMaximized():
                cfg = load_config()
                cfg["window_maximized"] = True
                save_config(cfg)
                return

            g = self.geometry()
            geo_str = f"{g.x()},{g.y()},{g.width()},{g.height()}"
            cfg = load_config()
            cfg["window_geometry"] = geo_str
            cfg["window_maximized"] = False
            save_config(cfg)
        except Exception as e:
            print(f"[geometry] 保存失败: {e}")

    def _on_theme_changed(self, colors: dict):
        self.colors = colors
        ToastManager.instance().set_colors(colors)
        self.log_page.colors = colors
        self.log_page.log_view.clear()
        rows = list(reversed(self.logger.recent(200)))
        self.log_page.load_recent(rows)

        try:
            for key in ("todo", "note", "weather", "docconvert"):
                self.features_page._destroy_detail(key)
        except Exception:
            pass

    # ---------- 启动动画 + 欢迎 ----------
    def _play_startup_anim(self):
        try:
            if self.isMaximized():
                self.setWindowOpacity(0.0)
                self._anim_fade = QPropertyAnimation(self, b"windowOpacity", self)
                self._anim_fade.setDuration(220)
                self._anim_fade.setStartValue(0.0)
                self._anim_fade.setEndValue(1.0)
                self._anim_fade.setEasingCurve(QEasingCurve.OutCubic)
                self._anim_fade.start(QAbstractAnimation.DeleteWhenStopped)
                return

            end_geo = self.geometry()
            w, h = end_geo.width(), end_geo.height()
            cx, cy = end_geo.center().x(), end_geo.center().y()
            sw, sh = int(w * 0.95), int(h * 0.95)
            start_geo = QRect(cx - sw // 2, cy - sh // 2, sw, sh)

            self.setWindowOpacity(0.0)

            self._anim_fade = QPropertyAnimation(self, b"windowOpacity", self)
            self._anim_fade.setDuration(220)
            self._anim_fade.setStartValue(0.0)
            self._anim_fade.setEndValue(1.0)
            self._anim_fade.setEasingCurve(QEasingCurve.OutCubic)

            self._anim_geo = QPropertyAnimation(self, b"geometry", self)
            self._anim_geo.setDuration(220)
            self._anim_geo.setStartValue(start_geo)
            self._anim_geo.setEndValue(end_geo)
            self._anim_geo.setEasingCurve(QEasingCurve.OutCubic)

            self._anim_fade.start(QAbstractAnimation.DeleteWhenStopped)
            self._anim_geo.start(QAbstractAnimation.DeleteWhenStopped)
        except Exception as e:
            print(f"[startup_anim] 失败: {e}")

    def _show_welcome(self):
        try:
            from welcome import build_welcome, should_show_welcome, mark_welcome_shown
            if not should_show_welcome():
                return
            title, body = build_welcome(self)
            pos = load_config().get("notify_position", "bottom-right")
            show_toast(
                title, body,
                duration=5000,
                colors=self.colors,
                position=pos,
                big=True,
            )
            mark_welcome_shown()
        except Exception as e:
            print(f"[welcome] 失败: {e}")

    def startup_post(self):
        self._play_startup_anim()
        QTimer.singleShot(500, self._show_welcome)

    # ---------- 倒计时到点 ----------
    def _on_timer_done(self, task):
        cfg = load_config()
        pos = cfg.get("notify_position", "bottom-right")
        colors = self.colors
        label = task.label

        snooze_min = max(1, int(cfg.get("snooze_minutes", 5)))
        snooze_sec = snooze_min * 60

        def _on_action(key: str):
            if key == "snooze":
                self.scheduler.add_timer(snooze_sec, f"延时提醒：{label}")
                self._append(
                    f"已延后 {snooze_min} 分钟：{label}",
                    level="action", source="提醒",
                )
                self._do_notify(
                    "⏰ 已延后",
                    f"{snooze_min} 分钟后再次提醒：{label}",
                )

        if not cfg.get("notify_screen", True):
            self._do_notify("⏰ 时间到", label)
            self._append(f"倒计时到点：{label}", level="success", source="提醒")
            return

        try:
            show_toast(
                "⏰ 时间到",
                label,
                duration=0,
                colors=colors,
                position=pos,
                buttons=[(f"{snooze_min} 分钟后再提醒", "snooze")],
                on_action=_on_action,
            )
        except Exception as e:
            print(f"[_on_timer_done] 浮窗失败: {e}")
            self._do_notify("⏰ 时间到", label)
            self._append(f"倒计时到点：{label}", level="success", source="提醒")
            return

        play_notify_sound()
        self._append(f"倒计时到点：{label}", level="success", source="提醒")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        top = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText(
            "搜索功能，或直接输入绝对指令（例：倒计时 20 分钟 / 关机 30 分钟）"
        )
        self.cmd_input.returnPressed.connect(self._on_command)
        run_btn = QPushButton("执行")
        run_btn.clicked.connect(self._on_command)

        top.addWidget(self.cmd_input, 1)
        top.addWidget(run_btn)

        self.weather_card = WeatherCard(self)
        top.addWidget(self.weather_card)
        root.addLayout(top)

        body = QHBoxLayout()
        self.nav = QListWidget()
        self.nav.setObjectName("navList")
        self.nav.setFixedWidth(140)
        self.nav.addItems(["首页", "日志记录", "任务", "更新日志", "设置"])
        self.nav.currentRowChanged.connect(self._on_nav)
        self.nav.itemClicked.connect(self._on_nav_item_clicked)
        body.addWidget(self.nav)

        self.stack = QStackedWidget()
        self.stack.setMinimumSize(0, 0)
        self.features_page = FeaturesPage(self.ctx, self.colors)
        self.stack.addWidget(self.features_page)
        self.log_page = LogPage(self, self.colors)
        self.stack.addWidget(self.log_page)
        self.task_panel = TaskPanel(self.scheduler, self.history, self.colors)
        self.stack.addWidget(self.task_panel)
        self.stack.addWidget(ChangelogPage(self))
        self.settings_page = SettingsPage(self, self.theme)
        self.stack.addWidget(self.settings_page)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        self.nav.setCurrentRow(0)
        self._load_log_from_db()

    def _on_nav(self, row: int):
        self.stack.setCurrentIndex(row)
        page = self.stack.currentWidget()

        if page is self.features_page:
            self.features_page.go_home()
            return

        if page:
            fade_in(page, duration=180)

    def _on_nav_item_clicked(self, item):
        row = self.nav.row(item)
        self._on_nav(row)

    def run_command_text(self, text: str):
        self.cmd_input.setText(text)
        self.cmd_input.setFocus()
        self._on_command()

    def _on_command(self):
        text = self.cmd_input.text().strip()
        if not text:
            return
        self.cmd_input.clear()

        # 内部日志信号，不当作命令
        if text.startswith("__log__"):
            msg = text[len("__log__"):].strip()
            self._append(msg, level="success", source="功能页")
            return

        # 内部通知信号：屏幕浮窗 + 系统通知 + 声音
        if text.startswith("__notify__"):
            payload = text[len("__notify__"):].strip()
            if "|" in payload:
                title, msg = payload.split("|", 1)
            else:
                title, msg = "MyToolbox", payload
            self._do_notify(title.strip(), msg.strip())
            return

        cmd, m = self.registry.match(text)
        if not cmd:
            self._append(f"> {text}\n未识别的命令，输入 /help 查看帮助",
                         level="warn", source="命令")
            self._do_notify("❓ 未识别的命令", f"「{text}」不是有效命令")
            return

        try:
            result = cmd.handler(m)
        except Exception as e:
            self._append(f"> {text}\n❌ 执行失败：{e}", level="error", source="命令")
            self._do_notify("❌ 执行失败", str(e))
            return

        notify_title, notify_msg = None, None
        if isinstance(result, tuple):
            if len(result) == 2:
                output, notify_msg = result
                notify_title = "MyToolbox"
            elif len(result) >= 3:
                output, notify_msg, notify_title = result[0], result[1], result[2]
            else:
                output = str(result)
        else:
            output = str(result)

        self._append(f"> {text}\n{output}", level="success", source="命令")
        if notify_msg:
            self._do_notify(notify_title or "MyToolbox", notify_msg)

    @staticmethod
    def _escape(s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace("\n", "<br>"))

    def _append(self, text: str, level: str = "info", source: str = "命令"):
        if not hasattr(self, "log_page"):
            return
        ts = self.logger.log(text, level=level, source=source)
        c = self.colors
        color = {
            "info": c["text"],
            "success": c["success"],
            "warn": c["warn"],
            "error": c["error"],
            "action": c["action"],
        }.get(level, c["text"])
        html = (
            f'<div style="margin:2px 0;">'
            f'<span style="color:{c["text_hint"]};">[{ts}]</span> '
            f'<span style="color:{c["text_dim"]};">({source})</span> '
            f'<span style="color:{color};">{self._escape(text)}</span>'
            f'</div>'
        )
        self.log_page.append_html(html)

    def _load_log_from_db(self):
        rows = list(reversed(self.logger.recent(200)))
        self.log_page.load_recent(rows)

    def _register_commands(self):
        reg = self.registry

        @reg.register(
            "timer",
            r"^(?:倒计时|定时)\s*(\d+)\s*(秒|分钟|分|小时|时|s|min|h)$",
            "设置倒计时", "倒计时 30 分钟",
        )
        def _timer(m):
            n, unit = int(m.group(1)), m.group(2)
            self.scheduler.add_timer(n * UNIT[unit], f"{n}{unit}倒计时")
            msg = f"已设置：{n}{unit} 后提醒"
            return f"✅ {msg}", f"⏰ {msg}"

        @reg.register(
            "shutdown",
            r"^(?:定时关机|关机)\s*(\d+)\s*(秒|分钟|分|小时|时|s|min|h)$",
            "设置定时关机", "关机 30 分钟",
        )
        def _shutdown(m):
            n, unit = int(m.group(1)), m.group(2)
            self.scheduler.add_shutdown(n * UNIT[unit])
            msg = f"将在 {n}{unit} 后自动关机"
            return f"✅ {msg}（可在任务面板取消）", f"🔌 {msg}"

        @reg.register(
            "cancel_shutdown",
            r"^(?:取消关机|cancel\s*shutdown)$",
            "取消所有关机任务", "取消关机",
        )
        def _cancel_shutdown(m):
            n = 0
            for t in self.scheduler.list_tasks():
                if t.kind == "shutdown":
                    self.scheduler.cancel(t.id)
                    n += 1
            msg = f"已取消 {n} 个关机任务" if n else "当前没有关机任务"
            return f"✅ {msg}", f"✅ {msg}"

        @reg.register("lock", r"^(?:锁屏|lock)$", "锁定屏幕", "锁屏")
        def _lock(m):
            schedule_lock(self, source="命令")
            cfg = load_config()
            delay_ms = max(0, int(cfg.get("lock_delay_ms", 3000)))
            secs = delay_ms / 1000.0
            if delay_ms < 1000:
                return "✅ 即将锁屏"
            return f"✅ {secs:g} 秒后锁屏"

        @reg.register(
            "open", r"^(?:打开|open)\s+(.+)$", "打开程序或网址", "打开 notepad",
        )
        def _open(m):
            target = m.group(1).strip()
            if "://" in target:
                webbrowser.open(target)
            else:
                subprocess.Popen(target, shell=True)
            return f"✅ 已尝试打开：{target}", f"🚀 已打开：{target}"

        @reg.register(
            "weather", r"^(?:天气|weather)\s+(\S+)$", "切换天气城市", "天气 上海",
        )
        def _weather(m):
            city = m.group(1)
            self.weather_card.set_city(city)
            return f"✅ 天气城市已切换为：{city}", f"🌤️ 天气城市已切换：{city}"

        @reg.register(
            "weather_auto",
            r"^(?:自动定位|定位天气|weather\s*auto)$",
            "重新自动定位天气", "自动定位",
        )
        def _weather_auto(m):
            self.weather_card.reset_auto()
            return "✅ 已切换为自动定位，正在重新获取…", "📍 已切换为自动定位"

        @reg.register("help", r"^(?:/help|帮助|\?)$", "显示帮助", "/help")
        def _help(m):
            return self.registry.help_text()

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray.setIcon(icon)
        self.setWindowIcon(icon)

        menu = QMenu()
        menu.addAction("显示主界面", self._show_window)
        menu.addAction("日志记录", lambda: (self._show_window(), self.nav.setCurrentRow(1)))
        menu.addAction("任务面板", lambda: (self._show_window(), self.nav.setCurrentRow(2)))
        menu.addAction("更新日志", lambda: (self._show_window(), self.nav.setCurrentRow(3)))
        menu.addSeparator()
        menu.addAction("退出", self._quit)
        self.tray.setContextMenu(menu)

        self.tray.activated.connect(
            lambda r: self._show_window() if r == QSystemTrayIcon.DoubleClick else None
        )
        self.tray.show()

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self):
        tasks = []
        try:
            tasks = self.scheduler.list_tasks()
        except Exception:
            pass

        if tasks:
            lines = []
            for t in tasks[:5]:
                icon = "⏰" if t.kind == "timer" else "🔌"
                lines.append(f"  {icon} {t.label}")
            more = f"\n  …等 {len(tasks)} 个" if len(tasks) > 5 else ""
            text = "退出后这些任务将失效：\n\n" + "\n".join(lines) + more

            box = QMessageBox(self)
            box.setWindowTitle("确认退出")
            box.setIcon(QMessageBox.Warning)
            box.setText(f"还有 {len(tasks)} 个任务在进行中")
            box.setInformativeText(text)
            yes_btn = box.addButton("仍要退出", QMessageBox.DestructiveRole)
            cancel_btn = box.addButton("取消", QMessageBox.RejectRole)
            box.setDefaultButton(cancel_btn)
            box.exec()
            if box.clickedButton() is not yes_btn:
                return

        try:
            for t in tasks:
                self.history.add(t.kind, t.label, "aborted")
        except Exception:
            pass

        self._save_geometry()

        try:
            self.scheduler.shutdown()
        except Exception:
            pass

        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, e):
        e.ignore()
        self.hide()
        self._do_notify("MyToolbox", "已最小化到托盘，双击图标恢复")

    def _do_notify(self, title: str, msg: str):
        cfg = load_config()
        system_on = cfg.get("notify_system", True)
        screen_on = cfg.get("notify_screen", True)

        if system_on:
            try:
                send_notify(title, msg, self.tray)
            except Exception as e:
                print(f"[_do_notify] 系统通知失败: {e}")

        if screen_on:
            try:
                pos = cfg.get("notify_position", "bottom-right")
                show_toast(title, msg, duration=3000,
                           colors=self.colors, position=pos)
            except Exception as e:
                print(f"[_do_notify] 屏幕通知失败: {e}")

        play_notify_sound()