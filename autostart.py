import sys
from pathlib import Path

from app_paths import is_frozen


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "MyToolbox"


def _get_exe_path() -> str:
    if is_frozen():
        return f'"{Path(sys.executable)}"'
    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe")
    script = Path(__file__).parent / "main.py"
    exe = pyw if pyw.exists() else py
    return f'"{exe}" "{script}"'


def is_enabled() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def enable() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_exe_path())
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def disable() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_enabled(on: bool) -> bool:
    return enable() if on else disable()