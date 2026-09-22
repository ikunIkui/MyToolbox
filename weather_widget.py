from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)

from weather import Weather, fetch_weather_auto
from app_paths import load_config, save_config
from anim import fade_in


_FALLBACK = {
    "bg_card": "#2b2f3a",
    "border": "#3a3f4b",
    "text": "#e8eaed",
    "text_dim": "#9aa2b1",
}


class WeatherWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, city_override: str = ""):
        super().__init__()
        self.city_override = city_override

    def run(self):
        try:
            self.done.emit(fetch_weather_auto(self.city_override))
        except Exception as e:
            self.failed.emit(str(e))


class WeatherCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = load_config()
        self._manual_city: str = cfg.get("weather_city", "") or ""
        self._worker: WeatherWorker | None = None

        # 拿主题色
        self.colors = _FALLBACK
        w = self
        while w is not None and not hasattr(w, "colors"):
            w = w.parent() if hasattr(w, "parent") else None
        if w is not None and hasattr(w, "colors"):
            self.colors = w.colors

        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(30 * 60 * 1000)

        self.refresh()

    def _build_ui(self):
        c = self.colors
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(72)
        self.setStyleSheet(f"""
            WeatherCard {{
                background: {c['bg_card']};
                border-radius: 10px;
                border: 1px solid {c['border']};
            }}
            QLabel {{ color: {c['text']}; background: transparent; }}
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(12)

        self.icon_label = QLabel("⏳")
        self.icon_label.setStyleSheet(
            f"font-size: 28px; background: transparent; color: {c['text']};"
        )
        self.icon_label.setFixedWidth(40)
        self.icon_label.setAlignment(Qt.AlignCenter)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.city_label = QLabel("定位中…")
        self.city_label.setStyleSheet(
            f"font-size: 12px; color:{c['text_dim']}; background: transparent;"
        )
        self.temp_label = QLabel("--°C")
        self.temp_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {c['text']}; "
            f"background: transparent;"
        )
        self.desc_label = QLabel("加载中…")
        self.desc_label.setStyleSheet(
            f"font-size: 12px; color:{c['text_dim']}; background: transparent;"
        )

        info.addWidget(self.city_label)
        info.addWidget(self.temp_label)
        info.addWidget(self.desc_label)

        root.addWidget(self.icon_label)
        root.addLayout(info, 1)
        self.setToolTip("天气加载中…")

    # ---------- 对外 ----------
    def set_city(self, city: str):
        self._manual_city = city
        cfg = load_config()
        cfg["weather_city"] = city
        save_config(cfg)
        self.refresh()

    def reset_auto(self):
        self._manual_city = ""
        cfg = load_config()
        cfg["weather_city"] = ""
        cfg["weather_cache"] = None
        save_config(cfg)
        self.city_label.setText("定位中…")
        self.refresh()

    # ---------- 内部 ----------
    def refresh(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = WeatherWorker(self._manual_city)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, w: Weather):
        self.icon_label.setText(w.icon)
        self.temp_label.setText(f"{round(w.temperature)}°C")
        self.desc_label.setText(w.desc)
        self.city_label.setText(w.city + ("（手动）" if self._manual_city else ""))
        self.setToolTip(
            f"{w.city}  {w.desc}\n"
            f"温度：{w.temperature}°C\n"
            f"湿度：{w.humidity}%\n"
            f"风速：{w.wind} km/h"
        )
        fade_in(self.temp_label, duration=300)
        fade_in(self.icon_label, duration=300)
        fade_in(self.desc_label, duration=300)

    def _on_failed(self, err: str):
        self.icon_label.setText("⚠️")
        self.temp_label.setText("--°C")
        self.desc_label.setText("获取失败")
        self.setToolTip(f"天气获取失败：{err}")

    # ---------- 主题变更时刷新颜色 ----------
    def apply_colors(self, colors: dict):
        self.colors = colors
        self._build_ui()