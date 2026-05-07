from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from app.services.repo_reader import RepoReader


ALLOWED_OPERATIONS = {"auto", "create", "append", "replace"}
MAX_DIFF_LINES = 400


@dataclass(frozen=True)
class PatchDraftInput:
    target_file: str
    intent: str
    new_content: str
    operation: str = "auto"


class PatchWriter:
    def __init__(self, reader: RepoReader) -> None:
        self.reader = reader

    def draft(self, draft_input: PatchDraftInput) -> dict[str, Any]:
        target_file = _normalize_repo_path(draft_input.target_file)
        if not target_file:
            raise ValueError("target_file 必须是仓库内的相对路径")

        operation = draft_input.operation.strip().lower() or "auto"
        if operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"operation 只支持：{', '.join(sorted(ALLOWED_OPERATIONS))}")

        intent = draft_input.intent.strip()
        new_content = _normalize_content(draft_input.new_content)
        if not intent:
            raise ValueError("intent 不能为空")
        if not new_content.strip():
            raise ValueError("new_content 不能为空")

        target_read = self.reader.read_file(target_file)
        current_content = target_read.get("content") or ""
        target_was_read = target_read.get("status") == "ok"
        resolved_operation = _resolve_operation(operation, target_was_read)
        proposed_content = _build_proposed_content(
            current_content=current_content,
            new_content=new_content,
            operation=resolved_operation,
        )
        diff_lines = list(
            difflib.unified_diff(
                current_content.splitlines(keepends=True),
                proposed_content.splitlines(keepends=True),
                fromfile=f"a/{target_file}",
                tofile=f"b/{target_file}",
                lineterm="",
            )
        )
        diff_truncated = len(diff_lines) > MAX_DIFF_LINES
        diff_preview = "\n".join(diff_lines[:MAX_DIFF_LINES])

        commit_subject = _commit_subject(intent, target_file, resolved_operation)
        pr_title = f"入库稿：{intent}"
        read_files = [_read_file_summary(target_read)]
        risk_notes = _risk_notes(target_read, resolved_operation)

        return {
            "status": "ok",
            "target_file": target_file,
            "operation": resolved_operation,
            "suggested_save_path": target_file,
            "read_files": read_files,
            "target_read": _read_file_summary(target_read),
            "markdown_body": new_content,
            "diff_summary": {
                "intent": intent,
                "target_was_read": target_was_read,
                "added_lines": _line_count(new_content),
                "proposed_total_lines": _line_count(proposed_content),
                "summary": _human_diff_summary(
                    target_file=target_file,
                    operation=resolved_operation,
                    target_was_read=target_was_read,
                    added_lines=_line_count(new_content),
                ),
            },
            "diff_preview": diff_preview,
            "diff_truncated": diff_truncated,
            "commit_message": commit_subject,
            "pr_title": pr_title,
            "pr_body": _pr_body(
                intent=intent,
                target_file=target_file,
                operation=resolved_operation,
                read_files=read_files,
                risk_notes=risk_notes,
            ),
            "risk_notes": risk_notes,
        }


def _normalize_repo_path(path: str) -> str:
    cleaned = (path or "").replace("\\", "/").strip().lstrip("/")
    if not cleaned:
        return ""
    pure_path = PurePosixPath(cleaned)
    if any(part in {"", ".", ".."} for part in pure_path.parts):
        return ""
    return str(pure_path)


def _normalize_content(content: str) -> str:
    normalized = (content or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if normalized:
        normalized += "\n"
    return normalized


def _resolve_operation(operation: str, target_was_read: bool) -> str:
    if operation != "auto":
        return operation
    return "append" if target_was_read else "create"


def _build_proposed_content(
    current_content: str,
    new_content: str,
    operation: str,
) -> str:
    if operation in {"create", "replace"}:
        return new_content
    if not current_content:
        return new_content
    separator = "\n" if current_content.endswith("\n\n") else "\n\n"
    if not current_content.endswith("\n"):
        separator = "\n\n"
    return f"{current_content}{separator}{new_content}"


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


def _line_count(content: str) -> int:
    if not content:
        return 0
    return len(content.splitlines())


def _human_diff_summary(
    target_file: str,
    operation: str,
    target_was_read: bool,
    added_lines: int,
) -> str:
    read_text = "目标文件本次读取成功" if target_was_read else "目标文件本次未读取到"
    if operation == "append":
        action = f"向 {target_file} 追加 {added_lines} 行入库内容"
    elif operation == "replace":
        action = f"用新增内容替换 {target_file} 的全文"
    else:
        action = f"按新增文件生成 {target_file}"
    return f"{read_text}；草稿建议{action}。"


def _risk_notes(target_read: dict[str, Any], operation: str) -> list[str]:
    notes: list[str] = []
    if target_read.get("status") != "ok":
        notes.append("目标文件本次未读取到，不等于文件不存在；入库前需要再次确认路径。")
    if operation == "replace":
        notes.append("replace 会替换目标文件全文，入库前必须人工复核完整 diff。")
    if operation == "create" and target_read.get("status") == "ok":
        notes.append("目标文件本次已读取到，但操作选择 create；请确认不是误覆盖已有文件。")
    return notes


def _commit_subject(intent: str, target_file: str, operation: str) -> str:
    prefix = "docs"
    if operation == "create":
        verb = "add"
    elif operation == "replace":
        verb = "replace"
    else:
        verb = "update"
    slug = _compact_text(intent)
    if slug:
        return f"{prefix}: {verb} {slug}"
    return f"{prefix}: {verb} {target_file}"


def _compact_text(value: str) -> str:
    compact = re.sub(r"\s+", " ", value.strip())
    return compact[:72].rstrip()


def _pr_body(
    intent: str,
    target_file: str,
    operation: str,
    read_files: list[dict[str, Any]],
    risk_notes: list[str],
) -> str:
    read_file_lines = [
        f"- `{item.get('path')}`：{item.get('status')} / {item.get('source') or 'unknown'}"
        for item in read_files
    ]
    risk_lines = [f"- {note}" for note in risk_notes] or ["- 未发现额外风险；仍需按 diff 人工复核。"]
    return "\n".join(
        [
            "## 变更意图",
            intent,
            "",
            "## 已读取文件",
            *read_file_lines,
            "",
            "## 建议修改",
            f"- 目标文件：`{target_file}`",
            f"- 操作方式：`{operation}`",
            "",
            "## 风险与复核",
            *risk_lines,
            "",
            "## 验证建议",
            "- 重新运行 `/repo/file?path=` 确认目标文件当前版本。",
            "- 人工检查 diff 后再提交到 SK 仓库。",
        ]
    )
