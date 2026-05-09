from __future__ import annotations


CARRYOVER_PATTERNS = [
    "基于以上",
    "根据上面",
    "继续",
    "接着",
    "用刚才的",
    "整理以上候选来源",
    "基于这些来源",
    "不要重新搜索",
    "先不联网",
    "总结刚才结果",
    "刚才",
    "以上候选来源",
]


def is_carryover_intent(user_input: str) -> bool:
    normalized = (user_input or "").strip().lower()
    return any(pattern.lower() in normalized for pattern in CARRYOVER_PATTERNS)
