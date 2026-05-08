from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from app.config import CANONICAL_FILES
from app.services.repo_reader import RepoReader


ARTICLE_ID_RE = re.compile(r"(?<!\d)(\d{3}[A-Z]?)(?!\d)")
PUBLICATION_SECTION_RE = re.compile(r"##\s*发布状态(?P<body>.*?)(?:\n---|\Z)", re.DOTALL)
CASE_HEADING_RE = re.compile(r"^##\s+(CASE-[^\n]+)$", re.MULTILINE)
CASE_ID_RE = re.compile(r"\bcase_id:\s*[\"']?([^\"'\n]+)", re.IGNORECASE)
ARTICLE_FILE_RE = re.compile(r"\barticle_file:\s*[\"']?([^\"'\n]+)", re.IGNORECASE)
ARTICLE_PUBLISHED_RE = re.compile(r"\barticle_published:\s*[\"']?([^\"'\n]+)", re.IGNORECASE)
DEPTH_DRAFT_RE = re.compile(r"\bdepth_draft:\s*[\"']?([^\"'\n]+)", re.IGNORECASE)


@dataclass(frozen=True)
class AuditConflict:
    check: str
    risk_level: str
    message: str
    evidence: list[dict[str, Any]]
    suggested_files: list[str]
    minimal_fix: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StatusAuditor:
    def __init__(self, reader: RepoReader) -> None:
        self.reader = reader

    def audit(self, preflight: dict[str, Any] | None = None) -> dict[str, Any]:
        if preflight is None:
            canonical = self.reader.read_canonical_files()
            read_files = [_read_file_summary(item) for item in canonical.get("files", [])]
        else:
            canonical = {
                "status": preflight.get("status"),
                "files": [],
            }
            read_files = preflight.get("read_files", [])

        canonical_files = (
            self.reader.read_canonical_files()
            if preflight is not None
            else canonical
        )
        contents = {
            item.get("path"): item.get("content") or ""
            for item in canonical_files.get("files", [])
            if item.get("status") == "ok"
        }

        conflicts: list[AuditConflict] = []
        if canonical.get("status") != "ok":
            conflicts.append(
                AuditConflict(
                    check="canonical_files_read",
                    risk_level="high",
                    message="canonical 文件本次没有全部读取成功，状态审计不完整。",
                    evidence=read_files,
                    suggested_files=CANONICAL_FILES,
                    minimal_fix="先修复仓库读取配置或文件路径，再重新运行状态审计。",
                )
            )

        readme = contents.get("README.md", "")
        status_table = contents.get("ops/执行状态总表.md", "")
        case_index = contents.get("cases/2026/case-index.md", "")
        case_cards = contents.get("cases/2026/case-cards.md", "")

        readme_status = _extract_readme_publication_statuses(readme)
        status_table_status = _extract_article_statuses(status_table, "ops/执行状态总表.md")
        case_index_status = _extract_case_index_statuses(case_index)
        cards = _extract_case_cards(case_cards)

        conflicts.extend(_check_readme_vs_status_table(readme_status, status_table_status))
        conflicts.extend(_check_case_index_vs_cards(case_index_status, cards))
        conflicts.extend(_check_published_marked_waiting(case_index_status, cards, readme_status, status_table_status))
        conflicts.extend(_check_depth_draft_without_case_card(cards))
        conflicts.extend(_check_cards_missing_article_published(cards))

        risk_level = _overall_risk(conflicts)
        conclusion = _conclusion(conflicts)
        minimal_fix_plan = _minimal_fix_plan(conflicts)
        conflict_dicts = [conflict.to_dict() for conflict in conflicts]
        answer_markdown = _answer_markdown(
            conclusion=conclusion,
            read_files=read_files,
            risk_level=risk_level,
            minimal_fix_plan=minimal_fix_plan,
        )
        return {
            "status": "ok",
            "conclusion": conclusion,
            "read_files": read_files,
            "evidence": conflict_dicts,
            "risks": [conflict.message for conflict in conflicts] or ["未发现明确状态冲突。"],
            "minimal_next_step": minimal_fix_plan[0] if minimal_fix_plan else "无需修复。",
            "ingest_draft": {
                "required": bool(conflicts),
                "reason": "状态审计只生成最小修复建议，不直接写仓库。",
                "suggested_files": _unique_file_list(
                    file_path
                    for conflict in conflicts
                    for file_path in conflict.suggested_files
                ),
            },
            "answer_markdown": answer_markdown,
            "summary": {
                "readme_article_count": len(readme_status),
                "status_table_article_count": len(status_table_status),
                "case_index_article_count": len(case_index_status),
                "case_card_count": len(cards),
                "conflict_count": len(conflicts),
                "risk_level": risk_level,
            },
            "conflicts": conflict_dicts,
            "risk_level": risk_level,
            "minimal_fix_plan": minimal_fix_plan,
            "suggested_files": _unique_file_list(
                file_path
                for conflict in conflicts
                for file_path in conflict.suggested_files
            ),
            "codex_instruction": _codex_instruction(conflicts),
        }


def _read_file_summary(item: dict[str, Any]) -> dict[str, Any]:
    file_meta = item.get("file") or {}
    return {
        "path": item.get("path"),
        "status": item.get("status"),
        "source": file_meta.get("source") or item.get("source"),
        "size": file_meta.get("size"),
        "last_modified": file_meta.get("last_modified"),
    }


def _extract_article_statuses(content: str, source: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(content.splitlines(), start=1):
        for match in ARTICLE_ID_RE.finditer(line):
            article_id = match.group(1)
            if article_id.startswith("20"):
                continue
            status = _line_status(line)
            if not status:
                continue
            result[article_id] = {
                "id": article_id,
                "status": status,
                "source": source,
                "line": line_number,
                "text": line.strip(),
            }
    return result


def _extract_readme_publication_statuses(content: str) -> dict[str, dict[str, Any]]:
    match = PUBLICATION_SECTION_RE.search(content)
    if not match:
        return {}
    body = match.group("body")
    offset = content[: match.start("body")].count("\n")
    result: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(body.splitlines(), start=offset + 1):
        for item in re.finditer(r"(?<!\d)(\d{3}[A-Z]?)(?!\d)\s+([^\d\n]+?)(?=(?:\s+\d{3}[A-Z]?\s)|$)", line):
            article_id = item.group(1)
            status_text = item.group(2).strip()
            status = _line_status(status_text)
            if not status:
                continue
            result[article_id] = {
                "id": article_id,
                "status": status,
                "source": "README.md",
                "line": line_number,
                "text": item.group(0).strip(),
            }
    return result


def _extract_case_index_statuses(content: str) -> dict[str, dict[str, Any]]:
    return _extract_article_statuses(content, "cases/2026/case-index.md")


def _extract_case_cards(content: str) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    headings = list(CASE_HEADING_RE.finditer(content))
    for index, heading in enumerate(headings):
        start = heading.start()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        block = content[start:end]
        line = content[:start].count("\n") + 1
        heading_text = heading.group(1).strip()
        article_file = _first_match(ARTICLE_FILE_RE, block)
        article_published = _first_match(ARTICLE_PUBLISHED_RE, block)
        depth_draft = _first_match(DEPTH_DRAFT_RE, block)
        case_id = _first_match(CASE_ID_RE, block) or heading_text.split("·")[0].strip()
        article_id = _article_id_from_text(article_file or heading_text)
        cards[case_id] = {
            "case_id": case_id,
            "heading": heading_text,
            "article_id": article_id,
            "article_file": article_file,
            "article_published": article_published,
            "depth_draft": depth_draft,
            "source": "cases/2026/case-cards.md",
            "line": line,
        }
    return cards


def _check_readme_vs_status_table(
    readme: dict[str, dict[str, Any]],
    status_table: dict[str, dict[str, Any]],
) -> list[AuditConflict]:
    conflicts: list[AuditConflict] = []
    for article_id in sorted(set(readme) & set(status_table)):
        left = readme[article_id]
        right = status_table[article_id]
        if _status_bucket(left["status"]) == _status_bucket(right["status"]):
            continue
        conflicts.append(
            AuditConflict(
                check="readme_vs_status_table",
                risk_level="high",
                message=f"README 与执行状态总表对文章 {article_id} 的状态口径不一致。",
                evidence=[left, right],
                suggested_files=["README.md", "ops/执行状态总表.md"],
                minimal_fix=f"确认文章 {article_id} 的真实状态，并只改动 README 或执行状态总表中落后的那一处。",
            )
        )
    return conflicts


def _check_case_index_vs_cards(
    case_index: dict[str, dict[str, Any]],
    cards: dict[str, dict[str, Any]],
) -> list[AuditConflict]:
    conflicts: list[AuditConflict] = []
    card_article_ids = {
        card["article_id"]: card
        for card in cards.values()
        if card.get("article_id")
    }
    for case_id, card in sorted(cards.items()):
        article_id = card.get("article_id")
        if not article_id:
            continue
        if article_id not in case_index:
            conflicts.append(
                AuditConflict(
                    check="case_cards_vs_case_index",
                    risk_level="medium",
                    message=f"{case_id} 指向文章 {article_id}，但 case-index 未找到该文章编号。",
                    evidence=[card],
                    suggested_files=["cases/2026/case-index.md", "cases/2026/case-cards.md"],
                    minimal_fix=f"确认 {case_id} 的 article_file 编号是否正确；若正确，在 case-index 补充文章 {article_id} 的状态。",
                )
            )
    return conflicts


def _check_published_marked_waiting(
    case_index: dict[str, dict[str, Any]],
    cards: dict[str, dict[str, Any]],
    readme: dict[str, dict[str, Any]],
    status_table: dict[str, dict[str, Any]],
) -> list[AuditConflict]:
    conflicts: list[AuditConflict] = []
    published_ids = {
        article_id
        for source in (case_index, readme, status_table)
        for article_id, item in source.items()
        if _status_bucket(item["status"]) == "published"
    }
    for card in cards.values():
        article_id = card.get("article_id")
        article_published = str(card.get("article_published") or "")
        if not article_id or article_id not in published_ids:
            continue
        if _status_bucket(article_published) == "waiting":
            conflicts.append(
                AuditConflict(
                    check="published_article_still_waiting",
                    risk_level="high",
                    message=f"文章 {article_id} 已发布，但案例卡 article_published 仍标为待发布/待写。",
                    evidence=[card],
                    suggested_files=["cases/2026/case-cards.md"],
                    minimal_fix=f"把文章 {article_id} 对应案例卡的 article_published 更新为发布日期，或确认文章编号映射是否错误。",
                )
            )
    return conflicts


def _check_depth_draft_without_case_card(cards: dict[str, dict[str, Any]]) -> list[AuditConflict]:
    conflicts: list[AuditConflict] = []
    for card in cards.values():
        if card.get("depth_draft"):
            continue
        if "CASE-" not in str(card.get("heading")):
            continue
        conflicts.append(
            AuditConflict(
                check="case_card_missing_depth_draft",
                risk_level="low",
                message=f"{card['case_id']} 缺少 depth_draft 字段，无法回链深度底稿。",
                evidence=[card],
                suggested_files=["cases/2026/case-cards.md"],
                minimal_fix=f"若 {card['case_id']} 有深度底稿，在案例卡补 `depth_draft`；若没有，保留但标注为轻量卡。",
            )
        )
    return conflicts


def _check_cards_missing_article_published(cards: dict[str, dict[str, Any]]) -> list[AuditConflict]:
    conflicts: list[AuditConflict] = []
    for card in cards.values():
        if card.get("article_published"):
            continue
        conflicts.append(
            AuditConflict(
                check="case_card_missing_article_published",
                risk_level="medium",
                message=f"{card['case_id']} 缺少 article_published 字段。",
                evidence=[card],
                suggested_files=["cases/2026/case-cards.md"],
                minimal_fix=f"在 {card['case_id']} 案例卡补 `article_published`，值为发布日期、待发布、待写或不适用。",
            )
        )
    return conflicts


def _line_status(line: str) -> str | None:
    if "已发布" in line or "published" in line.lower():
        return "已发布"
    if any(token in line for token in ("待发布", "待写", "待补", "骨架", "暂缓", "占位")):
        return "待发布"
    return None


def _status_bucket(status: str | None) -> str:
    value = str(status or "").lower()
    if "已发布" in value or "published" in value or re.search(r"20\d{2}-\d{2}-\d{2}", value):
        return "published"
    if any(token in value for token in ("待发布", "待写", "待补", "骨架", "暂缓", "占位")):
        return "waiting"
    return "unknown"


def _article_id_from_text(value: str | None) -> str | None:
    if not value:
        return None
    match = ARTICLE_ID_RE.search(value)
    return match.group(1) if match else None


def _first_match(pattern: re.Pattern[str], content: str) -> str | None:
    match = pattern.search(content)
    return match.group(1).strip() if match else None


def _overall_risk(conflicts: list[AuditConflict]) -> str:
    levels = [conflict.risk_level for conflict in conflicts]
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    if "low" in levels:
        return "low"
    return "none"


def _conclusion(conflicts: list[AuditConflict]) -> str:
    if not conflicts:
        return "未发现明确状态冲突。"
    high = sum(1 for item in conflicts if item.risk_level == "high")
    medium = sum(1 for item in conflicts if item.risk_level == "medium")
    low = sum(1 for item in conflicts if item.risk_level == "low")
    return f"发现 {len(conflicts)} 个状态审计项：high={high}, medium={medium}, low={low}。"


def _minimal_fix_plan(conflicts: list[AuditConflict]) -> list[str]:
    if not conflicts:
        return ["无需修复。"]
    return _unique_file_list(conflict.minimal_fix for conflict in conflicts)


def _codex_instruction(conflicts: list[AuditConflict]) -> str:
    if not conflicts:
        return "无需执行修改。"
    files = ", ".join(_unique_file_list(file_path for conflict in conflicts for file_path in conflict.suggested_files))
    return (
        "请先读取以下文件的当前内容，再按 minimal_fix_plan 做最小修改草稿，"
        f"不要直接写 GitHub：{files}"
    )


def _answer_markdown(
    conclusion: str,
    read_files: list[dict[str, Any]],
    risk_level: str,
    minimal_fix_plan: list[str],
) -> str:
    read_file_lines = [
        f"- {item.get('path')}：{item.get('status')} / {item.get('source') or 'unknown'}"
        for item in read_files
    ]
    fix_lines = [f"- {item}" for item in minimal_fix_plan]
    return "\n".join(
        [
            "## 结论",
            conclusion,
            "",
            "## 已读取文件",
            *(read_file_lines or ["- 无"]),
            "",
            "## 风险",
            f"- {risk_level}",
            "",
            "## 最小下一步",
            *(fix_lines or ["- 无需修复。"]),
        ]
    )


def _unique_file_list(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
