from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.indexer import _is_sk_content_path


client = TestClient(app)


def test_memory_core_returns_core_memory_and_constitution() -> None:
    response = client.get("/memory/core")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "canonical files" in payload["core_memory"].lower()
    assert "Human review" in payload["constitution"]


def test_memory_registries_returns_expected_files() -> None:
    response = client.get("/memory/registries")

    assert response.status_code == 200
    payload = response.json()
    assert "repo_qa_agent" in payload["agent_registry"]
    assert "深度研究员" in payload["gpts_registry"]
    assert "Codex" in payload["external_tools"]


def test_external_run_can_be_written_and_listed() -> None:
    response = client.post(
        "/memory/external-run",
        json={
            "agent_type": "gpts",
            "agent_name": "深度研究员",
            "task_type": "external_research",
            "input_summary": "Research a product for SK intake.",
            "output_summary": "Candidate evidence collected; not ingested.",
            "source_link_or_file": "https://example.com/research",
            "related_sk_files": ["cases/2026/case-index.md"],
            "status": "reviewed",
            "should_ingest": True,
            "ingested": False,
            "notes": "Phase 9.2 test record.",
        },
    )

    assert response.status_code == 200
    created = response.json()["run"]
    assert created["agent_type"] == "gpts"
    assert created["ingested"] is False
    assert created["related_sk_files"] == ["cases/2026/case-index.md"]

    list_response = client.get("/memory/external-runs?limit=20")
    assert list_response.status_code == 200
    runs = list_response.json()["runs"]
    assert any(item["id"] == created["id"] for item in runs)


def test_external_runs_do_not_affect_canonical_preflight() -> None:
    response = client.get("/repo/canonical")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 4
    assert payload["canonical_files"] == [
        "README.md",
        "ops/执行状态总表.md",
        "cases/2026/case-index.md",
        "cases/2026/case-cards.md",
    ]


def test_memory_files_do_not_enter_sk_content_index() -> None:
    assert _is_sk_content_path("memory/core_memory.md") is False
    assert _is_sk_content_path("memory/episodes/drift-log.md") is False
    assert _is_sk_content_path("README.md") is True
