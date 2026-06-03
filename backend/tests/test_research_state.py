from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.roles.role_router import create_internal_role_run


client = TestClient(app)


def _slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_research_object_can_be_created_and_listed() -> None:
    slug = _slug("myhair")
    response = client.post(
        "/research/objects",
        json={"name": "MYHAIR AI", "slug": slug, "notes": "test object"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"]["slug"] == slug

    list_response = client.get("/research/objects?limit=20")
    assert list_response.status_code == 200
    assert any(item["slug"] == slug for item in list_response.json()["objects"])


def test_candidate_source_updates_research_state() -> None:
    slug = _slug("source")
    client.post("/research/objects", json={"name": "Source Test", "slug": slug})

    response = client.post(
        f"/research/objects/{slug}/sources",
        json={
            "url": "https://example.com/product",
            "title": "Example Product",
            "source_type": "official",
            "source_reason": "domain matches product official site",
        },
    )

    assert response.status_code == 200
    source = response.json()["source"]
    assert source["source_type"] == "official"
    assert source["evidence_level"] == "A_candidate"

    state_response = client.get(f"/research/objects/{slug}/state")
    assert state_response.status_code == 200
    state = state_response.json()["state"]
    assert state["counts"]["sources"] == 1
    assert state["sources"][0]["url"] == "https://example.com/product"
    assert "Research state cannot override SK canonical files." in state["risks"]


def test_read_source_into_state_extracts_candidate_facts(monkeypatch) -> None:
    slug = _slug("read")
    client.post("/research/objects", json={"name": "Read Test", "slug": slug})
    monkeypatch.setattr(
        "app.services.research_state.read_source",
        lambda url, source_type, max_chars: {
            "status": "ok",
            "url": url,
            "source_type": source_type,
            "title": "Readable Source",
            "clean_text": "Readable clean text",
            "metadata": {"description": "AI product description"},
            "extracted_facts": ["Official site describes AI product features."],
            "candidate_claims": [
                {
                    "claim": "The product has AI product features.",
                    "supporting_source": url,
                    "confidence": 0.62,
                }
            ],
            "source_quotes": ["A source quote for manual review."],
        },
    )

    response = client.post(
        f"/research/objects/{slug}/read-source",
        json={"url": "https://example.com/product", "source_type": "official"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["read_status"] == "read"
    assert payload["facts_added"]

    state = client.get(f"/research/objects/{slug}/state").json()["state"]
    assert state["counts"]["read_sources"] == 1
    assert state["counts"]["facts"] >= 1
    assert any("AI product" in fact["fact_text"] for fact in state["facts"])


def test_internal_role_run_can_be_ingested_into_research_state() -> None:
    slug = _slug("run")
    client.post("/research/objects", json={"name": "Run Test", "slug": slug})
    run = create_internal_role_run(
        {
            "role_id": "deep_researcher_role",
            "role_name": "Deep Researcher",
            "task_type": "deep_research",
            "input_summary": "Run Test",
            "read_files": [],
            "structured_output": {
                "evidence_ledger": [
                    {
                        "claim": "Official source candidate found.",
                        "source_title": "Official",
                        "source_url": "https://example.com",
                        "source_type": "official",
                        "source_reason": "domain matches product official site",
                        "evidence_level": "A_candidate",
                        "confidence": 0.78,
                    }
                ],
                "source_readings": [
                    {
                        "status": "ok",
                        "url": "https://example.com",
                        "source_type": "official",
                        "title": "Official",
                        "clean_text": "Official text",
                        "metadata": {},
                        "extracted_facts": ["Official page is readable."],
                        "candidate_claims": [],
                        "source_quotes": [],
                    }
                ],
            },
            "conclusion": "Candidate sources found.",
            "risks": [],
            "minimal_next_step": "Review candidate source.",
            "answer_markdown": "Candidate sources found.",
        }
    )

    response = client.post(
        f"/research/objects/{slug}/ingest-role-run",
        json={"run_id": run["id"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_count"] >= 1
    assert payload["fact_count"] >= 1

    state = client.get(f"/research/objects/{slug}/state").json()["state"]
    assert state["counts"]["sources"] >= 1
    assert state["counts"]["facts"] >= 1
