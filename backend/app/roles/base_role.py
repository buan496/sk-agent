from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.canonical_preflight import merge_read_files
from app.services.repo_reader import RepoReader


@dataclass(frozen=True)
class RoleContext:
    reader: RepoReader
    preflight: dict[str, Any]
    task_type: str
    allow_web: bool = False
    web_queries: list[str] | None = None
    web_results: list[dict[str, Any]] | None = None
    web_warnings: list[str] | None = None


class BaseRole:
    role_id = ""
    role_name = ""
    role_type = "internal"
    purpose = ""
    when_to_use: list[str] = []
    required_inputs: list[str] = []
    required_read_files: list[str] = []
    forbidden_actions: list[str] = []
    output_schema: list[str] = []
    system_prompt = ""

    def metadata(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "role_type": self.role_type,
            "purpose": self.purpose,
            "when_to_use": self.when_to_use,
            "required_inputs": self.required_inputs,
            "required_read_files": self.required_read_files,
            "forbidden_actions": self.forbidden_actions,
            "output_schema": self.output_schema,
            "system_prompt": self.system_prompt,
        }

    def run(self, user_input: str, notes: str, context: RoleContext) -> dict[str, Any]:
        raise NotImplementedError

    def read_required_files(self, context: RoleContext) -> list[dict[str, Any]]:
        return [_read_file_summary(context.reader.read_file(path)) for path in self.required_read_files]

    def role_result(
        self,
        *,
        context: RoleContext,
        conclusion: str,
        structured_output: dict[str, Any],
        risks: list[str],
        minimal_next_step: str,
        answer_markdown: str,
        read_files: list[dict[str, Any]] | None = None,
        should_ingest: bool = False,
        ingested: bool = False,
    ) -> dict[str, Any]:
        merged_read_files = merge_read_files(context.preflight.get("read_files", []), read_files or [])
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "conclusion": conclusion,
            "read_files": merged_read_files,
            "risks": risks,
            "minimal_next_step": minimal_next_step,
            "answer_markdown": answer_markdown,
            "human_readable_markdown": human_readable_report(
                conclusion=conclusion,
                structured_output=structured_output,
                risks=risks,
                minimal_next_step=minimal_next_step,
            ),
            "structured_output": structured_output,
            "web_used": bool(context.web_results),
            "web_queries": context.web_queries or [],
            "web_results_count": len(context.web_results or []),
            "evidence_ledger": structured_output.get("evidence_ledger", []),
            "missing_evidence": structured_output.get("missing_evidence", []),
            "warnings": context.web_warnings or structured_output.get("warnings", []),
            "should_ingest": should_ingest,
            "ingested": ingested,
        }


def markdown_from_sections(sections: list[tuple[str, Any]]) -> str:
    blocks: list[str] = []
    for title, body in sections:
        blocks.append(f"## {title}")
        if isinstance(body, list):
            blocks.extend(f"- {item}" for item in body)
        elif isinstance(body, dict):
            blocks.extend(f"- {key}: {value}" for key, value in body.items())
        else:
            blocks.append(str(body))
        blocks.append("")
    return "\n".join(blocks).strip()


def human_readable_report(
    *,
    conclusion: str,
    structured_output: dict[str, Any],
    risks: list[str],
    minimal_next_step: str,
) -> str:
    evidence = structured_output.get("evidence_ledger") or []
    missing = structured_output.get("missing_evidence") or []
    warnings = structured_output.get("warnings") or []
    found = _human_found_information(structured_output, evidence)
    sections = [
        ("当前判断", [conclusion or "暂时无法下结论。"]),
        ("当前找到的信息", found),
        ("缺失证据", _human_list(missing, "暂未列出额外缺失证据。")),
        ("风险", _human_list([*risks, *warnings], "暂未发现额外风险。")),
        ("下一步", [minimal_next_step or "先补齐证据，再做判断。"]),
    ]
    blocks: list[str] = ["# 研究简报", ""]
    for title, items in sections:
        blocks.append(f"## {title}")
        blocks.extend(f"- {item}" for item in items if item)
        blocks.append("")
    return "\n".join(blocks).strip()


def _human_found_information(structured_output: dict[str, Any], evidence: Any) -> list[str]:
    items: list[str] = []
    if isinstance(evidence, list):
        for entry in evidence[:10]:
            if not isinstance(entry, dict):
                continue
            title = entry.get("source_title") or entry.get("title") or "未命名来源"
            url = entry.get("source_url") or entry.get("url") or ""
            source_type = entry.get("source_type") or "unknown"
            level = entry.get("evidence_level") or "candidate"
            if url:
                items.append(f"{title}（{source_type}，{level}）：{url}")
            else:
                note = entry.get("note") or "暂未找到可引用来源。"
                items.append(f"{title}（{source_type}，{level}）：{note}")
    duplicate = structured_output.get("duplicate_check")
    if isinstance(duplicate, dict):
        status = duplicate.get("status") or "unknown"
        count = duplicate.get("match_count") or 0
        items.append(f"仓库排重结果：{status}，命中 {count} 条。")
    summary = structured_output.get("teardown_summary")
    if isinstance(summary, dict):
        product = summary.get("product")
        decision = summary.get("decision")
        if product or decision:
            items.append(f"产品初拆摘要：{product or '未命名产品'}，当前建议为 {decision or '待判断'}。")
    return items or ["暂未找到可引用的外部来源；当前输出主要是判断框架和证据缺口。"]


def _human_list(value: Any, fallback: str) -> list[str]:
    if isinstance(value, list):
        items = [str(item) for item in value if item]
        return items or [fallback]
    if value:
        return [str(value)]
    return [fallback]


def _read_file_summary(result: dict[str, Any]) -> dict[str, Any]:
    file_meta = result.get("file") or {}
    return {
        "path": result.get("path"),
        "status": result.get("status"),
        "source": file_meta.get("source") or result.get("source"),
        "size": file_meta.get("size"),
        "last_modified": file_meta.get("last_modified"),
        "message": result.get("message"),
    }
