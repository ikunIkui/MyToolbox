import sys

from PySide6.QtCore import QObject, Signal

from app_paths import load_config, save_config, resource_path


DARK = {
    "bg":            "#1e2128",
    "bg_alt":        "#232734",
    "bg_card":       "#2b2f3a",
    "bg_card_hover": "#333846",
    "bg_hint":       "#232734",
    "border":        "#3a3f4b",
    "border_hover":  "#5a6bff",
    "text":          "#e8eaed",
    "text_dim":      "#9aa2b1",
    "text_hint":     "#7d8493",
    "accent":        "#4a6bff",
    "accent_hover":  "#5f7cff",
    "accent_press":  "#3b57d6",
    "success":       "#7ed08a",
    "warn":          "#e6c46a",
    "error":         "#e07a7a",
    "action":        "#7aa2ff",
    "shadow":        "#5a6bff",
}

LIGHT = {
    "bg":            "#f4f5f7",
    "bg_alt":        "#ffffff",
    "bg_card":       "#ffffff",
    "bg_card_hover": "#eef1ff",
    "bg_hint":       "#eef0f4",
    "border":        "#d8dce3",
    "border_hover":  "#4a6bff",
    "text":          "#1e2128",
    "text_dim":      "#5a6270",
    "text_hint":     "#8a92a3",
    "accent":        "#3b57d6",
    "accent_hover":  "#4a6bff",
    "accent_press":  "#2d44b8",
    "success":       "#2e9e4a",
    "warn":          "#b8860b",
    "error":         "#c0392b",
    "action":        "#3b57d6",
    "shadow":        "#4a6bff",
}


def detect_system_theme() -> str:
    if sys.platform != "win32":
        return "dark"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if val == 1 else "dark"
    except Exception:
        return "dark"


class ThemeManager(QObject):
    changed = Signal(dict)

    def __init__(self):
        super().__init__()
        cfg = load_config()
        self._mode = cfg.get("theme", "auto")
        self._colors = self._resolve()

    def _resolve(self) -> dict:
        if self._mode == "dark":
            return DARK
        if self._mode == "light":
            return LIGHT
        return DARK if detect_system_theme() == "dark" else LIGHT

    @property
    def colors(self) -> dict:
        return self._colors

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str):
        if mode not in ("auto", "dark", "light"):
            return
        self._mode = mode
        cfg = load_config()
        cfg["theme"] = mode
        save_config(cfg)
        self._colors = self._resolve()
        self.changed.emit(self._colors)

    def apply(self, app):
        app.setStyleSheet(build_qss(self._colors))


def build_qss(c: dict) -> str:
    check_icon_path = resource_path("res/check.svg").as_posix()

    return f"""
    QWidget {{
        background: {c['bg']};
        color: {c['text']};
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        font-size: 13px;
    }}
    QMainWindow {{ background: {c['bg']}; }}

    /* === 功能宫格卡片 === */
    QFrame#featureCard {{
        background: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 10px;
    }}
    QFrame#featureCard:hover {{
        background: {c['bg_card_hover']};
        border: 1px solid {c['border_hover']};
    }}

    QListWidget#navList {{
        background: {c['bg_alt']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 4px;
        outline: none;
    }}
    QListWidget#navList::item {{
        padding: 8px 10px;
        border-radius: 6px;
    }}
    QListWidget#navList::item:hover {{
        background: {c['bg_card_hover']};
    }}
    QListWidget#navList::item:selected {{
        background: {c['accent']};
        color: white;
    }}

    QListWidget {{
        background: {c['bg_alt']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 4px;
    }}
    QListWidget::item {{ padding: 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background: {c['accent']}; color: white; }}
    QListWidget::item:hover {{ background: {c['bg_card_hover']}; }}

    QLineEdit, QPlainTextEdit, QTextEdit {{
        background: {c['bg_alt']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        color: {c['text']};
        padding: 6px 8px;
        selection-background-color: {c['accent']};
        selection-color: white;
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border: 1px solid {c['accent']};
    }}

    QPushButton {{
        background: {c['bg_alt']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 14px;
        min-height: 22px;
    }}
    QPushButton:hover {{
        background: {c['bg_card_hover']};
        border: 1px solid {c['border_hover']};
    }}
    QPushButton:pressed {{
        background: {c['border']};
    }}
    QPushButton:disabled {{
        background: {c['bg']};
        color: {c['text_dim']};
    }}

    QComboBox {{
        background: {c['bg_alt']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        color: {c['text']};
        padding: 4px 8px;
        min-height: 24px;
    }}
    QComboBox:hover {{ border: 1px solid {c['border_hover']}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c['text_dim']};
        width: 0;
        height: 0;
        margin-right: 6px;
    }}
    QComboBox QAbstractItemView {{
        background: {c['bg_alt']};
        color: {c['text']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent']};
        selection-color: white;
        outline: none;
    }}

    QSpinBox {{
        background: {c['bg_alt']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        color: {c['text']};
        padding: 4px 8px;
        padding-right: 22px;
        min-height: 24px;
    }}
    QSpinBox:focus {{ border: 1px solid {c['accent']}; }}
    QSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        height: 14px;
        background: {c['bg_card']};
        border-left: 1px solid {c['border']};
        border-top-right-radius: 6px;
    }}
    QSpinBox::up-button:hover {{ background: {c['bg_card_hover']}; }}
    QSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        height: 14px;
        background: {c['bg_card']};
        border-left: 1px solid {c['border']};
        border-bottom-right-radius: 6px;
    }}
    QSpinBox::down-button:hover {{ background: {c['bg_card_hover']}; }}
    QSpinBox::up-arrow {{
        image: none;
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-bottom: 4px solid {c['text_dim']};
        width: 0;
        height: 0;
    }}
    QSpinBox::down-arrow {{
        image: none;
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-top: 4px solid {c['text_dim']};
        width: 0;
        height: 0;
    }}

    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {c['border']};
        border-radius: 4px;
        background: {c['bg_alt']};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {c['accent']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border: 1px solid {c['accent']};
        image: url("{check_icon_path}");
    }}
    QCheckBox::indicator:disabled {{
        background: {c['bg_alt']};
        border: 1px solid {c['border']};
    }}

    QGroupBox {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 14px;
        padding: 12px 10px 10px 10px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
        left: 10px;
        color: {c['text_dim']};
    }}

    QScrollBar:vertical {{
        background: transparent; width: 10px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']}; border-radius: 5px; min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {c['text_dim']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; }}
    QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 5px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    QMenu {{
        background: {c['bg_alt']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {c['accent']}; color: white; }}

    QMessageBox, QDialog {{
        background: {c['bg']};
        color: {c['text']};
    }}
    QMessageBox QLabel {{ color: {c['text']}; }}
    QMessageBox QPushButton, QDialog QPushButton {{ min-width: 70px; }}

    QToolTip {{
        background: {c['bg_alt']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 4px 8px;
    }}

    QSplitter::handle {{ background: {c['border']}; width: 1px; height: 1px; }}

    QLabel {{ background: transparent; }}
    """