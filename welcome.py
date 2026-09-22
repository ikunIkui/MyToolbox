from datetime import datetime

from app_paths import load_config


WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


def _greeting_by_hour(hour: int) -> str:
    if 5 <= hour < 9:
        return "早上好"
    if 9 <= hour < 12:
        return "上午好"
    if 12 <= hour < 14:
        return "中午好"
    if 14 <= hour < 18:
        return "下午好"
    if 18 <= hour < 23:
        return "晚上好"
    return "夜深了"


def build_welcome(win) -> tuple[str, str]:
    """
    返回 (标题, 正文)。
    正文形如：
      9月22日 星期二 · 成都 21°C 多云
      3 个待办 · 2 个任务
    """
    now = datetime.now()
    wd = WEEKDAYS[now.weekday()]
    date_str = f"{now.month}月{now.day}日 星期{wd}"

    greeting = _greeting_by_hour(now.hour)

    # 天气
    weather_str = ""
    try:
        wc = getattr(win, "weather_card", None)
        if wc is not None:
            city = wc.city_label.text().replace("（手动）", "").strip()
            temp = wc.temp_label.text().strip()
            desc = wc.desc_label.text().strip()
            if city and temp and temp != "--°C":
                weather_str = f"{city} {temp} {desc}"
    except Exception:
        pass

    # 统计
    try:
        from todo_db import TodoDB
        todo_n = len(TodoDB().list_pending())
    except Exception:
        todo_n = 0

    try:
        task_n = len(win.scheduler.list_tasks())
    except Exception:
        task_n = 0

    # 组装
    line1 = date_str + (f" · {weather_str}" if weather_str else "")

    parts = []
    if todo_n:
        parts.append(f"{todo_n} 个待办")
    if task_n:
        parts.append(f"{task_n} 个任务")
    line2 = " · ".join(parts) if parts else "今天也是元气满满的一天"

    title = f"👋 {greeting}"
    body = f"{line1}\n{line2}"
    return title, body


def should_show_welcome() -> bool:
    """每天只弹一次"""
    today = datetime.now().strftime("%Y-%m-%d")
    cfg = load_config()
    return cfg.get("last_welcome_date", "") != today


def mark_welcome_shown():
    today = datetime.now().strftime("%Y-%m-%d")
    cfg = load_config()
    cfg["last_welcome_date"] = today
    from app_paths import save_config
    save_config(cfg)