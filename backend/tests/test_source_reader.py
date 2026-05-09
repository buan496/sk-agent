from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.source_reader import read_source


client = TestClient(app)


HTML = """
<html>
  <head>
    <title>MyHair AI</title>
    <meta name="description" content="AI hair analysis and personalized hair care recommendations.">
  </head>
  <body>
    <script>ignore()</script>
    <h1>AI hair analysis</h1>
    <p>MyHair uses AI to analyze hair type and provide personalized recommendations.</p>
    <p>Rating 4.6 stars from 1,200 reviews. Updated May 2026.</p>
  </body>
</html>
"""


def test_source_reader_extracts_official_text(monkeypatch) -> None:
    monkeypatch.setattr("app.services.source_reader._fetch_url", lambda url: HTML)

    result = read_source("https://myhair.ai", "official")

    assert result["status"] == "ok"
    assert result["title"] == "MyHair AI"
    assert "AI hair analysis" in result["clean_text"]
    assert result["metadata"]["description"].startswith("AI hair analysis")
    assert result["extracted_facts"]


def test_source_reader_extracts_app_store_metadata(monkeypatch) -> None:
    monkeypatch.setattr("app.services.source_reader._fetch_url", lambda url: HTML)

    result = read_source("https://play.google.com/store/apps/details?id=test", "app_store")

    assert result["status"] == "ok"
    assert result["metadata"]["rating"] == "4.6"
    assert result["metadata"]["review_count"] == "1,200"
    assert any("rating" in item.lower() for item in result["extracted_facts"])


def test_read_source_api(monkeypatch) -> None:
    monkeypatch.setattr("app.services.source_reader._fetch_url", lambda url: HTML)

    response = client.post(
        "/web/read-source",
        json={"url": "https://myhair.ai", "source_type": "official"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "MyHair AI"
    assert "clean_text" in payload


def test_deep_research_can_read_top_sources(monkeypatch) -> None:
    monkeypatch.setattr("app.roles.role_router.read_source", lambda url, source_type, max_chars: {
        "status": "ok",
        "url": url,
        "source_type": source_type,
        "title": "Readable source",
        "clean_text": "Readable source text",
        "metadata": {"description": "Readable description"},
        "extracted_facts": [f"{source_type} fact"],
        "candidate_claims": [{"claim": f"{source_type} fact", "supporting_source": url, "confidence": 0.55}],
        "source_quotes": ["Readable quote from source."],
    })
    monkeypatch.setattr("app.roles.role_router.search_web", lambda query, limit, settings: {
        "query": query,
        "provider": "test",
        "results": [
            {
                "title": "Official",
                "url": "https://myhair.ai",
                "snippet": "official",
                "source_type": "official",
                "source_reason": "domain matches product official site",
                "fetched_at": "2026-05-09T09:00:00+08:00",
                "provider": "test",
            },
            {
                "title": "App",
                "url": "https://play.google.com/store/apps/details?id=test",
                "snippet": "app",
                "source_type": "app_store",
                "source_reason": "Google Play app listing",
                "fetched_at": "2026-05-09T09:00:00+08:00",
                "provider": "test",
            },
        ],
    })

    response = client.post(
        "/roles/run",
        json={
            "task_type": "deep_research",
            "input": "MYHAIR AI",
            "allow_web": True,
            "read_sources": True,
            "web_queries": ["myhair.ai official"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_reading_used"] is True
    assert payload["read_sources_count"] == 2
    assert "extracted_facts" in payload["structured_output"]
    assert payload["extracted_facts"]
