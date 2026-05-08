from __future__ import annotations

import json
from typing import Any

from app.roles.base_role import BaseRole, RoleContext, markdown_from_sections
from app.services.patch_writer import PatchDraftInput, PatchWriter


class PatchWriterRole(BaseRole):
    role_id = "patch_writer_role"
    role_name = "入库稿生成器"
    purpose = "生成可审核入库稿、diff preview、commit message 和 PR body。"
    when_to_use = ["需要 patch draft", "需要 PR 草稿", "需要可审核入库材料"]
    required_inputs = ["target_file", "intent", "new_content"]
    required_read_files = []
    forbidden_actions = ["commit", "push", "自动 PR", "自动写 SK 仓库"]
    output_schema = [
        "suggested_path",
        "markdown_body",
        "diff_preview",
        "commit_message",
        "pr_title",
        "pr_body",
        "risks",
    ]
    system_prompt = "你是 SK 内部入库稿生成器，只生成草稿，不 commit、不 push、不自动 PR。"

    def run(self, user_input: str, notes: str, context: RoleContext) -> dict:
        parsed = _parse_patch_input(user_input, notes)
        draft = PatchWriter(context.reader).draft(
            PatchDraftInput(
                target_file=parsed["target_file"],
                intent=parsed["intent"],
                new_content=parsed["new_content"],
                operation=parsed["operation"],
            )
        )
        risks = draft.get("risk_notes", []) or ["仍需人工复核 diff 后再入库。"]
        structured = {
            "suggested_path": draft.get("suggested_save_path"),
            "markdown_body": draft.get("markdown_body"),
            "diff_preview": draft.get("diff_preview"),
            "commit_message": draft.get("commit_message"),
            "pr_title": draft.get("pr_title"),
            "pr_body": draft.get("pr_body"),
            "risks": risks,
            "action_status": "draft_only_no_commit_no_push_no_pr",
        }
        conclusion = f"已生成草稿：{draft.get('suggested_save_path')}"
        return self.role_result(
            context=context,
            conclusion=conclusion,
            structured_output=structured,
            risks=risks,
            minimal_next_step="人工审核 diff_preview、Markdown 正文、commit message 和 PR body。",
            answer_markdown=markdown_from_sections(
                [
                    ("结论", conclusion),
                    ("建议路径", draft.get("suggested_save_path")),
                    ("风险", risks),
                    ("commit message", draft.get("commit_message")),
                    ("PR title", draft.get("pr_title")),
                ]
            ),
            read_files=draft.get("read_files", []),
            should_ingest=True,
            ingested=False,
        )


def _parse_patch_input(user_input: str, notes: str) -> dict[str, Any]:
    try:
        parsed = json.loads(user_input)
        if isinstance(parsed, dict):
            return {
                "target_file": parsed.get("target_file") or "docs/role-draft.md",
                "intent": parsed.get("intent") or "生成内部角色入库稿草案",
                "new_content": parsed.get("new_content") or notes or user_input,
                "operation": parsed.get("operation") or "auto",
            }
    except json.JSONDecodeError:
        pass
    return {
        "target_file": "docs/role-draft.md",
        "intent": "生成内部角色入库稿草案",
        "new_content": user_input or notes or "# Draft\n\n待补充。",
        "operation": "auto",
    }
