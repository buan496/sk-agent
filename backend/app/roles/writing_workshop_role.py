from __future__ import annotations

from app.roles.base_role import BaseRole, RoleContext, markdown_from_sections


class WritingWorkshopRole(BaseRole):
    role_id = "writing_workshop_role"
    role_name = "写作工坊"
    purpose = "把底稿改成公众号文章，优化结构、标题、开头、结尾和传播表达。"
    when_to_use = ["文章改写", "结构优化", "标题和传播表达"]
    required_inputs = ["draft_text"]
    required_read_files = []
    forbidden_actions = ["最终事实核查", "擅自改变核心判断", "把 X 级证据写成事实"]
    output_schema = ["title", "core_cut", "structure", "draft_markdown", "risks", "revision_notes"]
    system_prompt = "你是 SK 内部写作工坊角色。必须保留核心那一刀，不做最终事实核查。"

    def run(self, user_input: str, notes: str, context: RoleContext) -> dict:
        title = "待定标题：先保留核心判断"
        core_cut = "核心判断需要人工确认；写作角色只负责表达，不改变判断。"
        structure = ["开头抛问题", "中段展开证据和案例", "结尾回到行动建议"]
        risks = ["写作优化不能替代事实核查。", "X 级证据不能写成事实。"]
        revision_notes = ["保留原文关键判断", "标记需要证据的位置", "发布前交给文章发布检查角色"]
        draft_markdown = user_input.strip() or "未提供底稿。"
        structured = {
            "title": title,
            "core_cut": core_cut,
            "structure": structure,
            "draft_markdown": draft_markdown,
            "risks": risks,
            "revision_notes": revision_notes,
        }
        return self.role_result(
            context=context,
            conclusion="已生成写作改稿框架；事实判断仍需复核。",
            structured_output=structured,
            risks=risks,
            minimal_next_step="补证据后运行文章发布检查。",
            answer_markdown=markdown_from_sections(
                [
                    ("标题", title),
                    ("那一刀", core_cut),
                    ("结构", structure),
                    ("草稿", draft_markdown),
                    ("风险", risks),
                    ("修改说明", revision_notes),
                ]
            ),
        )
