from __future__ import annotations

from app.roles.base_role import BaseRole, RoleContext, markdown_from_sections
from app.services.evidence_classifier import web_result_to_evidence


class DeepResearcherRole(BaseRole):
    role_id = "deep_researcher_role"
    role_name = "深度研究员"
    purpose = "补齐外部事实证据、产品基本面、创始人原话、竞品、用户反馈和市场证据。"
    when_to_use = ["需要外部事实证据", "需要证据等级", "需要确认未找到的信息"]
    required_inputs = ["research_question_or_product"]
    required_read_files = []
    forbidden_actions = ["宣布入库", "替代状态审计", "把未验证输出当事实"]
    output_schema = [
        "conclusion",
        "evidence_ledger",
        "missing_evidence",
        "risks",
        "recommended_next_research",
        "answer_markdown",
    ]
    system_prompt = "你是 SK 内部深度研究员角色。输出证据等级候选，不替代人工复核。"

    def run(self, user_input: str, notes: str, context: RoleContext) -> dict:
        claim = user_input.strip() or "未提供研究对象"
        web_results = context.web_results or []
        evidence_ledger = (
            [web_result_to_evidence(claim, item) for item in web_results]
            if web_results
            else [
                {
                    "claim": claim,
                    "source_title": "",
                    "source_url": "",
                    "source_type": "unknown",
                    "evidence_level": "X_candidate",
                    "confidence": 0.0,
                    "fetched_at": None,
                    "note": "allow_web=false 或搜索失败；当前只形成外部证据缺口清单。",
                }
            ]
        )
        missing_evidence = [
            "创始人原话",
            "用户反馈",
            "竞品对照",
            "市场证据",
            "可引用来源链接",
        ]
        risks = [
            "联网结果只是候选证据，不能视为事实或 SK 当前状态。",
            "候选证据不能自动入库，仍需人工复核。",
        ]
        next_research = [
            "核查候选来源是否为原始来源或官方来源",
            "将可用证据交给 patch draft 生成可审核入库稿",
        ]
        conclusion = (
            "已补入候选外部证据；仍不能替代人工复核。"
            if web_results
            else "需要外部证据补齐；当前只形成研究清单。"
        )
        structured = {
            "conclusion": conclusion,
            "evidence_ledger": evidence_ledger,
            "missing_evidence": missing_evidence,
            "risks": risks,
            "recommended_next_research": next_research,
            "warnings": context.web_warnings or [],
        }
        return self.role_result(
            context=context,
            conclusion=conclusion,
            structured_output=structured,
            risks=risks,
            minimal_next_step="先复核候选证据来源，再决定是否生成入库稿。",
            answer_markdown=markdown_from_sections(
                [
                    ("结论", conclusion),
                    ("证据账本", evidence_ledger),
                    ("缺失证据", missing_evidence),
                    ("风险", risks),
                    ("下一步研究", next_research),
                ]
            ),
        )
