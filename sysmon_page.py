from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QScrollArea, QProgressBar, QGridLayout,
)

from sysmon import (
    SysMonitor, Snapshot, HAS_PSUTIL,
    fmt_speed,
)


# 默认颜色兜底
_FALLBACK = {
    "bg": "#1e2128",
    "bg_card": "#2b2f3a",
    "border": "#3a3f4b",
    "text": "#e8eaed",
    "text_dim": "#9aa2b1",
    "accent": "#4a6bff",
    "success": "#7ed08a",
    "warn": "#e6c46a",
    "error": "#e07a7a",
}


# ==================== 单个卡片 ====================
class MonitorCard(QFrame):
    def __init__(self, title: str, colors: dict, parent=None):
        super().__init__(parent)
        self.colors = colors

        self.setStyleSheet(f"""
            MonitorCard {{
                background: {colors['bg_card']};
                border: 1px solid {colors['border']};
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; }}
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"color: {colors['text_dim']}; font-size: 12px; "
            f"font-weight: bold; background: transparent;"
        )

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet(
            f"color: {colors['text']}; font-size: 22px; "
            f"font-weight: bold; background: transparent;"
        )

        self.sub_label = QLabel("")
        self.sub_label.setStyleSheet(
            f"color: {colors['text_dim']}; font-size: 11px; "
            f"background: transparent;"
        )
        self.sub_label.setWordWrap(True)

        v.addWidget(self.title_label)
        v.addWidget(self.value_label)
        v.addWidget(self.sub_label)

        # 进度条（可选）
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background: {colors['bg']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {colors['accent']};
                border-radius: 3px;
            }}
        """)
        v.addWidget(self.bar)

        # 额外内容区（磁盘多分区、网络累计、GPU 等）
        self.extra_layout = QVBoxLayout()
        self.extra_layout.setSpacing(2)
        v.addLayout(self.extra_layout)

        v.addStretch()

    def set_value(self, value: str, sub: str = ""):
        self.value_label.setText(value)
        self.sub_label.setText(sub)

    def set_bar(self, percent: float, color: str | None = None):
        self.bar.setValue(int(max(0, min(100, percent))))
        if color:
            self.bar.setStyleSheet(f"""
                QProgressBar {{
                    background: {self.colors['bg']};
                    border: none;
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background: {color};
                    border-radius: 3px;
                }}
            """)

    def clear_extra(self):
        while self.extra_layout.count():
            item = self.extra_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def add_extra_line(self, text: str, color: str | None = None,
                       bar_percent: float | None = None):
        c = color or self.colors["text_dim"]

        line = QWidget()
        h = QVBoxLayout(line)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(2)

        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {c}; font-size: 11px; background: transparent;"
        )
        lbl.setWordWrap(True)
        h.addWidget(lbl)

        if bar_percent is not None:
            b = QProgressBar()
            b.setRange(0, 100)
            b.setValue(int(max(0, min(100, bar_percent))))
            b.setTextVisible(False)
            b.setFixedHeight(4)
            b.setStyleSheet(f"""
                QProgressBar {{
                    background: {self.colors['bg']};
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background: {c};
                    border-radius: 2px;
                }}
            """)
            h.addWidget(b)

        self.extra_layout.addWidget(line)


# ==================== 系统信息区 ====================
class SysInfoBox(QFrame):
    def __init__(self, colors: dict, parent=None):
        super().__init__(parent)
        self.colors = colors

        self.setStyleSheet(f"""
            SysInfoBox {{
                background: {colors['bg_card']};
                border: 1px solid {colors['border']};
                border-radius: 10px;
            }}
            QLabel {{ background: transparent; }}
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)

        title = QLabel("系统信息")
        title.setStyleSheet(
            f"color: {colors['text_dim']}; font-size: 12px; "
            f"font-weight: bold; background: transparent;"
        )
        v.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)

        self._labels: dict[str, QLabel] = {}
        rows = [
            ("os", "系统："),
            ("uptime", "开机："),
            ("cpu", "CPU："),
            ("host", "主机："),
        ]
        for i, (key, prefix) in enumerate(rows):
            k = QLabel(prefix)
            k.setStyleSheet(
                f"color: {colors['text_dim']}; font-size: 12px; "
                f"background: transparent;"
            )
            val = QLabel("--")
            val.setStyleSheet(
                f"color: {colors['text']}; font-size: 12px; "
                f"background: transparent;"
            )
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            val.setWordWrap(True)
            grid.addWidget(k, i, 0, Qt.AlignTop)
            grid.addWidget(val, i, 1)
            self._labels[key] = val

        grid.setColumnStretch(1, 1)
        v.addLayout(grid)

    def update_info(self, snap: Snapshot):
        self._labels["os"].setText(snap.sys.os_name or "--")
        self._labels["uptime"].setText(snap.sys.boot_uptime or "--")
        self._labels["cpu"].setText(snap.sys.cpu_model or "--")
        self._labels["host"].setText(snap.sys.host_user or "--")


# ==================== 主页面 ====================
class SysMonPage(QWidget):
    REFRESH_MS = 2000

    def __init__(self, win, colors: dict | None = None, parent=None):
        super().__init__(parent)
        self.win = win
        self.colors = colors or getattr(win, "colors", None) or _FALLBACK
        self.monitor = SysMonitor()
        self._timer: QTimer | None = None
        self._first_show = True

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        c = self.colors

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

        # 标题
        title = QLabel("📊 系统监控")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {c['text']};"
        )
        root.addWidget(title)

        if not HAS_PSUTIL:
            warn = QLabel("⚠️ 未安装 psutil，无法采集数据。请运行：pip install psutil")
            warn.setStyleSheet(f"color: {c['warn']}; font-size: 13px;")
            warn.setWordWrap(True)
            root.addWidget(warn)

        # 卡片网格：CPU / 内存 / 网络 / 磁盘 / GPU
        grid = QGridLayout()
        grid.setSpacing(12)

        self.card_cpu = MonitorCard("CPU", c)
        self.card_mem = MonitorCard("内存", c)
        self.card_net = MonitorCard("网络", c)
        self.card_disk = MonitorCard("磁盘", c)
        self.card_gpu = MonitorCard("GPU", c)

        grid.addWidget(self.card_cpu, 0, 0)
        grid.addWidget(self.card_mem, 0, 1)
        grid.addWidget(self.card_net, 1, 0)
        grid.addWidget(self.card_disk, 1, 1)
        grid.addWidget(self.card_gpu, 2, 0, 1, 2)   # GPU 占整行

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        root.addLayout(grid)

        # 系统信息
        self.sys_box = SysInfoBox(c)
        root.addWidget(self.sys_box)

        # 控制区
        ctrl = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(80)
        self.refresh_btn.clicked.connect(self.refresh_once)

        self.auto_check = QCheckBox("自动刷新 2 秒")
        self.auto_check.setChecked(True)
        self.auto_check.stateChanged.connect(self._on_auto_changed)

        self.ts_label = QLabel("")
        self.ts_label.setStyleSheet(
            f"color: {c['text_dim']}; font-size: 11px;"
        )

        ctrl.addWidget(self.refresh_btn)
        ctrl.addWidget(self.auto_check)
        ctrl.addStretch()
        ctrl.addWidget(self.ts_label)
        root.addLayout(ctrl)

        root.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    # ---------- 数据刷新 ----------
    def refresh_once(self):
        try:
            snap = self.monitor.snapshot()
        except Exception as e:
            print(f"[sysmon] 采集失败: {e}")
            return
        self._apply(snap)

    def _apply(self, snap: Snapshot):
        c = self.colors

        # CPU
        cpu = snap.cpu
        cpu_color = self._color_by_percent(cpu.percent)
        self.card_cpu.set_value(
            f"{cpu.percent:.0f}%",
            f"{cpu.cores} 核  {cpu.freq_mhz:.0f} MHz"
        )
        self.card_cpu.set_bar(cpu.percent, cpu_color)

        # 内存
        mem = snap.mem
        mem_color = self._color_by_percent(mem.percent)
        self.card_mem.set_value(
            f"{mem.percent:.0f}%",
            f"{mem.used_gb:.1f} / {mem.total_gb:.1f} GB"
        )
        self.card_mem.set_bar(mem.percent, mem_color)
        self.card_mem.clear_extra()
        if mem.swap_total_gb > 0:
            self.card_mem.add_extra_line(
                f"虚拟内存：{mem.swap_used_gb:.1f} / {mem.swap_total_gb:.1f} GB"
                f"  ({mem.swap_percent:.0f}%)",
                c["text_dim"],
            )

        # 网络
        net = snap.net
        self.card_net.set_value(
            f"↓ {fmt_speed(net.down_bps)}",
            f"↑ {fmt_speed(net.up_bps)}"
        )
        self.card_net.set_bar(0)
        self.card_net.bar.setVisible(False)
        self.card_net.clear_extra()
        self.card_net.add_extra_line(
            f"累计下载：{net.total_down_gb:.1f} GB", c["text_dim"]
        )
        self.card_net.add_extra_line(
            f"累计上传：{net.total_up_gb:.1f} GB", c["text_dim"]
        )

        # 磁盘
        self.card_disk.set_value(f"{len(snap.disks)} 个分区", "")
        self.card_disk.set_bar(0)
        self.card_disk.bar.setVisible(False)
        self.card_disk.clear_extra()
        if not snap.disks:
            self.card_disk.add_extra_line("无可用分区", c["text_dim"])
        else:
            for d in snap.disks:
                color = self._color_by_percent(d.percent)
                dev = d.device.rstrip("\\")
                self.card_disk.add_extra_line(
                    f"{dev}  {d.used_gb:.1f} / {d.total_gb:.1f} GB  "
                    f"({d.percent:.0f}%)",
                    color,
                    bar_percent=d.percent,
                )

        # GPU
        self._apply_gpu(snap)

        # 系统信息
        self.sys_box.update_info(snap)

        # 时间戳
        import time
        self.ts_label.setText(f"最后刷新：{time.strftime('%H:%M:%S')}")

    def _apply_gpu(self, snap):
        c = self.colors
        gpus = snap.gpus or []

        # 没有任何 GPU 信息 → 整张卡片隐藏
        if not gpus:
            self.card_gpu.setVisible(False)
            return

        self.card_gpu.setVisible(True)

        self.card_gpu.set_value(f"{len(gpus)} 个 GPU", "")
        self.card_gpu.set_bar(0)
        self.card_gpu.bar.setVisible(False)
        self.card_gpu.clear_extra()

        for g in gpus:
            vendor_tag = {
                "nvidia": "NVIDIA",
                "amd": "AMD",
                "intel": "Intel",
                "other": "GPU",
            }.get(g.vendor, "GPU")

            # 占用率能拿到就显示
            if g.percent >= 0:
                line1 = f"{vendor_tag}  {g.name}  —  {g.percent:.0f}%"
                color = self._color_by_percent(g.percent)
                bar_pct = g.percent
            else:
                line1 = f"{vendor_tag}  {g.name}"
                color = c["text_dim"]
                bar_pct = None

            self.card_gpu.add_extra_line(line1, color, bar_percent=bar_pct)

            # 第二行：显存 / 温度
            extras = []
            if g.mem_total_gb > 0:
                if g.mem_used_gb >= 0:
                    extras.append(
                        f"显存：{g.mem_used_gb:.1f} / {g.mem_total_gb:.1f} GB"
                    )
                else:
                    extras.append(f"显存：{g.mem_total_gb:.1f} GB")
            if g.temp_c >= 0:
                extras.append(f"{g.temp_c:.0f}°C")
            if g.vendor == "intel" and not extras:
                extras.append("共享显存")
            if extras:
                self.card_gpu.add_extra_line(
                    "  ".join(extras), c["text_dim"]
                )

    @staticmethod
    def _color_by_percent(p: float) -> str:
        if p >= 90:
            return _FALLBACK["error"]
        if p >= 70:
            return _FALLBACK["warn"]
        return _FALLBACK["accent"]

    # ---------- 自动刷新 ----------
    def _on_auto_changed(self, state):
        if state:
            self._start_timer()
        else:
            self._stop_timer()

    def _start_timer(self):
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self.refresh_once)
        self._timer.start(self.REFRESH_MS)

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.stop()

    # ---------- 生命周期：显示启动，隐藏停 ----------
    def showEvent(self, e):
        super().showEvent(e)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(0, self.refresh_once)
        if self.auto_check.isChecked():
            self._start_timer()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._stop_timer()

    def cleanup(self):
        self._stop_timer()