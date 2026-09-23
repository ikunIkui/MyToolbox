from app_paths import load_config

try:
    from winotify import Notification, audio
    HAS_WINOTIFY = True
except Exception:
    HAS_WINOTIFY = False


def notify(title: str, msg: str, tray=None, silent: bool = False):
    """
    系统通知（Windows 操作中心）。
    silent=True 时不播声音（由 sound.py 统一播）
    """
    if HAS_WINOTIFY:
        try:
            n = Notification(app_id="MyToolbox", title=title, msg=msg)
            if silent:
                try:
                    n.set_audio(audio.Silent, loop=False)
                except Exception:
                    # 旧版没 Silent，忽略
                    pass
            n.show()
            return
        except Exception as e:
            print(f"[notifier] winotify 失败: {e}")

    if tray is not None:
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            tray.showMessage(title, msg, QSystemTrayIcon.Information, 5000)
        except Exception as e:
            print(f"[notifier] 托盘通知失败: {e}")