from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.skgpt_reader import SKGPTReader


ROLE_ID_ALIASES = {
    "deep_research_role": "deep_researcher_role",
}


class RolePromptLoader:
    def __init__(
        self,
        settings: Settings,
        reader: SKGPTReader | None = None,
        mapping_path: Path | None = None,
    ) -> None:
        self.settings = settings
        self.reader = reader or SKGPTReader(settings)
        self.mapping_path = mapping_path or _memory_root() / "role_prompt_mapping.yml"

    def load_mapping(self) -> dict[str, dict[str, Any]]:
        if not self.mapping_path.exists():
            return {}
        return _parse_simple_yaml_mapping(self.mapping_path.read_text(encoding="utf-8"))

    def load_prompt_for_role(self, role_id: str) -> dict[str, Any]:
        mapping = self.load_mapping()
        normalized_role_id = _normalize_role_id(role_id)
        config = _lookup_role_config(mapping, normalized_role_id)
        if not config:
            return {
                "role_id": normalized_role_id,
                "status": "not_configured",
                "message": "未在 memory/role_prompt_mapping.yml 中配置此角色的 SKGPT 指令来源",
                "prompt": None,
            }

        source_repo = str(config.get("source_repo") or "").strip()
        if source_repo.upper() != "SKGPT":
            return {
                "role_id": normalized_role_id,
                "status": "unsupported_source",
                "source_repo": source_repo,
                "message": "当前阶段只允许从 SKGPT 读取角色指令",
                "prompt": None,
            }

        prompt_path = str(config.get("prompt_path") or "").strip()
        fallback_path = str(config.get("fallback_prompt_path") or "").strip()
        prompt = self.reader.read_file(prompt_path) if prompt_path else _empty_prompt_result()
        if prompt.get("status") != "ok" and fallback_path:
            prompt = self.reader.read_file(fallback_path)

        return {
            "role_id": normalized_role_id,
            "source_repo": "SKGPT",
            "prompt_path": prompt_path,
            "fallback_prompt_path": fallback_path or None,
            "status": "ok" if prompt.get("status") == "ok" else "unread",
            "message": None if prompt.get("status") == "ok" else prompt.get("message"),
            "prompt": {
                "path": prompt.get("path"),
                "content": prompt.get("content"),
                "source": prompt.get("source"),
                "last_modified": prompt.get("last_modified"),
                "commit_hash": prompt.get("commit_hash"),
            }
            if prompt.get("status") == "ok"
            else None,
        }

    def load_all_prompts(self) -> list[dict[str, Any]]:
        mapping = self.load_mapping()
        role_ids = sorted({_normalize_role_id(role_id) for role_id in mapping})
        return [self.load_prompt_for_role(role_id) for role_id in role_ids]


def _lookup_role_config(mapping: dict[str, dict[str, Any]], normalized_role_id: str) -> dict[str, Any] | None:
    for role_id, config in mapping.items():
        if _normalize_role_id(role_id) == normalized_role_id:
            return config
    return None


def _normalize_role_id(role_id: str) -> str:
    return ROLE_ID_ALIASES.get(role_id, role_id)


def _empty_prompt_result() -> dict[str, Any]:
    return {
        "status": "not_configured",
        "message": "prompt_path 为空",
        "content": None,
        "path": None,
    }


def _parse_simple_yaml_mapping(content: str) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    current_key = ""
    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith((" ", "\t")) and raw_line.rstrip().endswith(":"):
            current_key = raw_line.strip().rstrip(":")
            mapping[current_key] = {}
            continue
        if current_key and ":" in raw_line:
            key, value = raw_line.strip().split(":", 1)
            mapping[current_key][key.strip()] = _parse_scalar(value.strip())
    return mapping


def _parse_scalar(value: str) -> Any:
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _memory_root() -> Path:
    configured = os.getenv("MEMORY_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "memory"
