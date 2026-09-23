import re
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ReminderIntent:
    when: datetime
    what: str
    raw: str


UNIT = {"秒": 1, "分钟": 60, "分": 60, "小时": 3600, "时": 3600, "天": 86400}


CN_NUM = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
    "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
    "二十一": 21, "二十二": 22, "二十三": 23, "二十四": 24,
}

_NUM_PAT = r"(\d{1,2}|[一二两三四五六七八九十]{1,3})"


def cn_to_int(s: str) -> int | None:
    if not s:
        return None
    if s.isdigit():
        return int(s)
    return CN_NUM.get(s)


# ==================== 精确匹配（原逻辑，带「提醒我」字样） ====================

_REL = re.compile(
    r"(\d+)\s*(秒|分钟|分|小时|时|天)\s*(?:后|之后)\s*(?:提醒我?|叫我|通知我?)?\s*(.*)"
)

_ABS = re.compile(
    r"(今天|明天|后天)?\s*(早上|上午|中午|下午|晚上)?\s*(\d{1,2})\s*[点:：]\s*(\d{0,2})\s*分?\s*(.*)"
)


def parse_reminder(text: str) -> ReminderIntent | None:
    if not text:
        return None
    text = text.strip()

    m = _REL.search(text)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        what = (m.group(3) or "").strip() or "提醒"
        when = datetime.now() + timedelta(seconds=n * UNIT[unit])
        return ReminderIntent(when, what, text)

    m = _ABS.search(text)
    if m:
        day_word = m.group(1) or "今天"
        period = m.group(2)
        hour = int(m.group(3))
        minute = int(m.group(4) or 0)
        what = (m.group(5) or "").strip() or "提醒"
        return _build_abs(day_word, period, hour, minute, what, text)

    return None


# ==================== 宽松匹配（支持中文数字） ====================

_REL_LOOSE = re.compile(r"(\d+)\s*(秒|分钟|分|小时|时|天)\s*(?:后|之后)")

_ABS_LOOSE = re.compile(
    rf"(今天|明天|后天)?\s*(早上|上午|中午|下午|晚上)?\s*{_NUM_PAT}\s*[点:：]\s*"
    rf"({_NUM_PAT})?\s*分?"
)


def parse_reminder_loose(text: str) -> ReminderIntent | None:
    if not text:
        return None
    text = text.strip()

    # 相对时间
    m = _REL_LOOSE.search(text)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        rest = text[m.end():].strip(" ，,。.!！?？:：")
        what = rest[:30] or "提醒"
        when = datetime.now() + timedelta(seconds=n * UNIT[unit])
        return ReminderIntent(when, what, text)

    # 绝对时间
    m = _ABS_LOOSE.search(text)
    if m:
        day_word = m.group(1) or "今天"
        period = m.group(2)
        hour = cn_to_int(m.group(3))
        minute = cn_to_int(m.group(4)) if m.group(4) else 0
        if hour is None:
            return None
        if minute is None:
            minute = 0
        rest = text[m.end():].strip(" ，,。.!！?？:：")
        what = rest[:30] or "提醒"
        return _build_abs(day_word, period, hour, minute, what, text)

    return None


def _build_abs(day_word, period, hour, minute, what, text) -> ReminderIntent | None:
    base = datetime.now()
    if day_word == "明天":
        base += timedelta(days=1)
    elif day_word == "后天":
        base += timedelta(days=2)

    if period in ("下午", "晚上") and hour < 12:
        hour += 12
    elif period == "中午" and hour < 12:
        hour = 12

    try:
        when = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return None

    if when < datetime.now() and day_word == "今天":
        when += timedelta(days=1)
    return ReminderIntent(when, what, text)


# ==================== 整篇扫描 ====================

INTENT_WORDS = [
    "提醒", "叫我", "记得", "别忘", "要", "需要", "安排", "计划", "约",
]


def scan_note_for_reminder(text: str) -> ReminderIntent | None:
    """
    整篇笔记扫描提醒意图：
    1) 严格版逐行匹配
    2) 宽松版逐行匹配（有时间即可，不再强制意图词）
    """
    if not text:
        return None

    # 1) 严格
    for line in text.splitlines():
        intent = parse_reminder(line)
        if intent:
            return intent

    # 2) 宽松：有时间就建
    for line in text.splitlines():
        intent = parse_reminder_loose(line)
        if intent:
            return intent

    return None