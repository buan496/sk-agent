from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.skgpt import get_skgpt_reader
from app.config import Settings, get_settings
from app.main import app
from app.roles.role_prompt_loader import RolePromptLoader
from app.services.skgpt_reader import SKGPTReader


client = TestClient(app)


def test_skgpt_reader_reads_local_instruction_file(tmp_path: Path) -> None:
    prompt = tmp_path / "instructions" / "deep-researcher.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("# 深度研究员\n\n证据优先。", encoding="utf-8")

    reader = SKGPTReader(Settings(skgpt_repo_local_path=str(tmp_path)))
    result = reader.read_file("instructions/deep-researcher.md")

    assert result["status"] == "ok"
    assert result["path"] == "instructions/deep-researcher.md"
    assert "证据优先" in result["content"]
    assert result["source"] == "local_skgpt"


def test_role_prompt_loader_maps_skgpt_prompt_to_internal_role(tmp_path: Path) -> None:
    skgpt_root = tmp_path / "skgpt"
    prompt = skgpt_root / "instructions" / "deep-researcher.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("深度研究员指令", encoding="utf-8")

    mapping = tmp_path / "role_prompt_mapping.yml"
    mapping.write_text(
        "\n".join(
            [
                "deep_research_role:",
                "  source_repo: SKGPT",
                '  prompt_path: "instructions/deep-researcher.md"',
                "  fallback_prompt_path: null",
            ]
        ),
        encoding="utf-8",
    )

    loader = RolePromptLoader(
        settings=Settings(skgpt_repo_local_path=str(skgpt_root)),
        mapping_path=mapping,
    )
    result = loader.load_prompt_for_role("deep_research_role")

    assert result["status"] == "ok"
    assert result["role_id"] == "deep_researcher_role"
    assert result["prompt"]["content"] == "深度研究员指令"


def test_skgpt_api_lists_files_without_using_sk_repo(tmp_path: Path) -> None:
    prompt = tmp_path / "instructions" / "first-reader.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("第一读者指令", encoding="utf-8")

    app.dependency_overrides[get_skgpt_reader] = lambda: SKGPTReader(
        Settings(skgpt_repo_local_path=str(tmp_path))
    )
    try:
        response = client.get("/skgpt/files")
    finally:
        app.dependency_overrides.pop(get_skgpt_reader, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "local_skgpt"
    assert payload["files"][0]["path"] == "instructions/first-reader.md"


def test_role_prompt_api_uses_memory_mapping_and_skgpt_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    skgpt_root = tmp_path / "skgpt"
    prompt = skgpt_root / "instructions" / "writing-workshop.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("写作工坊指令", encoding="utf-8")

    memory_root = tmp_path / "memory"
    memory_root.mkdir()
    (memory_root / "role_prompt_mapping.yml").write_text(
        "\n".join(
            [
                "writing_workshop_role:",
                "  source_repo: SKGPT",
                '  prompt_path: "instructions/writing-workshop.md"',
                "  fallback_prompt_path: null",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MEMORY_DIR", str(memory_root))
    app.dependency_overrides[get_settings] = lambda: Settings(
        skgpt_repo_local_path=str(skgpt_root)
    )
    try:
        response = client.get("/skgpt/role-prompts")
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["principle"].startswith("SKGPT 只作为角色指令来源")
    assert payload["prompts"][0]["role_id"] == "writing_workshop_role"
    assert payload["prompts"][0]["prompt"]["content"] == "写作工坊指令"
