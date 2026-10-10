"""
系统监控数据采集（纯逻辑，无 UI）。
依赖：psutil
"""

import platform
import socket
import subprocess
import time
from dataclasses import dataclass, field

try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False


# ==================== 数据结构 ====================

@dataclass
class CpuInfo:
    percent: float = 0.0          # 总占用率 %
    cores: int = 0                # 逻辑核心数
    freq_mhz: float = 0.0         # 当前频率 MHz


@dataclass
class MemInfo:
    percent: float = 0.0          # 占用率 %
    used_gb: float = 0.0
    total_gb: float = 0.0
    swap_percent: float = 0.0
    swap_used_gb: float = 0.0
    swap_total_gb: float = 0.0


@dataclass
class NetInfo:
    down_bps: float = 0.0         # 下载 B/s
    up_bps: float = 0.0           # 上传 B/s
    total_down_gb: float = 0.0
    total_up_gb: float = 0.0


@dataclass
class DiskPart:
    device: str = ""              # "C:\\"
    percent: float = 0.0
    used_gb: float = 0.0
    total_gb: float = 0.0


@dataclass
class GpuPart:
    name: str = ""                # "NVIDIA GeForce RTX 3060"
    vendor: str = ""              # "nvidia" | "amd" | "intel" | "other"
    percent: float = -1.0         # 占用率 %，-1 表示拿不到
    mem_used_gb: float = -1.0     # 显存已用，-1 拿不到
    mem_total_gb: float = -1.0    # 显存总量
    temp_c: float = -1.0          # 温度，-1 拿不到


@dataclass
class SysInfo:
    os_name: str = ""
    boot_uptime: str = ""
    cpu_model: str = ""
    host_user: str = ""


@dataclass
class Snapshot:
    cpu: CpuInfo = field(default_factory=CpuInfo)
    mem: MemInfo = field(default_factory=MemInfo)
    net: NetInfo = field(default_factory=NetInfo)
    disks: list[DiskPart] = field(default_factory=list)
    gpus: list[GpuPart] = field(default_factory=list)
    sys: SysInfo = field(default_factory=SysInfo)


# ==================== 工具 ====================

def _gb(n: int | float) -> float:
    return round(n / (1024 ** 3), 1)


def fmt_speed(bps: float) -> str:
    """字节/秒 → 人类可读"""
    if bps < 1024:
        return f"{bps:.0f} B/s"
    if bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps / (1024 * 1024):.1f} MB/s"


def fmt_uptime(seconds: float) -> str:
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        return f"{d} 天 {h} 小时 {m} 分"
    if h:
        return f"{h} 小时 {m} 分"
    return f"{m} 分钟"


# ==================== 采集器 ====================

class SysMonitor:
    """
    有状态采集器：
    - CPU percent 需要两次采样才有值（第一次会返回 0）
    - 网络速度需要前后两次计数差
    - GPU 型号只查一次并缓存，避免每 2 秒起 PowerShell 卡 UI
    """

    def __init__(self):
        self._last_net = None
        self._last_net_ts = None
        self._gpu_cache: list[GpuPart] | None = None   # GPU 型号缓存

        # 先做一次空采样，让 CPU percent 有基线
        if HAS_PSUTIL:
            try:
                psutil.cpu_percent(interval=None)
            except Exception:
                pass

    # ---------- CPU ----------
    def _cpu(self) -> CpuInfo:
        info = CpuInfo()
        if not HAS_PSUTIL:
            return info
        try:
            info.percent = psutil.cpu_percent(interval=None)
        except Exception:
            pass
        try:
            info.cores = psutil.cpu_count(logical=True) or 0
        except Exception:
            pass
        try:
            f = psutil.cpu_freq()
            if f:
                info.freq_mhz = round(f.current, 0)
        except Exception:
            pass
        return info

    # ---------- 内存 ----------
    def _mem(self) -> MemInfo:
        info = MemInfo()
        if not HAS_PSUTIL:
            return info
        try:
            m = psutil.virtual_memory()
            info.percent = m.percent
            info.used_gb = _gb(m.used)
            info.total_gb = _gb(m.total)
        except Exception:
            pass
        try:
            s = psutil.swap_memory()
            info.swap_percent = s.percent
            info.swap_used_gb = _gb(s.used)
            info.swap_total_gb = _gb(s.total)
        except Exception:
            pass
        return info

    # ---------- 网络 ----------
    def _net(self) -> NetInfo:
        info = NetInfo()
        if not HAS_PSUTIL:
            return info
        try:
            counters = psutil.net_io_counters()
            now = time.time()

            info.total_down_gb = _gb(counters.bytes_recv)
            info.total_up_gb = _gb(counters.bytes_sent)

            if self._last_net is not None and self._last_net_ts is not None:
                dt = now - self._last_net_ts
                if dt > 0:
                    info.down_bps = max(
                        0.0, (counters.bytes_recv - self._last_net.bytes_recv) / dt
                    )
                    info.up_bps = max(
                        0.0, (counters.bytes_sent - self._last_net.bytes_sent) / dt
                    )

            self._last_net = counters
            self._last_net_ts = now
        except Exception:
            pass
        return info

    # ---------- 磁盘 ----------
    def _disks(self) -> list[DiskPart]:
        parts: list[DiskPart] = []
        if not HAS_PSUTIL:
            return parts
        try:
            for p in psutil.disk_partitions(all=False):
                # 跳过光驱 / 未插入的盘
                if "cdrom" in p.opts or p.fstype == "":
                    continue
                try:
                    u = psutil.disk_usage(p.mountpoint)
                except Exception:
                    continue
                parts.append(DiskPart(
                    device=p.device,
                    percent=u.percent,
                    used_gb=_gb(u.used),
                    total_gb=_gb(u.total),
                ))
        except Exception:
            pass
        return parts

    # ---------- GPU ----------
    def _gpus(self) -> list[GpuPart]:
        """
        型号：只查一次并缓存（PowerShell 起进程慢，不能每 2 秒查）
        NVIDIA 动态数据：只有存在 nvidia 卡时才查 nvidia-smi
        """
        # 首次：查型号并缓存
        if self._gpu_cache is None:
            parts: list[GpuPart] = []
            try:
                names = self._list_gpu_names()
            except Exception:
                names = []
            for name in names:
                vendor = self._detect_vendor(name)
                parts.append(GpuPart(name=name, vendor=vendor))
            self._gpu_cache = parts

        # 拷贝一份，避免调用方改到缓存
        parts = [
            GpuPart(
                name=g.name, vendor=g.vendor,
                percent=g.percent, mem_used_gb=g.mem_used_gb,
                mem_total_gb=g.mem_total_gb, temp_c=g.temp_c,
            )
            for g in self._gpu_cache
        ]

        # NVIDIA 动态数据：只有存在 nvidia 卡时才查
        has_nvidia = any(g.vendor == "nvidia" for g in parts)
        if has_nvidia:
            try:
                nv = self._nvidia_smi()
            except Exception:
                nv = []
            for g in parts:
                if g.vendor != "nvidia":
                    continue
                if not nv:
                    break
                info = nv.pop(0)
                g.percent = info.get("percent", -1.0)
                g.mem_used_gb = info.get("mem_used_gb", -1.0)
                g.mem_total_gb = info.get("mem_total_gb", -1.0)
                g.temp_c = info.get("temp_c", -1.0)

        return parts

    @staticmethod
    def _detect_vendor(name: str) -> str:
        n = name.lower()
        if "nvidia" in n or "geforce" in n or "rtx" in n or "gtx" in n:
            return "nvidia"
        if "amd" in n or "radeon" in n:
            return "amd"
        if "intel" in n or "iris" in n or "uhd" in n or "hd graphics" in n:
            return "intel"
        return "other"

    @staticmethod
    def _list_gpu_names() -> list[str]:
        """用 PowerShell 拿显卡型号（零依赖，只调一次）"""
        cmd = (
            'powershell -NoProfile -Command '
            '"Get-CimInstance Win32_VideoController | '
            'Select-Object -ExpandProperty Name"'
        )
        try:
            out = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=4,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            return []
        if out.returncode != 0:
            return []
        names = []
        for line in (out.stdout or "").splitlines():
            line = line.strip()
            if line:
                names.append(line)
        # 去重
        seen = set()
        uniq = []
        for n in names:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        return uniq

    @staticmethod
    def _nvidia_smi() -> list[dict]:
        """调 nvidia-smi 拿 NVIDIA 显卡详细数据，拿不到返回 []"""
        cmd = (
            'nvidia-smi --query-gpu=name,utilization.gpu,memory.used,'
            'memory.total,temperature.gpu '
            '--format=csv,noheader,nounits'
        )
        try:
            out = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=4,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            return []
        if out.returncode != 0:
            return []

        results = []
        for line in (out.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            try:
                name = parts[0]
                percent = float(parts[1])
                mem_used_mb = float(parts[2])
                mem_total_mb = float(parts[3])
                temp = float(parts[4])
            except Exception:
                continue
            results.append({
                "name": name,
                "percent": percent,
                "mem_used_gb": round(mem_used_mb / 1024, 1),
                "mem_total_gb": round(mem_total_mb / 1024, 1),
                "temp_c": temp,
            })
        return results

    # ---------- 系统信息（静态，只读一次也行） ----------
    def _sys(self) -> SysInfo:
        info = SysInfo()

        # ----- 操作系统（判断 Win10 / Win11） -----
        try:
            rel = platform.release()          # "10"
            ver = platform.version()          # "10.0.22631"
            build = 0
            if ver:
                try:
                    build = int(ver.split(".")[-1])
                except Exception:
                    build = 0
            # Windows 11 底层还是 NT 10.0，用 build >= 22000 判断
            if rel == "10" and build >= 22000:
                rel = "11"
            if build:
                info.os_name = f"Windows {rel} ({build})"
            else:
                info.os_name = f"Windows {rel}"
        except Exception:
            pass

        # ----- 开机时长 -----
        try:
            if HAS_PSUTIL:
                up = time.time() - psutil.boot_time()
                info.boot_uptime = fmt_uptime(up)
        except Exception:
            pass

        # ----- CPU 型号（优先读注册表） -----
        try:
            model = ""
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                )
                model = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
                winreg.CloseKey(key)
            except Exception:
                model = ""
            if not model:
                model = platform.processor() or "未知"
            info.cpu_model = model
        except Exception:
            pass

        # ----- 主机名 / 用户名 -----
        try:
            host = socket.gethostname()
            user = ""
            try:
                import getpass
                user = getpass.getuser()
            except Exception:
                pass
            info.host_user = f"{host} / {user}" if user else host
        except Exception:
            pass

        return info

    # ---------- 一次完整快照 ----------
    def snapshot(self) -> Snapshot:
        snap = Snapshot()
        if not HAS_PSUTIL:
            snap.sys.os_name = "psutil 未安装"
            return snap
        snap.cpu = self._cpu()
        snap.mem = self._mem()
        snap.net = self._net()
        snap.disks = self._disks()
        snap.gpus = self._gpus()
        snap.sys = self._sys()
        return snap