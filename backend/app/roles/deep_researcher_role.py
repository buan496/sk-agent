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
        if context.carryover_intent and context.context_used:
            return _run_carryover_report(self, user_input, context)

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
                    "source_reason": "unclassified source",
                    "evidence_level": "X_candidate",
                    "confidence": 0.0,
                    "fetched_at": None,
                    "note": "allow_web=false 或搜索失败；当前只形成外部证据缺口清单。",
                }
            ]
        )
        missing_evidence = _missing_evidence_from_sources(evidence_ledger)
        extracted_facts = _facts_from_source_readings(context.source_readings or [])
        candidate_claims = _claims_from_source_readings(context.source_readings or [])
        source_quotes = _quotes_from_source_readings(context.source_readings or [])
        risks = [
            "联网结果只是候选证据，不能视为事实或 SK 当前状态。",
            "候选证据不能自动入库，仍需人工复核。",
        ]
        next_research = [
            "优先打开 official / app_store / company_profile 来源核查原文。",
            "将可用证据交给 patch draft 生成可审核入库稿。",
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
            "source_readings": context.source_readings or [],
            "extracted_facts": extracted_facts,
            "candidate_claims": candidate_claims,
            "source_quotes": source_quotes,
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
                    ("正文提取事实", extracted_facts),
                    ("候选断言", candidate_claims),
                    ("来源摘录", source_quotes),
                    ("缺失证据", missing_evidence),
                    ("风险", risks),
                    ("下一步研究", next_research),
                ]
            ),
        )


def _missing_evidence_from_sources(evidence_ledger: list[dict]) -> list[str]:
    source_types = {str(item.get("source_type") or "") for item in evidence_ledger}
    missing: list[str] = []
    if "official" in source_types:
        missing.append("产品官网 / 功能说明：已有候选官网来源，需打开原文复核。")
    else:
        missing.append("产品官网 / 功能说明：仍缺官方来源。")

    if "app_store" in source_types:
        missing.append("用户反馈：部分可补，Google Play / App Store 评论可进一步读取。")
    else:
        missing.append("用户反馈：仍缺应用商店、社区或访谈来源。")

    if "company_profile" in source_types:
        missing.append("公司资料：已有 LinkedIn / Crunchbase 等候选，公司规模和融资需复核。")
    else:
        missing.append("公司资料：仍缺 LinkedIn / Crunchbase / PitchBook 等候选来源。")

    missing.extend(
        [
            "创始人原话：仍需原始访谈、官网 About、新闻稿或公开视频。",
            "竞品对照：仍需单独检索竞品与替代方案。",
            "市场证据：仍需行业报告、客户案例或可信媒体来源。",
        ]
    )
    return missing


def _facts_from_source_readings(readings: list[dict]) -> list[str]:
    facts: list[str] = []
    for reading in readings:
        facts.extend(str(item) for item in reading.get("extracted_facts", []) if item)
    return facts[:12]


def _claims_from_source_readings(readings: list[dict]) -> list[dict]:
    claims: list[dict] = []
    for reading in readings:
        claims.extend(item for item in reading.get("candidate_claims", []) if isinstance(item, dict))
    return claims[:12]


def _quotes_from_source_readings(readings: list[dict]) -> list[dict]:
    quotes: list[dict] = []
    for reading in readings:
        url = reading.get("url")
        for quote in reading.get("source_quotes", [])[:3]:
            quotes.append({"source_url": url, "quote": quote})
    return quotes[:12]


def _run_carryover_report(role: DeepResearcherRole, user_input: str, context: RoleContext) -> dict:
    inherited = context.carryover_context or {}
    previous_structured = inherited.get("structured_output") or {}
    evidence_ledger = previous_structured.get("evidence_ledger") or []
    missing_evidence = previous_structured.get("missing_evidence") or _missing_evidence_from_sources(evidence_ledger)
    grouped_sources = _group_sources(evidence_ledger)
    product_functions = _product_functions_from_sources(grouped_sources)
    next_questions = [
        "官网功能描述是否能对应真实用户场景？",
        "App Store / Google Play 的评论里是否出现稳定痛点？",
        "LinkedIn / Crunchbase 等公司资料是否能交叉验证团队、融资、增长阶段？",
        "是否存在独立媒体或客户案例支持产品价值？",
        "哪些信息仍只来自社区或不明来源，应该剔除或降权？",
    ]
    unreliable_filter = [
        "unknown 来源只保留为线索，不进入事实判断。",
        "community 来源只能代表用户声音候选，不能当作公司事实。",
        "company_profile 来源需要与官网、新闻稿或公司披露交叉复核。",
    ]
    risks = [
        "本轮使用上一轮候选来源，没有重新联网。",
        "继承上下文不是 SK 当前状态，不能自动入库。",
    ]
    conclusion = "已基于上一轮候选来源整理研究简报；没有重新联网。"
    structured = {
        "conclusion": conclusion,
        "evidence_ledger": evidence_ledger,
        "candidate_sources": grouped_sources,
        "product_functions": product_functions,
        "missing_evidence": missing_evidence,
        "next_research_questions": next_questions,
        "unreliable_source_filter": unreliable_filter,
        "risks": risks,
        "warnings": context.web_warnings or [],
    }
    return role.role_result(
        context=context,
        conclusion=conclusion,
        structured_output=structured,
        risks=risks,
        minimal_next_step="打开 official / app_store / company_profile 来源原文，逐条确认可引用事实。",
        answer_markdown=markdown_from_sections(
            [
                ("结论", conclusion),
                ("产品功能", product_functions),
                ("已有候选证据", grouped_sources),
                ("仍缺证据", missing_evidence),
                ("下一步研究问题", next_questions),
                ("不可靠来源剔除建议", unreliable_filter),
            ]
        ),
    )


def _group_sources(evidence_ledger: list[dict]) -> dict[str, list[dict]]:
    groups = {
        "官网 / 产品页": [],
        "App Store / Google Play": [],
        "LinkedIn / Crunchbase": [],
        "媒体报道": [],
        "社区评论": [],
        "未分类来源": [],
    }
    for item in evidence_ledger:
        source_type = item.get("source_type")
        slim = {
            "title": item.get("source_title"),
            "url": item.get("source_url"),
            "evidence_level": item.get("evidence_level"),
            "source_reason": item.get("source_reason"),
        }
        if source_type == "official":
            groups["官网 / 产品页"].append(slim)
        elif source_type == "app_store":
            groups["App Store / Google Play"].append(slim)
        elif source_type == "company_profile":
            groups["LinkedIn / Crunchbase"].append(slim)
        elif source_type == "media":
            groups["媒体报道"].append(slim)
        elif source_type == "community":
            groups["社区评论"].append(slim)
        else:
            groups["未分类来源"].append(slim)
    return groups


def _product_functions_from_sources(grouped_sources: dict[str, list[dict]]) -> list[str]:
    functions: list[str] = []
    for item in grouped_sources.get("官网 / 产品页", [])[:5]:
        title = item.get("title") or "官网候选页面"
        functions.append(f"官网候选功能线索：{title}")
    for item in grouped_sources.get("App Store / Google Play", [])[:3]:
        title = item.get("title") or "应用商店候选页面"
        functions.append(f"应用商店功能 / 用户反馈线索：{title}")
    return functions or ["上一轮候选来源中尚未形成明确产品功能，需要打开原文进一步提取。"]
