from __future__ import annotations

from typing import Any

from app.config import Settings
from app.services.llm_client import ChatMessage, get_llm_client
from app.services.repo_reader import RepoReader
from app.services.retriever import Retriever


SYSTEM_PROMPT = """你是 SK 仓库 Agent 工作台。
回答规则：
1. 必须基于给定的仓库片段回答。
2. 必须先列出“已读取文件”。
3. 必须引用路径和行号。
4. 不确定就说不确定。
5. 找不到不能编。
6. 不要输出思考过程。"""


class QAService:
    def __init__(self, settings: Settings, reader: RepoReader) -> None:
        self.settings = settings
        self.reader = reader
        self.retriever = Retriever()

    def ask(self, question: str, limit: int = 8) -> dict[str, Any]:
        search_result = self.retriever.search(question, limit=limit)
        hits = search_result.get("results", [])
        read_files = self._verify_current_files(search_result.get("read_files", []))
        read_ok_paths = [item["path"] for item in read_files if item["status"] == "ok"]

        if not hits:
            return {
                "status": "no_context",
                "question": question,
                "answer": "已读取文件：无。\n\n本次检索没有找到可支撑回答的仓库片段，因此不确定，不能编。",
                "read_files": read_files,
                "search": search_result,
            }

        context = _format_context(hits)
        user_prompt = f"""问题：{question}

本次检索并读取到的文件：
{chr(10).join(f"- {path}" for path in read_ok_paths) or "- 无"}

仓库片段：
{context}

请按以下格式回答：
结论
已读取文件
依据
不确定项
"""

        client = get_llm_client(self.settings)
        completion = client.chat(
            [
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ],
            max_completion_tokens=4096,
        )
        return {
            "status": "ok",
            "question": question,
            "answer": completion["content"],
            "read_files": read_files,
            "citations": [
                {
                    "file_path": hit["file_path"],
                    "start_line": hit["start_line"],
                    "end_line": hit["end_line"],
                    "heading": hit["heading"],
                }
                for hit in hits
            ],
            "search": search_result,
            "llm": {
                "provider": completion["provider"],
                "model": completion["model"],
                "usage": completion["usage"],
                "reasoning_present": completion["reasoning_present"],
                "raw_finish_reason": completion["raw_finish_reason"],
            },
        }

    def _verify_current_files(self, paths: list[str]) -> list[dict[str, Any]]:
        verified: list[dict[str, Any]] = []
        for path in paths[:8]:
            result = self.reader.read_file(path)
            file_meta = result.get("file") or {}
            verified.append(
                {
                    "path": path,
                    "status": result.get("status"),
                    "source": file_meta.get("source") or result.get("source"),
                    "size": file_meta.get("size"),
                    "last_modified": file_meta.get("last_modified"),
                }
            )
        return verified


def _format_context(hits: list[dict[str, Any]]) -> str:
    blocks = []
    for index, hit in enumerate(hits, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[{index}] {hit['file_path']}:{hit['start_line']}-{hit['end_line']}",
                    f"heading: {hit.get('heading') or ''}",
                    hit["content"],
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)
