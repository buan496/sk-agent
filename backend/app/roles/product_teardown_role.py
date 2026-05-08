from __future__ import annotations

from app.roles.base_role import BaseRole, RoleContext, markdown_from_sections
from app.services.evidence_classifier import web_result_to_evidence
from app.services.retriever import Retriever


class ProductTeardownRole(BaseRole):
    role_id = "product_teardown_role"
    role_name = "产品初拆"
    purpose = "产品轻量初拆，判断是否值得进入标准 10 维度拆解或深度研究。"
    when_to_use = ["产品初拆", "入库前排重", "判断是否需要深度研究"]
    required_inputs = ["product_name"]
    required_read_files = ["core/product-teardown-template.md", "content/article_template.md"]
    forbidden_actions = ["跳过排重", "不读 canonical files", "直接宣布入库"]
    output_schema = [
        "conclusion",
        "read_files",
        "duplicate_check",
        "teardown_summary",
        "evidence_ledger",
        "risks",
        "minimal_next_step",
        "ingest_draft",
    ]
    system_prompt = "你是 SK 内部产品初拆角色。必须先排重、读 canonical files，不直接宣布入库。"

    def run(self, user_input: str, notes: str, context: RoleContext) -> dict:
        product_name = user_input.strip() or "未命名产品"
        docs = self.read_required_files(context)
        search = Retriever().search(f"{product_name} 产品 初拆 案例 case-card", limit=6)
        duplicate_count = int(search.get("count") or 0)
        duplicate_check = {
            "status": "possible_duplicate" if duplicate_count else "no_direct_match",
            "match_count": duplicate_count,
            "matched_files": search.get("read_files", []),
        }
        evidence_ledger = [
            web_result_to_evidence(f"{product_name} 产品基本面 / 定价 / 竞品 / 最新状态", item)
            for item in (context.web_results or [])
        ]
        missing_evidence = [
            "官方产品页面",
            "定价页面",
            "融资或公司背景",
            "竞品列表",
            "近期用户反馈",
        ]
        risks = []
        if duplicate_count:
            risks.append("仓库已有相关命中，入库前必须排重。")
        risks.append("初拆不是入库许可，需要人工复核。")
        if evidence_ledger:
            risks.append("联网证据只是候选材料，不能覆盖 canonical files。")
        ingest_draft = {
            "required": False,
            "suggested_path": f"cases/2026/{_slugify(product_name)}-teardown.md",
            "reason": "先排重和复核候选证据，再决定是否生成 patch draft。",
        }
        teardown_summary = {
            "product": product_name,
            "notes": notes,
            "decision": "hold_for_duplicate_check" if duplicate_count else "candidate_for_light_teardown",
        }
        conclusion = (
            "先排重，暂不直接入库。"
            if duplicate_count
            else "可作为轻量初拆候选，仍需人工复核。"
        )
        structured = {
            "conclusion": conclusion,
            "duplicate_check": duplicate_check,
            "teardown_summary": teardown_summary,
            "evidence_ledger": evidence_ledger,
            "missing_evidence": missing_evidence,
            "risks": risks,
            "minimal_next_step": "读取命中文件并确认是否已有底稿 / 案例卡。",
            "ingest_draft": ingest_draft,
            "warnings": context.web_warnings or [],
        }
        return self.role_result(
            context=context,
            conclusion=conclusion,
            structured_output=structured,
            risks=risks,
            minimal_next_step="读取命中文件并确认是否已有底稿 / 案例卡。",
            answer_markdown=markdown_from_sections(
                [
                    ("结论", conclusion),
                    ("排重", duplicate_check),
                    ("初拆摘要", teardown_summary),
                    ("证据账本", evidence_ledger),
                    ("缺失证据", missing_evidence),
                    ("风险", risks),
                    ("入库草稿", ingest_draft),
                ]
            ),
            read_files=docs,
            should_ingest=False,
        )


def _slugify(value: str) -> str:
    ascii_slug = "".join(char.lower() if char.isalnum() and char.isascii() else "-" for char in value)
    ascii_slug = "-".join(part for part in ascii_slug.split("-") if part)
    return ascii_slug or "new-product"
