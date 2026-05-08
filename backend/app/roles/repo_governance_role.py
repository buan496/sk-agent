from __future__ import annotations

from app.roles.base_role import BaseRole, RoleContext, markdown_from_sections
from app.services.status_auditor import StatusAuditor


class RepoGovernanceRole(BaseRole):
    role_id = "repo_governance_role"
    role_name = "仓库治理副驾"
    purpose = "任务路由、状态漂移判断、SK/SKGPT 双仓边界和仓库维护建议。"
    when_to_use = ["状态治理", "任务路由", "双仓边界", "维护建议"]
    required_inputs = ["governance_question"]
    required_read_files = []
    forbidden_actions = ["直接写仓库", "越过人工确认", "忽略冲突"]
    output_schema = [
        "conclusion",
        "current_state",
        "conflicts",
        "risks",
        "recommended_files_to_update",
        "minimal_next_step",
        "codex_or_cursor_instruction",
    ]
    system_prompt = "你是 SK 工作台副驾角色。有冲突先指出冲突，不直接写仓库。"

    def run(self, user_input: str, notes: str, context: RoleContext) -> dict:
        audit = StatusAuditor(context.reader).audit(preflight=context.preflight)
        conflicts = audit.get("conflicts", [])
        risks = audit.get("risks", []) or ["未发现明确状态冲突。"]
        recommended = audit.get("suggested_files", [])
        conclusion = audit.get("conclusion", "需要先读取 canonical files 后判断。")
        minimal = audit.get("minimal_next_step") or "先处理状态审计中的最小修复项。"
        instruction = audit.get("codex_instruction") or "仅生成草稿，不直接写 SK 仓库。"
        structured = {
            "conclusion": conclusion,
            "current_state": audit.get("summary", {}),
            "conflicts": conflicts,
            "risks": risks,
            "recommended_files_to_update": recommended,
            "minimal_next_step": minimal,
            "codex_or_cursor_instruction": instruction,
        }
        return self.role_result(
            context=context,
            conclusion=conclusion,
            structured_output=structured,
            risks=risks,
            minimal_next_step=minimal,
            answer_markdown=markdown_from_sections(
                [
                    ("结论", conclusion),
                    ("当前状态", audit.get("summary", {})),
                    ("冲突", [item.get("message") for item in conflicts] or ["无明确冲突"]),
                    ("风险", risks),
                    ("建议修改文件", recommended),
                    ("执行指令", instruction),
                ]
            ),
        )
