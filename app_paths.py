import json
import os
import sys
from pathlib import Path

APP_NAME = "MyToolbox"


def get_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> Path:
    return get_data_dir() / "data.db"


def get_config_path() -> Path:
    return get_data_dir() / "config.json"


def resource_path(rel: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel
    return Path(__file__).parent / rel


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


_DEFAULT_CONFIG = {
    "weather_city": "",
    "weather_cache": None,
    "theme": "auto",
    "notify_sound": True,
    "notify_sound_preset": "default",
    "notify_sound_file": "",
    "notify_system": True,
    "notify_screen": True,
    "notify_position": "bottom-right",
    "snooze_minutes": 5,
    "autostart": False,
    "lock_delay_ms": 3000,
    "global_hotkey": "Alt+Space",
    "log_limit": 500,
    "note_smart_category": True,
    "note_smart_reminder": True,
    # 窗口几何 & 欢迎
    "window_geometry": "",           # "x,y,w,h"
    "window_maximized": False,
    "last_welcome_date": "",         # "YYYY-MM-DD"
}


def load_config() -> dict:
    p = get_config_path()
    if not p.exists():
        return dict(_DEFAULT_CONFIG)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        cfg = dict(_DEFAULT_CONFIG)
        cfg.update(data or {})
        return cfg
    except Exception:
        return dict(_DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    try:
        get_config_path().write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass