from __future__ import annotations

from app.roles.base_role import BaseRole, RoleContext, markdown_from_sections
from app.services.evidence_classifier import web_result_to_evidence


class ArticlePublishCheckRole(BaseRole):
    role_id = "article_publish_check_role"
    role_name = "文章发布检查"
    purpose = "核查文章终稿中的关键事实、数据、产品现状和发布风险。"
    when_to_use = ["文章发布前检查", "事实核查", "产品现状复核"]
    required_inputs = ["final_article"]
    required_read_files = [
        "content/article_template.md",
        "content/公众号写作指南.md",
        "content/文章发布SOP.md",
    ]
    forbidden_actions = ["直接发布", "自动入库", "把候选联网证据写成事实"]
    output_schema = [
        "conclusion",
        "read_files",
        "evidence_ledger",
        "missing_evidence",
        "risks",
        "minimal_next_step",
    ]
    system_prompt = "你是 SK 文章发布检查角色。你只做发布前风险检查，不自动发布或入库。"

    def run(self, user_input: str, notes: str, context: RoleContext) -> dict:
        docs = self.read_required_files(context)
        article_summary = (user_input or "").strip()[:300]
        evidence_ledger = [
            web_result_to_evidence("文章关键事实 / 数据 / 产品现状核查", item)
            for item in (context.web_results or [])
        ]
        missing_evidence = [
            "文章中每个产品现状的官方来源",
            "关键数据的原始出处",
            "创始人或公司原话出处",
            "发布时间敏感信息的最新确认",
        ]
        risks = [
            "发布检查不能替代最终事实核查。",
            "联网结果只是候选证据，不能覆盖 canonical files。",
            "不能自动发布、自动入库或自动更新 SK 仓库。",
        ]
        conclusion = (
            "已补入候选联网证据；仍需人工确认后才能发布。"
            if evidence_ledger
            else "未联网或未取得外部证据；只能输出发布前证据缺口。"
        )
        structured = {
            "conclusion": conclusion,
            "article_summary": article_summary,
            "evidence_ledger": evidence_ledger,
            "missing_evidence": missing_evidence,
            "risks": risks,
            "minimal_next_step": "逐条核对关键事实来源，再决定是否进入发布包。",
            "warnings": context.web_warnings or [],
        }
        return self.role_result(
            context=context,
            conclusion=conclusion,
            structured_output=structured,
            risks=risks,
            minimal_next_step="逐条核对关键事实来源，再决定是否进入发布包。",
            answer_markdown=markdown_from_sections(
                [
                    ("结论", conclusion),
                    ("证据账本", evidence_ledger),
                    ("缺失证据", missing_evidence),
                    ("风险", risks),
                    ("最小下一步", "逐条核对关键事实来源，再决定是否进入发布包。"),
                ]
            ),
            read_files=docs,
            should_ingest=False,
        )
