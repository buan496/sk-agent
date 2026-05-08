from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.services.canonical_preflight import canonical_preflight, merge_read_files
from app.services.llm_client import (
    ChatMessage,
    LLMConfigurationError,
    get_llm_client,
)
from app.services.repo_reader import RepoReader
from app.services.retriever import Retriever
from app.services.status_auditor import StatusAuditor


MAX_CONTEXT_CHARS = 18000
MAX_DOC_CHARS = 5000

PRODUCT_TEMPLATE_PATHS = [
    "core/product-teardown-template.md",
    "content/article_template.md",
]
RED_TEAM_PATHS = [
    "core/项目审问清单.md",
    "core/产品评估决策清单.md",
    "core/failure_modes.yml",
    "core/SKILL-真实产品外部体检与机会推演SOP.md",
]
PUBLISH_CHECK_PATHS = [
    "content/公众号写作指南.md",
    "content/内容生产经验手册.md",
    "content/文章发布SOP.md",
    "content/article_template.md",
]


@dataclass(frozen=True)
class WorkflowInput:
    value: str
    notes: str = ""
    limit: int = 8
    preflight: dict[str, Any] | None = None


class SKWorkflowAgents:
    def __init__(
        self,
        settings: Settings,
        reader: RepoReader,
        retriever: Retriever | None = None,
    ) -> None:
        self.settings = settings
        self.reader = reader
        self.retriever = retriever or Retriever()

    def product_teardown(self, request: WorkflowInput) -> dict[str, Any]:
        product_name = request.value.strip()
        if not product_name:
            raise ValueError("product_name 不能为空")

        preflight = request.preflight or canonical_preflight(self.reader)
        canonical_read_files = preflight.get("read_files", [])
        status_audit = StatusAuditor(self.reader).audit(preflight=preflight)
        search_result = self._safe_search(
            f"{product_name} 产品 初拆 案例 case-card",
            limit=request.limit,
        )
        template_docs = self._read_documents(
            PRODUCT_TEMPLATE_PATHS,
            fallback_queries=["轻量初拆 模板", "product teardown template"],
        )
        search_files = self._read_search_files(search_result)
        read_files = merge_read_files(
            canonical_read_files,
            status_audit.get("read_files", []),
            template_docs["read_files"],
            search_files,
        )
        ingest_recommendation = _product_ingest_recommendation(product_name, search_result)
        prompt = _format_prompt(
            title="产品轻量初拆",
            instructions=[
                "先报告状态校准结果，再判断仓库是否已有相关内容。",
                "基于模板生成轻量初拆草稿。",
                "必须输出是否建议入库，以及建议保存路径。",
                "不确定就说不确定；找不到不能编。",
            ],
            user_input=f"产品名：{product_name}\n补充信息：{request.notes or '无'}",
            read_files=read_files,
            context_blocks=[
                _status_context(status_audit),
                _search_context(search_result),
                template_docs["context"],
            ],
        )
        completion = self._safe_chat(prompt, _fallback_product_teardown(product_name, ingest_recommendation))
        answer_markdown = completion["content"]
        return _agent_response(
            {
                "status": "ok",
                "agent": "product_teardown",
                "product_name": product_name,
                "read_files": read_files,
                "status_audit_summary": status_audit.get("summary"),
                "search": _compact_search(search_result),
                "ingest_recommendation": ingest_recommendation,
                "answer": answer_markdown,
                "llm": completion["llm"],
                "conclusion": _product_conclusion(ingest_recommendation, status_audit),
                "evidence": {
                    "status_audit": status_audit.get("summary"),
                    "search": _compact_search(search_result),
                    "template_paths": PRODUCT_TEMPLATE_PATHS,
                },
                "risks": _product_risks(status_audit, search_result),
                "minimal_next_step": _product_next_step(ingest_recommendation),
                "ingest_draft": ingest_recommendation,
                "answer_markdown": answer_markdown,
            }
        )

    def framework_red_team(self, request: WorkflowInput) -> dict[str, Any]:
        idea = request.value.strip()
        if not idea:
            raise ValueError("idea 不能为空")

        preflight = request.preflight or canonical_preflight(self.reader)
        canonical_read_files = preflight.get("read_files", [])
        search_result = self._safe_search(
            f"{idea} 项目审问 产品评估 failure_modes 失败模式",
            limit=request.limit,
        )
        docs = self._read_documents(
            RED_TEAM_PATHS,
            fallback_queries=["项目审问清单", "产品评估决策清单", "failure_modes"],
        )
        search_files = self._read_search_files(search_result)
        read_files = merge_read_files(canonical_read_files, docs["read_files"], search_files)
        prompt = _format_prompt(
            title="框架红队",
            instructions=[
                "读取项目审问清单、产品评估决策清单和 failure_modes 后再判断。",
                "输出反向排雷：最危险假设、失败路径、证伪实验、必须补证据。",
                "最后给出 Kill / Go / Hold 判断，并解释不确定性。",
                "不确定就说不确定；找不到不能编。",
            ],
            user_input=f"项目想法 / 产品方向：{idea}\n补充信息：{request.notes or '无'}",
            read_files=read_files,
            context_blocks=[docs["context"], _search_context(search_result)],
        )
        completion = self._safe_chat(prompt, _fallback_red_team(idea))
        answer_markdown = completion["content"]
        return _agent_response(
            {
                "status": "ok",
                "agent": "framework_red_team",
                "idea": idea,
                "read_files": read_files,
                "search": _compact_search(search_result),
                "answer": answer_markdown,
                "llm": completion["llm"],
                "conclusion": _first_non_empty_line(answer_markdown) or "Hold：需要更多证据后再判断。",
                "evidence": {
                    "search": _compact_search(search_result),
                    "required_paths": RED_TEAM_PATHS,
                },
                "risks": _workflow_risks(search_result, docs["read_files"]),
                "minimal_next_step": "补充目标用户、场景、替代方案和可验证证据；必要时再生成入库稿。",
                "ingest_draft": {
                    "required": False,
                    "reason": "框架红队输出先用于判断，入库前需要人工确认。",
                },
                "answer_markdown": answer_markdown,
            }
        )

    def article_publish_check(self, request: WorkflowInput) -> dict[str, Any]:
        article = request.value.strip()
        if not article:
            raise ValueError("final_article 不能为空")

        preflight = request.preflight or canonical_preflight(self.reader)
        canonical_read_files = preflight.get("read_files", [])
        docs = self._read_documents(
            PUBLISH_CHECK_PATHS,
            fallback_queries=["公众号写作指南", "内容生产经验手册", "文章发布SOP"],
        )
        search_result = self._safe_search("公众号写作指南 内容生产经验手册 发布 SOP", limit=request.limit)
        search_files = self._read_search_files(search_result)
        read_files = merge_read_files(canonical_read_files, docs["read_files"], search_files)
        prompt = _format_prompt(
            title="文章发布检查",
            instructions=[
                "读取写作指南、内容生产经验手册和发布 SOP 后再检查文章。",
                "输出风险检查、需要补证据的位置、标题/摘要建议和发布包。",
                "发布包至少包含：标题建议、导语、摘要、标签、发布前 checklist。",
                "不确定就说不确定；找不到不能编。",
            ],
            user_input=f"文章终稿：\n{article}\n\n补充信息：{request.notes or '无'}",
            read_files=read_files,
            context_blocks=[docs["context"], _search_context(search_result)],
        )
        completion = self._safe_chat(prompt, _fallback_publish_check(article))
        answer_markdown = completion["content"]
        return _agent_response(
            {
                "status": "ok",
                "agent": "article_publish_check",
                "article_length": len(article),
                "read_files": read_files,
                "search": _compact_search(search_result),
                "answer": answer_markdown,
                "llm": completion["llm"],
                "conclusion": _first_non_empty_line(answer_markdown) or "需要按发布 SOP 做人工复核。",
                "evidence": {
                    "search": _compact_search(search_result),
                    "required_paths": PUBLISH_CHECK_PATHS,
                },
                "risks": _workflow_risks(search_result, docs["read_files"]),
                "minimal_next_step": "按风险检查修订终稿，确认事实、案例状态和发布清单后再发布。",
                "ingest_draft": {
                    "required": False,
                    "reason": "发布检查结果不自动入库；如需入库，应走 /patch/draft 生成草稿。",
                },
                "answer_markdown": answer_markdown,
            }
        )

    def _safe_search(self, query: str, limit: int) -> dict[str, Any]:
        try:
            return self.retriever.search(query, limit=limit)
        except Exception as exc:
            return {
                "status": "error",
                "query": query,
                "message": str(exc),
                "read_files": [],
                "count": 0,
                "results": [],
            }

    def _read_documents(
        self,
        candidate_paths: list[str],
        fallback_queries: list[str],
    ) -> dict[str, Any]:
        docs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for path in candidate_paths:
            self._read_document_into(path, docs, seen)

        for query in fallback_queries:
            search = self._safe_search(query, limit=4)
            for path in search.get("read_files", []):
                self._read_document_into(path, docs, seen)

        return {
            "read_files": [_read_file_summary(doc["result"]) for doc in docs],
            "context": _documents_context(docs),
        }

    def _read_search_files(self, search_result: dict[str, Any]) -> list[dict[str, Any]]:
        read_files: list[dict[str, Any]] = []
        for path in search_result.get("read_files", [])[:8]:
            result = self.reader.read_file(path)
            read_files.append(_read_file_summary(result))
        return read_files

    def _read_document_into(
        self,
        path: str,
        docs: list[dict[str, Any]],
        seen: set[str],
    ) -> None:
        if path in seen:
            return
        seen.add(path)
        result = self.reader.read_file(path)
        docs.append({"path": path, "result": result})

    def _safe_chat(self, prompt: str, fallback: str) -> dict[str, Any]:
        try:
            completion = get_llm_client(self.settings).chat(
                [
                    ChatMessage(
                        role="system",
                        content=(
                            "你是 SK 仓库工作流 Agent。所有判断必须基于本次读取文件；"
                            "必须列出已读取文件；不确定就说不确定；不要输出思考过程。"
                        ),
                    ),
                    ChatMessage(role="user", content=prompt[:MAX_CONTEXT_CHARS]),
                ],
                max_completion_tokens=4096,
            )
            return {
                "content": completion["content"],
                "llm": {
                    "status": "ok",
                    "provider": completion["provider"],
                    "model": completion["model"],
                    "usage": completion["usage"],
                    "reasoning_present": completion["reasoning_present"],
                    "raw_finish_reason": completion["raw_finish_reason"],
                },
            }
        except (LLMConfigurationError, RuntimeError) as exc:
            return {
                "content": fallback,
                "llm": {
                    "status": "unavailable",
                    "message": str(exc),
                },
            }


def _format_prompt(
    title: str,
    instructions: list[str],
    user_input: str,
    read_files: list[dict[str, Any]],
    context_blocks: list[str],
) -> str:
    read_file_lines = [
        f"- {item.get('path')}：{item.get('status')} / {item.get('source') or 'unknown'}"
        for item in read_files
    ]
    return "\n".join(
        [
            f"# {title}",
            "",
            "## 工作规则",
            *[f"- {instruction}" for instruction in instructions],
            "",
            "## 已读取文件",
            *(read_file_lines or ["- 无"]),
            "",
            "## 用户输入",
            user_input,
            "",
            "## 仓库上下文",
            "\n\n---\n\n".join(block for block in context_blocks if block).strip() or "无",
            "",
            "## 输出格式",
            "结论",
            "已读取文件",
            "关键依据",
            "风险与不确定性",
            "建议入库稿 / 发布包 / 红队结论",
            "下一步执行指令",
        ]
    )


def _documents_context(docs: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for doc in docs:
        result = doc["result"]
        content = result.get("content") or ""
        if result.get("status") == "ok":
            body = content[:MAX_DOC_CHARS]
        else:
            body = result.get("message") or "本次未读取到"
        blocks.append(
            "\n".join(
                [
                    f"文件：{doc['path']}",
                    f"状态：{result.get('status')}",
                    body,
                ]
            )
        )
    return "\n\n".join(blocks)


def _status_context(status_audit: dict[str, Any]) -> str:
    conflicts = status_audit.get("conflicts", [])[:8]
    return "\n".join(
        [
            "状态审计摘要：",
            f"- risk_level: {status_audit.get('risk_level')}",
            f"- summary: {status_audit.get('summary')}",
            "冲突摘录：",
            *[
                f"- {item.get('check')} / {item.get('risk_level')} / {item.get('message')}"
                for item in conflicts
            ],
        ]
    )


def _search_context(search_result: dict[str, Any]) -> str:
    rows = []
    for hit in search_result.get("results", [])[:8]:
        rows.append(
            "\n".join(
                [
                    f"命中：{hit.get('file_path')}:{hit.get('start_line')}-{hit.get('end_line')}",
                    f"标题：{hit.get('heading') or ''}",
                    f"摘要：{hit.get('excerpt') or hit.get('content') or ''}",
                ]
            )
        )
    return "\n\n".join(rows)


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


def _agent_response(payload: dict[str, Any]) -> dict[str, Any]:
    answer_markdown = payload.get("answer_markdown") or payload.get("answer") or ""
    payload.setdefault("conclusion", _first_non_empty_line(answer_markdown) or "不确定")
    payload.setdefault("read_files", [])
    payload.setdefault("evidence", {})
    payload.setdefault("risks", [])
    payload.setdefault("minimal_next_step", "先人工复核本次读取文件和证据。")
    payload.setdefault(
        "ingest_draft",
        {"required": False, "reason": "未生成入库稿；如需入库，请走 /patch/draft。"},
    )
    payload["answer_markdown"] = answer_markdown
    payload.setdefault("answer", answer_markdown)
    return payload


def _first_non_empty_line(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip().strip("#").strip()
        if stripped and stripped not in {"结论", "已读取文件"}:
            return stripped
    return ""


def _product_conclusion(
    ingest_recommendation: dict[str, Any],
    status_audit: dict[str, Any],
) -> str:
    decision = ingest_recommendation.get("decision") or "unknown"
    risk_level = status_audit.get("risk_level") or "unknown"
    return f"入库判断：{decision}；状态审计风险：{risk_level}。"


def _product_risks(status_audit: dict[str, Any], search_result: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    conflict_count = int((status_audit.get("summary") or {}).get("conflict_count") or 0)
    if conflict_count:
        risks.append(f"状态审计发现 {conflict_count} 个冲突，入库前需要先校准。")
    if int(search_result.get("count") or 0):
        risks.append("仓库已有相关命中，入库前需要排重。")
    if not risks:
        risks.append("未发现阻断风险，但仍需人工复核事实和路径。")
    return risks


def _product_next_step(ingest_recommendation: dict[str, Any]) -> str:
    if ingest_recommendation.get("decision") == "check_duplicate":
        return "先读取检索命中文件做排重，确认不是重复内容后再生成 /patch/draft 入库稿。"
    return "使用 /patch/draft 生成可审核入库稿，不直接写入仓库。"


def _workflow_risks(
    search_result: dict[str, Any],
    required_read_files: list[dict[str, Any]],
) -> list[str]:
    risks: list[str] = []
    missing = [item.get("path") for item in required_read_files if item.get("status") != "ok"]
    if missing:
        risks.append(f"部分工作流参考文件本次未读取到：{', '.join(str(path) for path in missing)}")
    if search_result.get("status") == "error":
        risks.append(f"检索失败：{search_result.get('message')}")
    if int(search_result.get("count") or 0) == 0:
        risks.append("本次没有检索到可交叉验证的仓库片段。")
    if not risks:
        risks.append("未发现阻断风险，但结论仍以本次读取文件为准。")
    return risks


def _unique_read_files(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for item in group:
            path = str(item.get("path") or "")
            key = path or str(item)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _compact_search(search_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": search_result.get("status"),
        "query": search_result.get("query"),
        "mode": search_result.get("mode"),
        "count": search_result.get("count"),
        "read_files": search_result.get("read_files", []),
        "results": [
            {
                "file_path": hit.get("file_path"),
                "heading": hit.get("heading"),
                "start_line": hit.get("start_line"),
                "end_line": hit.get("end_line"),
                "total_score": hit.get("total_score"),
                "excerpt": hit.get("excerpt"),
            }
            for hit in search_result.get("results", [])[:8]
        ],
    }


def _product_ingest_recommendation(product_name: str, search_result: dict[str, Any]) -> dict[str, Any]:
    count = int(search_result.get("count") or 0)
    if count == 0:
        return {
            "decision": "suggest_draft",
            "reason": f"本次没有检索到与 {product_name} 直接相关的仓库片段，可先生成轻量初拆草稿。",
            "suggested_path": f"cases/2026/{_slugify(product_name)}-teardown.md",
        }
    return {
        "decision": "check_duplicate",
        "reason": f"本次检索到 {count} 个相关片段，入库前需要先排重和确认是否补充已有文件。",
        "suggested_path": f"cases/2026/{_slugify(product_name)}-teardown.md",
    }


def _slugify(value: str) -> str:
    ascii_slug = "".join(char.lower() if char.isalnum() and char.isascii() else "-" for char in value)
    ascii_slug = "-".join(part for part in ascii_slug.split("-") if part)
    return ascii_slug or "new-product"


def _fallback_product_teardown(product_name: str, recommendation: dict[str, Any]) -> str:
    return "\n".join(
        [
            "结论",
            "MiniMax 当前不可用，已返回规则版轻量初拆骨架。请在模型可用后重新生成完整稿。",
            "",
            "已读取文件",
            "见接口 read_files 字段。",
            "",
            "建议入库判断",
            f"- decision: {recommendation['decision']}",
            f"- suggested_path: {recommendation['suggested_path']}",
            f"- reason: {recommendation['reason']}",
            "",
            "轻量初拆骨架",
            f"# {product_name} 轻量初拆",
            "",
            "## 一句话判断",
            "不确定，需要补充产品定位、目标用户、核心场景和已有证据。",
            "",
            "## 必补信息",
            "- 产品官网 / 入口",
            "- 目标用户",
            "- 高频场景",
            "- 收费方式",
            "- 可验证的增长或失败信号",
        ]
    )


def _fallback_red_team(idea: str) -> str:
    return "\n".join(
        [
            "结论",
            "MiniMax 当前不可用，已返回规则版红队骨架。Kill / Go 判断暂定为 Hold。",
            "",
            "已读取文件",
            "见接口 read_files 字段。",
            "",
            "反向排雷",
            f"- 方向：{idea}",
            "- 最危险假设：用户痛点、付费意愿、分发路径、替代方案优势均未被证实。",
            "- 证伪实验：先访谈目标用户，再做最小 landing / demo 验证真实行为。",
            "",
            "Kill / Go 判断",
            "Hold：证据不足，不建议直接投入重开发。",
        ]
    )


def _fallback_publish_check(article: str) -> str:
    title = article.splitlines()[0].strip("# ").strip() if article.splitlines() else "未命名文章"
    return "\n".join(
        [
            "结论",
            "MiniMax 当前不可用，已返回规则版发布检查骨架。",
            "",
            "已读取文件",
            "见接口 read_files 字段。",
            "",
            "风险检查",
            "- 需要人工确认事实、引用、案例状态和发布状态。",
            "- 需要检查标题、导语、结尾行动指令是否完整。",
            "",
            "发布包",
            f"- 标题建议：{title}",
            "- 摘要：待模型生成或人工补写。",
            "- 标签：SK、产品观察、案例拆解",
            "- 发布前 checklist：事实核对、错别字检查、链接检查、封面检查、状态表更新。",
        ]
    )
