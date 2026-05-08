from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import CANONICAL_FILES
from app.config import Settings
from app.main import app
from app.services.evidence_classifier import candidate_level_for_source
from app.services.web_search import search_web


client = TestClient(app)


def test_web_search_mock_provider_returns_results() -> None:
    response = client.post("/web/search", json={"query": "Luffu pricing founder quote", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["results"]
    assert {"title", "url", "snippet", "source_type", "fetched_at", "provider"} <= set(
        payload["results"][0]
    )


def test_tavily_failure_falls_back_to_mock(monkeypatch) -> None:
    def broken_tavily(*args, **kwargs):
        raise RuntimeError("tavily unavailable")

    monkeypatch.setattr("app.services.search_providers.tavily_provider.TavilySearchProvider.search", broken_tavily)
    payload = search_web(
        query="Example Product official pricing",
        limit=3,
        settings=Settings(web_search_provider="tavily", tavily_api_key="test-key"),
    )

    assert payload["provider"] == "mock"
    assert payload["warnings"]
    assert payload["results"]


def test_tavily_provider_is_used_when_key_exists(monkeypatch) -> None:
    def fake_tavily(self, query: str, limit: int):
        from app.services.search_providers.base import SearchResult, fetched_now

        return [
            SearchResult(
                title="Real provider result",
                url="https://example.gov/product",
                snippet="official candidate",
                source_type="official",
                fetched_at=fetched_now(),
                provider="tavily",
            )
        ]

    monkeypatch.setattr("app.services.search_providers.tavily_provider.TavilySearchProvider.search", fake_tavily)
    payload = search_web(
        query="Example Product official pricing",
        limit=3,
        settings=Settings(web_search_provider="tavily", tavily_api_key="test-key"),
    )

    assert payload["provider"] == "tavily"
    assert payload["results"][0]["provider"] == "tavily"
    assert payload["results"][0]["source_type"] == "official"


def test_allow_web_false_deep_research_does_not_call_web_search(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("web search should not be called")

    monkeypatch.setattr("app.roles.role_router.search_web", fail_if_called)
    response = client.post(
        "/roles/run",
        json={"task_type": "deep_research", "input": "Example Product", "allow_web": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["web_used"] is False
    assert payload["web_results_count"] == 0


def test_allow_web_true_deep_research_calls_web_search(monkeypatch) -> None:
    calls: list[str] = []

    def fake_search_web(query: str, limit: int, settings):
        calls.append(query)
        return {
            "query": query,
            "provider": "test",
            "results": [
                {
                    "title": "Community result",
                    "url": "https://example.com/community",
                    "snippet": "candidate",
                    "source_type": "community",
                    "fetched_at": "2026-05-08T12:00:00+08:00",
                    "provider": "test",
                }
            ],
        }

    monkeypatch.setattr("app.roles.role_router.search_web", fake_search_web)
    response = client.post(
        "/roles/run",
        json={
            "task_type": "deep_research",
            "input": "Example Product",
            "allow_web": True,
            "web_queries": ["Example Product official pricing"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert calls == ["Example Product official pricing"]
    assert payload["web_used"] is True
    assert payload["web_results_count"] == 1
    assert payload["evidence_ledger"][0]["source_url"] == "https://example.com/community"
    assert "human_readable_markdown" in payload
    assert "当前判断" in payload["human_readable_markdown"]
    assert "Community result" in payload["human_readable_markdown"]
    assert "{'claim'" not in payload["human_readable_markdown"]


def test_non_web_role_ignores_allow_web(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("web search should not be called")

    monkeypatch.setattr("app.roles.role_router.search_web", fail_if_called)
    response = client.post(
        "/roles/run",
        json={"task_type": "first_reader", "input": "Draft", "allow_web": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["web_used"] is False
    assert payload["warnings"]
    assert "不允许联网" in payload["warnings"][0]


def test_community_and_unknown_are_not_a_candidates() -> None:
    assert candidate_level_for_source("community") != "A_candidate"
    assert candidate_level_for_source("unknown") == "X_candidate"


def test_roles_run_still_contains_canonical_read_files_with_web(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.roles.role_router.search_web",
        lambda query, limit, settings: {"query": query, "provider": "test", "results": []},
    )
    response = client.post(
        "/roles/run",
        json={"task_type": "product_teardown", "input": "Example Product", "allow_web": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["path"] for item in payload["read_files"][:4]] == CANONICAL_FILES


def test_search_failure_does_not_break_role_output(monkeypatch) -> None:
    def broken_search(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("app.roles.role_router.search_web", broken_search)
    response = client.post(
        "/roles/run",
        json={"task_type": "article_publish_check", "input": "Final article", "allow_web": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role_id"] == "article_publish_check_role"
    assert payload["warnings"]
    assert payload["read_files"]
