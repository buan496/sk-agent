from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_cognitive_think_creates_session_and_tracks_entity() -> None:
    response = client.post(
        "/cognitive/think",
        json={"input": "MYHAIR AI 会不会最后变成卖药渠道？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["session"]["id"]
    assert payload["current_topic"] == "MYHAIR AI"
    assert payload["entities"]
    assert payload["research_object"]["slug"] == "myhair-ai"
    assert payload["read_files"]
    assert "卖药" in " ".join(payload["unresolved_questions"])


def test_cognitive_thought_continuity_without_explicit_carryover() -> None:
    first = client.post(
        "/cognitive/think",
        json={"input": "Hippocratic AI 和 MYHAIR AI 都像诊断入口。"},
    ).json()
    session_id = first["session"]["id"]

    second_response = client.post(
        "/cognitive/think",
        json={"session_id": session_id, "input": "那它的信任冲突在哪里？"},
    )

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["session"]["id"] == session_id
    assert second["judgment_evolution"]
    assert len(second["judgment_evolution"]) >= 2
    assert any("信任" in risk for risk in second["risks"])
    assert second["messages"]


def test_cognitive_state_can_be_read() -> None:
    created = client.post(
        "/cognitive/think",
        json={"input": "ListenLabs 可能和反馈回路有关。"},
    ).json()

    response = client.get(f"/cognitive/sessions/{created['session']['id']}/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["session"]["id"] == created["session"]["id"]
    assert payload["entities"]
    assert payload["judgment_evolution"]


def test_cognitive_sessions_can_be_listed() -> None:
    response = client.get("/cognitive/sessions?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "sessions" in payload


def test_cognitive_web_operator_can_be_disabled_by_default(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("RoleRouter should not run when allow_web is false")

    monkeypatch.setattr("app.cognitive.cognitive_session.RoleRouter", fail_if_called)
    response = client.post(
        "/cognitive/think",
        json={"input": "Supermemory 这个产品先做一个判断。", "allow_web": False},
    )

    assert response.status_code == 200
    assert response.json()["operator_used"] is None
