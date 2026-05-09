from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.conversation_intent import is_carryover_intent


client = TestClient(app)


def test_carryover_intent_detection() -> None:
    assert is_carryover_intent("基于以上候选来源，整理 MYHAIR AI")
    assert is_carryover_intent("继续总结刚才结果")
    assert not is_carryover_intent("研究 MYHAIR AI 的产品功能")


def test_carryover_with_conversation_id_does_not_call_web_search(monkeypatch) -> None:
    def fake_search_web(query: str, limit: int, settings):
        return {
            "query": query,
            "provider": "test",
            "results": [
                {
                    "title": "MYHAIR AI official",
                    "url": "https://myhair.ai",
                    "snippet": "AI hair analysis",
                    "source_type": "official",
                    "source_reason": "domain matches product official site",
                    "fetched_at": "2026-05-09T09:00:00+08:00",
                    "provider": "test",
                },
                {
                    "title": "MYHAIR AI LinkedIn",
                    "url": "https://www.linkedin.com/company/myhair-ai",
                    "snippet": "company profile",
                    "source_type": "company_profile",
                    "source_reason": "company profile database",
                    "fetched_at": "2026-05-09T09:00:00+08:00",
                    "provider": "test",
                },
            ],
        }

    monkeypatch.setattr("app.roles.role_router.search_web", fake_search_web)
    first = client.post(
        "/roles/run",
        json={
            "task_type": "deep_research",
            "input": "MYHAIR AI",
            "allow_web": True,
            "web_queries": ["myhair.ai official"],
        },
    )
    assert first.status_code == 200
    run_id = first.json()["run_id"]

    def fail_if_called(*args, **kwargs):
        raise AssertionError("web search should not be called on carryover")

    monkeypatch.setattr("app.roles.role_router.search_web", fail_if_called)
    second = client.post(
        "/roles/run",
        json={
            "conversation_id": str(run_id),
            "task_type": "deep_research",
            "input": "基于以上候选来源，整理 MYHAIR AI 的产品功能、证据缺口、下一步研究问题",
            "allow_web": True,
        },
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["carryover_intent"] is True
    assert payload["context_used"] is True
    assert payload["new_web_search_performed"] is False
    assert payload["inherited_sources_count"] == 2
    assert "product_functions" in payload["structured_output"]
    assert "candidate_sources" in payload["structured_output"]


def test_carryover_without_context_warns_and_does_not_search(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("web search should not be called without carryover context")

    monkeypatch.setattr("app.roles.role_router.search_web", fail_if_called)
    response = client.post(
        "/roles/run",
        json={
            "task_type": "deep_research",
            "input": "基于以上候选来源，整理 MYHAIR AI",
            "allow_web": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["carryover_intent"] is True
    assert payload["context_used"] is False
    assert payload["new_web_search_performed"] is False
    assert payload["inherited_sources_count"] == 0
    assert payload["warnings"]
