from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import CANONICAL_FILES, Settings
from app.main import app
from app.services.sk_workflow_agents import SKWorkflowAgents, WorkflowInput


class FakeReader:
    def __init__(self) -> None:
        self.files = {
            **{path: "" for path in CANONICAL_FILES},
            "core/product-teardown-template.md": "# Template\n",
            "content/article_template.md": "# Article Template\n",
            "core/项目审问清单.md": "# Questions\n",
            "core/产品评估决策清单.md": "# Decision\n",
            "core/failure_modes.yml": "FM001: risk\n",
            "core/SKILL-真实产品外部体检与机会推演SOP.md": "# SOP\n",
            "content/公众号写作指南.md": "# Guide\n",
            "content/内容生产经验手册.md": "# Handbook\n",
            "content/文章发布SOP.md": "# Publish SOP\n",
        }

    def read_file(self, path: str) -> dict:
        if path not in self.files:
            return {
                "status": "not_found",
                "path": path,
                "source": "fake",
                "message": "本次未读取到，文件未读取到不等于文件不存在",
                "file": None,
                "content": None,
            }
        content = self.files[path]
        return {
            "status": "ok",
            "path": path,
            "content": content,
            "file": {
                "path": path,
                "size": len(content.encode("utf-8")),
                "last_modified": None,
                "source": "fake",
            },
        }

    def read_canonical_files(self) -> dict:
        files = [self.read_file(path) for path in CANONICAL_FILES]
        return {
            "status": "ok",
            "canonical_files": CANONICAL_FILES,
            "read_count": len(files),
            "total": len(files),
            "files": files,
        }


class FakeRetriever:
    def search(self, query: str, limit: int = 10) -> dict:
        return {
            "status": "ok",
            "query": query,
            "mode": "keyword",
            "read_files": ["core/failure_modes.yml"],
            "count": 1,
            "results": [
                {
                    "file_path": "core/failure_modes.yml",
                    "heading": "FM001",
                    "content": "FM001: risk",
                    "excerpt": "FM001: risk",
                    "start_line": 1,
                    "end_line": 1,
                    "total_score": 10,
                }
            ],
        }


def test_product_teardown_returns_fallback_without_llm_key() -> None:
    service = SKWorkflowAgents(
        settings=Settings(minimax_api_key=""),
        reader=FakeReader(),  # type: ignore[arg-type]
        retriever=FakeRetriever(),  # type: ignore[arg-type]
    )

    result = service.product_teardown(WorkflowInput(value="Example Product"))

    assert result["status"] == "ok"
    assert result["agent"] == "product_teardown"
    assert result["llm"]["status"] == "unavailable"
    assert result["ingest_recommendation"]["decision"] == "check_duplicate"
    assert result["read_files"]


def test_framework_red_team_returns_hold_fallback() -> None:
    service = SKWorkflowAgents(
        settings=Settings(minimax_api_key=""),
        reader=FakeReader(),  # type: ignore[arg-type]
        retriever=FakeRetriever(),  # type: ignore[arg-type]
    )

    result = service.framework_red_team(WorkflowInput(value="AI product idea"))

    assert result["status"] == "ok"
    assert result["agent"] == "framework_red_team"
    assert "Hold" in result["answer"]


def test_article_publish_check_returns_publish_package_fallback() -> None:
    service = SKWorkflowAgents(
        settings=Settings(minimax_api_key=""),
        reader=FakeReader(),  # type: ignore[arg-type]
        retriever=FakeRetriever(),  # type: ignore[arg-type]
    )

    result = service.article_publish_check(WorkflowInput(value="# Title\n\nBody"))

    assert result["status"] == "ok"
    assert result["agent"] == "article_publish_check"
    assert "发布包" in result["answer"]


def test_product_teardown_api_rejects_empty_product_name() -> None:
    client = TestClient(app)

    response = client.post("/agents/product-teardown", json={"product_name": ""})

    assert response.status_code == 422
