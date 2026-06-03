from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.research_state import slugify


KNOWN_METHOD_PATTERNS = [
    "diagnosis gap",
    "feedback loop",
    "failure mode",
    "MTP",
    "FM015",
    "诊断空白",
    "反馈回路",
    "信任冲突",
    "推荐偏差",
]


@dataclass(frozen=True)
class ThoughtEntity:
    name: str
    slug: str
    entity_type: str


def extract_entities(text: str) -> list[ThoughtEntity]:
    raw = text or ""
    candidates: list[str] = []
    candidates.extend(re.findall(r"\b[A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*){0,3}\s+AI\b", raw))
    candidates.extend(re.findall(r"\b[A-Z][A-Za-z0-9]{2,}(?:\.[a-z]{2,})?\b", raw))
    candidates.extend(pattern for pattern in KNOWN_METHOD_PATTERNS if pattern.lower() in raw.lower())
    candidates.extend(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+(?:公司|产品|案例|理论|框架|方法|模型)", raw))
    entities: list[ThoughtEntity] = []
    seen: set[str] = set()
    for value in candidates:
        name = _clean_name(value)
        if not name:
            continue
        slug = slugify(name)
        if slug in seen:
            continue
        seen.add(slug)
        entities.append(ThoughtEntity(name=name, slug=slug, entity_type=classify_entity(name)))
    return entities[:12]


def classify_entity(name: str) -> str:
    lowered = name.lower()
    if lowered.endswith(" ai") or ".ai" in lowered or lowered in {"openai", "anthropic"}:
        return "product"
    if any(marker in lowered for marker in ["gap", "loop", "mode", "framework", "mtp", "fm015"]):
        return "methodology"
    if any(marker in name for marker in ["诊断", "框架", "方法", "理论", "模型", "冲突", "偏差"]):
        return "methodology"
    if any(marker in name for marker in ["案例"]):
        return "case"
    if any(marker in name for marker in ["公司"]):
        return "company"
    return "unknown"


def infer_topic(text: str, existing_topic: str = "", entities: list[ThoughtEntity] | None = None) -> str:
    if entities:
        return entities[0].name
    compact = " ".join((text or "").split())
    if compact:
        return compact[:80]
    return existing_topic or "未命名思考"


def _clean_name(value: str) -> str:
    name = re.sub(r"\s+", " ", value or "").strip(" ,.;:!?，。；：！？")
    stop_words = {"AI", "SK", "GPTS", "JSON", "API", "PR"}
    return "" if name in stop_words else name
