from __future__ import annotations

from app.config import get_settings
from app.roles.base_role import BaseRole
from app.roles.article_publish_check_role import ArticlePublishCheckRole
from app.roles.deep_researcher_role import DeepResearcherRole
from app.roles.first_reader_role import FirstReaderRole
from app.roles.patch_writer_role import PatchWriterRole
from app.roles.product_teardown_role import ProductTeardownRole
from app.roles.role_prompt_loader import RolePromptLoader
from app.roles.repo_governance_role import RepoGovernanceRole
from app.roles.writing_workshop_role import WritingWorkshopRole


def role_registry() -> dict[str, BaseRole]:
    roles: list[BaseRole] = [
        DeepResearcherRole(),
        WritingWorkshopRole(),
        FirstReaderRole(),
        ProductTeardownRole(),
        ArticlePublishCheckRole(),
        RepoGovernanceRole(),
        PatchWriterRole(),
    ]
    return {role.role_id: role for role in roles}


def role_metadata() -> list[dict]:
    metadata = [role.metadata() for role in role_registry().values()]
    try:
        prompt_mapping = RolePromptLoader(settings=get_settings()).load_mapping()
    except Exception:
        prompt_mapping = {}

    for item in metadata:
        prompt_config = prompt_mapping.get(item["role_id"])
        item["prompt_source"] = {
            "source_repo": "SKGPT",
            "status": "configured" if prompt_config else "not_configured",
            "prompt_path": prompt_config.get("prompt_path") if prompt_config else None,
            "last_modified": None,
            "commit_hash": None,
            "message": "调用 /skgpt/role-prompts 可读取实际 SKGPT 指令内容"
            if prompt_config
            else None,
        }
    return metadata
