import winsound
from pathlib import Path

from app_paths import load_config, resource_path


# 预设名 → 内置文件（相对项目根，要带 res/）
PRESETS = {
    "default": "res/sounds/default.wav",
    "notify":  "res/sounds/notify.wav",
    "alert":   "res/sounds/alert.wav",
}


def _resolve_path() -> Path | None:
    """根据配置决定播哪个文件，返回 None 表示静音"""
    cfg = load_config()
    if not cfg.get("notify_sound", True):
        return None

    preset = cfg.get("notify_sound_preset", "default")
    if preset == "custom":
        f = cfg.get("notify_sound_file", "")
        if f:
            p = Path(f)
            if p.exists():
                return p
        # 自定义文件无效 → 退回默认
        preset = "default"

    rel = PRESETS.get(preset)
    if not rel:
        return None
    p = resource_path(rel)
    return p if p.exists() else None


def play_notify():
    """播一次通知音。静音或文件不存在时静默返回。"""
    path = _resolve_path()
    if path is None:
        return
    try:
        winsound.PlaySound(
            str(path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except Exception as e:
        print(f"[sound] 播放失败: {e}")


def play_file(path: str):
    """设置页试听用：直接播指定文件"""
    try:
        winsound.PlaySound(
            str(path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except Exception as e:
        print(f"[sound] 试听失败: {e}")