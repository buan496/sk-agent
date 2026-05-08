from __future__ import annotations

from app.roles.base_role import BaseRole, RoleContext, markdown_from_sections


class FirstReaderRole(BaseRole):
    role_id = "first_reader_role"
    role_name = "第一读者"
    purpose = "以陌生读者视角审稿，判断是否读得懂、是否有兴趣、是否有传播钩子。"
    when_to_use = ["读者视角审稿", "传播钩子检查", "找无聊和困惑点"]
    required_inputs = ["article_draft"]
    required_read_files = []
    forbidden_actions = ["事实核查", "直接改正文", "宣布入库"]
    output_schema = [
        "reader_reaction",
        "confusing_points",
        "boring_points",
        "strongest_hook",
        "weakest_part",
        "risks",
        "minimal_next_step",
    ]
    system_prompt = "你是 SK 内部第一读者角色，只输出读者视角风险。"

    def run(self, user_input: str, notes: str, context: RoleContext) -> dict:
        reader_reaction = "能判断主题，但需要更明确的开头钩子和读者收益。"
        confusing_points = ["核心对象、结论和证据链需要更早出现。"]
        boring_points = ["如果连续讲流程，传播张力会下降。"]
        strongest_hook = "先读仓库再判断，比普通聊天更可靠。"
        weakest_part = "缺少一个让陌生读者立刻理解问题严重性的例子。"
        risks = ["这不是事实核查结果。", "不应直接改正文或宣布可发布。"]
        minimal = "补一个具体例子，再交给写作工坊或发布检查。"
        structured = {
            "reader_reaction": reader_reaction,
            "confusing_points": confusing_points,
            "boring_points": boring_points,
            "strongest_hook": strongest_hook,
            "weakest_part": weakest_part,
            "risks": risks,
            "minimal_next_step": minimal,
            "ingest_draft": {"required": False, "reason": "第一读者反馈不是入库稿。"},
        }
        return self.role_result(
            context=context,
            conclusion=reader_reaction,
            structured_output=structured,
            risks=risks,
            minimal_next_step=minimal,
            answer_markdown=markdown_from_sections(
                [
                    ("读者反应", reader_reaction),
                    ("困惑点", confusing_points),
                    ("无聊点", boring_points),
                    ("最强钩子", strongest_hook),
                    ("最弱部分", weakest_part),
                    ("风险", risks),
                    ("最小下一步", minimal),
                ]
            ),
        )
