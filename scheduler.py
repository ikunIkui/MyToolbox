import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler


@dataclass
class Task:
    id: str
    kind: str          # "timer" | "shutdown"
    label: str
    due_at: datetime


def fmt_duration(secs: int) -> str:
    secs = max(0, int(secs))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}小时{m}分"
    if m:
        return f"{m}分{s}秒" if s else f"{m}分钟"
    return f"{s}秒"


class TaskScheduler:
    def __init__(self):
        self._sched = BackgroundScheduler(daemon=True)
        self._sched.start()
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._counter = 0
        self._notify: Callable[[str, str], None] = lambda t, m: None
        self._notify_timer_done: Callable[[Task], None] | None = None
        self._history = None

    def set_notify(self, fn: Callable[[str, str], None]):
        self._notify = fn

    def set_notify_timer_done(self, fn: Callable[[Task], None]):
        """倒计时到点的专用回调：让 UI 层决定要不要带按钮"""
        self._notify_timer_done = fn

    def set_history(self, history):
        self._history = history

    def shutdown(self):
        """退出时停掉调度器，避免残留线程"""
        try:
            self._sched.shutdown(wait=False)
        except Exception:
            pass

    # ---------- 查询 ----------
    def list_tasks(self) -> list[Task]:
        with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t.due_at)

    # ---------- 倒计时 ----------
    def add_timer(self, seconds: int, label: str) -> Task:
        tid = self._next_id("timer")
        due = datetime.now() + timedelta(seconds=seconds)
        task = Task(tid, "timer", label, due)
        with self._lock:
            self._tasks[tid] = task
        self._sched.add_job(
            self._fire_timer, "date", run_date=due,
            args=[tid], id=tid, misfire_grace_time=60,
        )
        return task

    def _fire_timer(self, tid: str):
        with self._lock:
            task = self._tasks.pop(tid, None)
        if not task:
            return

        if self._notify_timer_done is not None:
            try:
                self._notify_timer_done(task)
            except Exception as e:
                print(f"[scheduler] notify_timer_done 失败: {e}")
                self._notify("⏰ 时间到", task.label)
        else:
            self._notify("⏰ 时间到", task.label)

        if self._history:
            try:
                self._history.add(
                    task.kind, task.label, "done",
                    created_at=task.due_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            except Exception:
                pass

    # ---------- 定时关机 ----------
    def add_shutdown(self, seconds: int) -> Task:
        tid = self._next_id("shutdown")
        due = datetime.now() + timedelta(seconds=seconds)
        task = Task(tid, "shutdown", f"{fmt_duration(seconds)}后关机", due)
        with self._lock:
            self._tasks[tid] = task

        warn_at = due - timedelta(seconds=60)
        if warn_at > datetime.now():
            self._sched.add_job(
                self._warn_shutdown, "date", run_date=warn_at,
                args=[tid], id=tid + "-warn", misfire_grace_time=30,
            )

        self._sched.add_job(
            self._fire_shutdown, "date", run_date=due,
            args=[tid], id=tid, misfire_grace_time=30,
        )
        return task

    def _warn_shutdown(self, tid: str):
        with self._lock:
            exists = tid in self._tasks
        if exists:
            self._notify("⚠️ 即将关机", "还有 1 分钟将自动关机，可在任务面板取消")

    def _fire_shutdown(self, tid: str):
        with self._lock:
            task = self._tasks.pop(tid, None)
        if task:
            subprocess.run("shutdown /s /t 0", shell=True)
            if self._history:
                try:
                    self._history.add(
                        task.kind, task.label, "done",
                        created_at=task.due_at.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                except Exception:
                    pass

    # ---------- 取消 ----------
    def cancel(self, tid: str) -> bool:
        with self._lock:
            task = self._tasks.pop(tid, None)
        existed = task is not None
        for jid in (tid, tid + "-warn"):
            try:
                self._sched.remove_job(jid)
            except Exception:
                pass
        if existed and self._history:
            try:
                self._history.add(
                    task.kind, task.label, "cancelled",
                    created_at=task.due_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            except Exception:
                pass
        return existed

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter}"