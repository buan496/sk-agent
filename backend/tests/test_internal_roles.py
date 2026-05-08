from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import CANONICAL_FILES
from app.main import app


client = TestClient(app)


def test_roles_run_deep_research_returns_role_and_structured_fields() -> None:
    response = client.post(
        "/roles/run",
        json={
            "task_type": "deep_research",
            "input": "Research Example Product",
            "notes": "",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role_id"] == "deep_researcher_role"
    assert "evidence_ledger" in payload["structured_output"]
    assert "missing_evidence" in payload["structured_output"]


def test_roles_run_product_teardown_contains_canonical_read_files() -> None:
    response = client.post(
        "/roles/run",
        json={
            "task_type": "product_teardown",
            "input": "Example Product",
            "notes": "test",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["path"] for item in payload["read_files"][:4]] == CANONICAL_FILES


def test_roles_run_first_reader_does_not_require_ingest_draft() -> None:
    response = client.post(
        "/roles/run",
        json={
            "task_type": "first_reader",
            "input": "# Draft\n\nThis is a draft.",
            "notes": "",
        },
    )

    assert response.status_code == 200
    structured = response.json()["structured_output"]
    assert structured["ingest_draft"]["required"] is False


def test_internal_role_runs_can_be_read() -> None:
    response = client.get("/roles/runs?limit=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "runs" in payload


def test_internal_role_memory_and_docs_exist() -> None:
    assert _project_file("memory/internal_roles.md").exists()
    assert _project_file("docs/internal-role-system.md").exists()


def test_internal_roles_cannot_bypass_canonical_preflight() -> None:
    response = client.post(
        "/roles/run",
        json={
            "task_type": "first_reader",
            "input": "Reader check.",
            "notes": "",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["path"] for item in payload["read_files"][:4]] == CANONICAL_FILES


def test_patch_writer_role_is_draft_only() -> None:
    response = client.post(
        "/roles/run",
        json={
            "task_type": "patch_draft",
            "input": '{"target_file":"docs/test-role-draft.md","intent":"test draft","new_content":"# Test\\n\\nDraft only."}',
            "notes": "",
        },
    )

    assert response.status_code == 200
    structured = response.json()["structured_output"]
    assert structured["action_status"] == "draft_only_no_commit_no_push_no_pr"
    assert "commit_message" in structured
    assert "pr_body" in structured


def _project_file(relative_path: str) -> Path:
    mounted = Path("/") / relative_path
    if mounted.exists():
        return mounted
    return Path(__file__).resolve().parents[2] / relative_path
