import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QCheckBox, QSpinBox, QGroupBox, QMessageBox,
    QApplication, QScrollArea, QFrame, QFileDialog,
)

from app_paths import load_config, save_config, get_data_dir
import autostart


class SettingsPage(QWidget):
    def __init__(self, win, theme, parent=None):
        super().__init__(parent)
        self.win = win
        self.theme = theme

        self._build_ui()
        self._load_config()

    # ---------- UI ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        title = QLabel("设置")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        root.addWidget(title)

        # ===== 外观 =====
        g1 = QGroupBox("外观")
        g1v = QVBoxLayout(g1)

        row = QHBoxLayout()
        row.addWidget(QLabel("主题："))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["跟随系统", "深色", "浅色"])
        self.theme_combo.setFixedWidth(160)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        row.addWidget(self.theme_combo)
        row.addStretch()
        g1v.addLayout(row)
        root.addWidget(g1)

        # ===== 天气 =====
        g2 = QGroupBox("天气")
        g2v = QVBoxLayout(g2)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("城市："))
        self.city_edit = QLineEdit()
        self.city_edit.setPlaceholderText("留空则自动定位")
        row2.addWidget(self.city_edit, 1)

        set_btn = QPushButton("保存")
        set_btn.setFixedWidth(70)
        set_btn.clicked.connect(self._on_save_city)
        row2.addWidget(set_btn)

        auto_btn = QPushButton("自动定位")
        auto_btn.setFixedWidth(90)
        auto_btn.clicked.connect(self._on_auto_city)
        row2.addWidget(auto_btn)
        g2v.addLayout(row2)
        root.addWidget(g2)

        # ===== 通知 =====
        g3 = QGroupBox("通知")
        g3v = QVBoxLayout(g3)

        self.sound_check = QCheckBox("通知声音")
        self.sound_check.stateChanged.connect(self._on_sound_changed)
        g3v.addWidget(self.sound_check)

        # 音效选择行
        row_sound = QHBoxLayout()
        row_sound.addWidget(QLabel("音效："))
        self.sound_combo = QComboBox()
        self.sound_combo.addItems(["默认", "提示", "警告", "自定义…"])
        self.sound_combo.setFixedWidth(120)
        self.sound_combo.currentTextChanged.connect(self._on_sound_preset_changed)
        row_sound.addWidget(self.sound_combo)

        self.sound_test_btn = QPushButton("▶ 试听")
        self.sound_test_btn.setFixedWidth(70)
        self.sound_test_btn.clicked.connect(self._test_sound)
        row_sound.addWidget(self.sound_test_btn)

        self.sound_browse_btn = QPushButton("浏览…")
        self.sound_browse_btn.setFixedWidth(70)
        self.sound_browse_btn.clicked.connect(self._browse_sound)
        self.sound_browse_btn.setVisible(False)
        row_sound.addWidget(self.sound_browse_btn)

        self.sound_path_label = QLabel("")
        self.sound_path_label.setStyleSheet("font-size: 11px; color: #9aa2b1;")
        self.sound_path_label.setVisible(False)
        row_sound.addWidget(self.sound_path_label, 1)

        row_sound.addStretch()
        g3v.addLayout(row_sound)

        self.sys_check = QCheckBox("系统通知（Windows 操作中心）")
        self.sys_check.stateChanged.connect(self._on_sys_changed)
        g3v.addWidget(self.sys_check)

        self.screen_check = QCheckBox("屏幕浮窗通知")
        self.screen_check.stateChanged.connect(self._on_screen_changed)
        g3v.addWidget(self.screen_check)

        row_pos = QHBoxLayout()
        row_pos.addWidget(QLabel("浮窗位置："))
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["右下", "左下", "右上", "左上"])
        self.pos_combo.setFixedWidth(120)
        self.pos_combo.currentTextChanged.connect(self._on_position_changed)
        row_pos.addWidget(self.pos_combo)
        row_pos.addStretch()
        g3v.addLayout(row_pos)

        row_snooze = QHBoxLayout()
        row_snooze.addWidget(QLabel("延长时间："))
        self.snooze_combo = QComboBox()
        self.snooze_combo.addItems(["5 分钟", "10 分钟", "15 分钟", "30 分钟"])
        self.snooze_combo.setFixedWidth(120)
        self.snooze_combo.currentTextChanged.connect(self._on_snooze_changed)
        row_snooze.addWidget(self.snooze_combo)
        row_snooze.addStretch()
        g3v.addLayout(row_snooze)

        row_test = QHBoxLayout()
        test_toast_btn = QPushButton("测试浮窗位置")
        test_toast_btn.setFixedWidth(140)
        test_toast_btn.clicked.connect(self._test_toast)
        test_sys_btn = QPushButton("测试系统通知")
        test_sys_btn.setFixedWidth(140)
        test_sys_btn.clicked.connect(self._test_system)
        row_test.addWidget(test_toast_btn)
        row_test.addWidget(test_sys_btn)
        row_test.addStretch()
        g3v.addLayout(row_test)

        root.addWidget(g3)

        # ===== 系统 =====
        g4 = QGroupBox("系统")
        g4v = QVBoxLayout(g4)

        self.autostart_check = QCheckBox("开机自动启动")
        self.autostart_check.stateChanged.connect(self._on_autostart_changed)
        g4v.addWidget(self.autostart_check)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("锁屏延迟："))
        self.lock_spin = QSpinBox()
        self.lock_spin.setRange(1, 30)
        self.lock_spin.setSuffix(" 秒")
        self.lock_spin.setFixedWidth(120)
        self.lock_spin.valueChanged.connect(self._on_lock_delay_changed)
        row4.addWidget(self.lock_spin)
        row4.addStretch()
        g4v.addLayout(row4)

        root.addWidget(g4)

        # ===== 数据 =====
        g5 = QGroupBox("数据")
        g5v = QVBoxLayout(g5)

        row5 = QHBoxLayout()
        row5.addWidget(QLabel("数据目录："))
        self.data_path_label = QLabel(str(get_data_dir()))
        self.data_path_label.setStyleSheet("font-size: 12px;")
        self.data_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row5.addWidget(self.data_path_label, 1)

        open_btn = QPushButton("打开")
        open_btn.setFixedWidth(70)
        open_btn.clicked.connect(self._open_data_dir)
        row5.addWidget(open_btn)
        g5v.addLayout(row5)

        row6 = QHBoxLayout()
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self._clear_logs)
        clear_note_btn = QPushButton("清空笔记")
        clear_note_btn.clicked.connect(self._clear_notes)
        clear_task_btn = QPushButton("清空任务历史")
        clear_task_btn.clicked.connect(self._clear_task_history)
        row6.addWidget(clear_log_btn)
        row6.addWidget(clear_note_btn)
        row6.addWidget(clear_task_btn)
        row6.addStretch()
        g5v.addLayout(row6)

        root.addWidget(g5)

        # ===== 关于 =====
        g6 = QGroupBox("关于")
        g6v = QVBoxLayout(g6)
        about = QLabel("MyToolbox v0.5.0\n个人效率工具台\n-制作者：涛涛\n特别鸣谢：\n名单暂未上传")
        about.setStyleSheet("font-size: 12px;")
        g6v.addWidget(about)
        root.addWidget(g6)

        root.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    # ---------- 加载配置 ----------
    def _load_config(self):
        cfg = load_config()

        mode_map = {"auto": "跟随系统", "dark": "深色", "light": "浅色"}
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText(
            mode_map.get(cfg.get("theme", "auto"), "跟随系统")
        )
        self.theme_combo.blockSignals(False)

        self.city_edit.setText(cfg.get("weather_city", ""))

        self.sound_check.blockSignals(True)
        self.sound_check.setChecked(bool(cfg.get("notify_sound", True)))
        self.sound_check.blockSignals(False)

        # 音效预设
        preset_map_rev = {
            "default": "默认",
            "notify": "提示",
            "alert": "闹铃",
            "custom": "自定义…",
        }
        preset = cfg.get("notify_sound_preset", "default")
        self.sound_combo.blockSignals(True)
        self.sound_combo.setCurrentText(preset_map_rev.get(preset, "默认"))
        self.sound_combo.blockSignals(False)

        self.sound_browse_btn.setVisible(preset == "custom")
        self._refresh_sound_path_label(cfg)

        self.sys_check.blockSignals(True)
        self.sys_check.setChecked(bool(cfg.get("notify_system", True)))
        self.sys_check.blockSignals(False)

        self.screen_check.blockSignals(True)
        self.screen_check.setChecked(bool(cfg.get("notify_screen", True)))
        self.screen_check.blockSignals(False)

        pos_map = {
            "bottom-right": "右下",
            "bottom-left": "左下",
            "top-right": "右上",
            "top-left": "左上",
        }
        self.pos_combo.blockSignals(True)
        self.pos_combo.setCurrentText(
            pos_map.get(cfg.get("notify_position", "bottom-right"), "右下")
        )
        self.pos_combo.blockSignals(False)

        snooze_map = {5: "5 分钟", 10: "10 分钟", 15: "15 分钟", 30: "30 分钟"}
        self.snooze_combo.blockSignals(True)
        self.snooze_combo.setCurrentText(
            snooze_map.get(int(cfg.get("snooze_minutes", 5)), "5 分钟")
        )
        self.snooze_combo.blockSignals(False)

        self.autostart_check.blockSignals(True)
        try:
            self.autostart_check.setChecked(autostart.is_enabled())
        except Exception:
            self.autostart_check.setChecked(False)
        self.autostart_check.blockSignals(False)

        self.lock_spin.blockSignals(True)
        self.lock_spin.setValue(max(1, int(cfg.get("lock_delay_ms", 3000)) // 1000))
        self.lock_spin.blockSignals(False)

    def _refresh_sound_path_label(self, cfg: dict):
        """显示自定义音效文件名"""
        if cfg.get("notify_sound_preset") == "custom":
            f = cfg.get("notify_sound_file", "")
            if f:
                import os as _os
                self.sound_path_label.setText(_os.path.basename(f))
                self.sound_path_label.setToolTip(f)
                self.sound_path_label.setVisible(True)
                return
        self.sound_path_label.setVisible(False)

    # ---------- 统一确认弹窗 ----------
    def _confirm_clear(self, what: str) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle("确认清空")
        box.setIcon(QMessageBox.Warning)
        box.setText(f"确定要清空{what}吗？")
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
            return False

        return clicked is yes_btn

    # ---------- 事件 ----------
    def _on_theme_changed(self, text: str):
        mode_map = {"跟随系统": "auto", "深色": "dark", "浅色": "light"}
        mode = mode_map.get(text, "auto")
        try:
            self.theme.set_mode(mode)
            app = QApplication.instance()
            if app:
                self.theme.apply(app)
        except Exception as e:
            print(f"[settings] 主题切换失败: {e}")

    def _on_save_city(self):
        city = self.city_edit.text().strip()
        cfg = load_config()
        cfg["weather_city"] = city
        cfg["weather_cache"] = None
        save_config(cfg)
        try:
            if city:
                self.win.weather_card.set_city(city)
            else:
                self.win.weather_card.reset_auto()
        except Exception:
            pass
        self.win._append(
            f"天气城市已设为：{city or '自动定位'}",
            level="success", source="设置",
        )

    def _on_auto_city(self):
        self.city_edit.clear()
        cfg = load_config()
        cfg["weather_city"] = ""
        cfg["weather_cache"] = None
        save_config(cfg)
        try:
            self.win.weather_card.reset_auto()
        except Exception:
            pass
        self.win._append("天气已切换为自动定位",
                         level="success", source="设置")

    def _on_sound_changed(self, state):
        cfg = load_config()
        cfg["notify_sound"] = bool(state)
        save_config(cfg)

    def _on_sound_preset_changed(self, text: str):
        preset_map = {
            "默认": "default",
            "提示": "notify",
            "闹铃": "alert",
            "自定义…": "custom",
        }
        preset = preset_map.get(text, "default")
        cfg = load_config()
        cfg["notify_sound_preset"] = preset
        save_config(cfg)

        self.sound_browse_btn.setVisible(preset == "custom")
        self._refresh_sound_path_label(cfg)

        # 选自定义但还没选文件 → 自动弹浏览框
        if preset == "custom" and not cfg.get("notify_sound_file"):
            self._browse_sound()

    def _test_sound(self):
        try:
            from sound import play_notify
            play_notify()
        except Exception as e:
            QMessageBox.warning(self, "试听失败", str(e))

    def _browse_sound(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择音效文件", "", "音频 (*.wav)"
        )
        if not path:
            # 用户取消 → 如果还是 custom 但没文件，退回默认
            cfg = load_config()
            if not cfg.get("notify_sound_file"):
                cfg["notify_sound_preset"] = "default"
                save_config(cfg)
                self.sound_combo.blockSignals(True)
                self.sound_combo.setCurrentText("默认")
                self.sound_combo.blockSignals(False)
                self.sound_browse_btn.setVisible(False)
                self._refresh_sound_path_label(cfg)
            return

        cfg = load_config()
        cfg["notify_sound_preset"] = "custom"
        cfg["notify_sound_file"] = path
        save_config(cfg)
        self._refresh_sound_path_label(cfg)

        # 试听
        try:
            from sound import play_file
            play_file(path)
        except Exception:
            pass

    def _on_sys_changed(self, state):
        cfg = load_config()
        cfg["notify_system"] = bool(state)
        save_config(cfg)

    def _on_screen_changed(self, state):
        cfg = load_config()
        cfg["notify_screen"] = bool(state)
        save_config(cfg)

    def _on_position_changed(self, text):
        pos_map = {
            "右下": "bottom-right",
            "左下": "bottom-left",
            "右上": "top-right",
            "左上": "top-left",
        }
        pos = pos_map.get(text, "bottom-right")
        cfg = load_config()
        cfg["notify_position"] = pos
        save_config(cfg)
        try:
            from screen_notify import ToastManager
            ToastManager.instance().set_position(pos)
        except Exception:
            pass

        self._test_toast()

    def _on_snooze_changed(self, text: str):
        m = int(text.split()[0])
        cfg = load_config()
        cfg["snooze_minutes"] = m
        save_config(cfg)

    def _on_autostart_changed(self, state):
        on = bool(state)
        ok = autostart.set_enabled(on)
        if ok:
            cfg = load_config()
            cfg["autostart"] = on
            save_config(cfg)
            self.win._append(
                f"开机自启已{'开启' if on else '关闭'}",
                level="success", source="设置",
            )
        else:
            QMessageBox.warning(self, "失败", "开机自启设置失败，请检查权限")
            self.autostart_check.blockSignals(True)
            self.autostart_check.setChecked(not on)
            self.autostart_check.blockSignals(False)

    def _on_lock_delay_changed(self, val: int):
        cfg = load_config()
        cfg["lock_delay_ms"] = val * 1000
        save_config(cfg)

    # ---------- 测试 ----------
    def _test_toast(self):
        try:
            from screen_notify import show_toast
            pos = load_config().get("notify_position", "bottom-right")
            colors = self.theme.colors if self.theme else None
            show_toast(
                "🔔 测试通知",
                f"当前位置：{self.pos_combo.currentText()}",
                duration=3000,
                colors=colors,
                position=pos,
            )
        except Exception as e:
            QMessageBox.warning(self, "测试失败", str(e))

    def _test_system(self):
        try:
            from notifier import notify as send_notify
            send_notify(
                "🔔 测试系统通知",
                "这是一条来自 MyToolbox 的测试通知",
                None,
            )
        except Exception as e:
            QMessageBox.warning(self, "测试失败", str(e))

    # ---------- 数据 ----------
    def _open_data_dir(self):
        path = str(get_data_dir())
        try:
            os.startfile(path)
        except Exception:
            subprocess.Popen(f'explorer "{path}"', shell=True)

    def _clear_logs(self):
        if not self._confirm_clear("所有操作日志"):
            return
        try:
            self.win.logger.clear()
            if hasattr(self.win, "log_page"):
                self.win.log_page.log_view.clear()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        self.win._append("日志已清空", level="warn", source="设置")

    def _clear_notes(self):
        if not self._confirm_clear("所有笔记"):
            return
        try:
            from note_db import NoteDB
            import sqlite3
            db = NoteDB()
            with sqlite3.connect(db.db_path) as conn:
                conn.execute("DELETE FROM notes")
                conn.execute("DELETE FROM notes_fts")
                conn.commit()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        self.win._append("所有笔记已清空", level="warn", source="设置")

    def _clear_task_history(self):
        if not self._confirm_clear("所有任务历史"):
            return
        try:
            from task_history import TaskHistory
            TaskHistory().clear()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
            return
        self.win._append("任务历史已清空", level="warn", source="设置")
        try:
            if hasattr(self.win, "task_panel"):
                self.win.task_panel.refresh()
        except Exception:
            pass