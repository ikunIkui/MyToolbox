import re


CATEGORY_RULES = {
    "待办": ["要", "记得", "别忘", "todo", "待办", "任务", "完成", "提交", "处理"],
    "日程": ["明天", "后天", "下周", "周一", "周二", "周三", "周四", "周五",
             "周六", "周日", "点", "开会", "见面", "约", "面试", "会议", "生日"],
    "灵感": ["灵感", "想法", "idea", "突然想到", "点子", "构思", "创意"],
    "学习": ["学习", "复习", "知识点", "笔记", "课程", "章节", "考试", "作业"],
    "财务": ["报销", "工资", "账单", "花", "买", "付", "转账", "发票", "钱"],
}


def classify(title: str, body: str) -> str:
    """返回分类名，识别不到返回「其他」"""
    text = f"{title}\n{body}"

    scores: dict[str, int] = {}
    for cat, words in CATEGORY_RULES.items():
        s = 0
        for w in words:
            # 英文小写匹配，中文直接 in
            if w.isascii():
                s += len(re.findall(w, text, re.IGNORECASE))
            else:
                s += text.count(w)
        if s > 0:
            scores[cat] = s

    if not scores:
        return "其他"

    # 取最高分，平局按固定顺序
    order = ["待办", "日程", "学习", "财务", "灵感"]
    best = max(scores.items(), key=lambda x: (x[1], -order.index(x[0]) if x[0] in order else 0))
    return best[0]