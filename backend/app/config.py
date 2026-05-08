from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


CANONICAL_FILES = [
    "README.md",
    "ops/执行状态总表.md",
    "cases/2026/case-index.md",
    "cases/2026/case-cards.md",
]


@dataclass(frozen=True)
class Settings:
    app_name: str = "SK Agent Workbench"
    local_repo_path: str = ""
    github_repo: str = ""
    github_branch: str = "main"
    github_token: str = ""
    github_raw_base_url: str = ""
    database_url: str = ""
    llm_provider: str = "minimax"
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.io/v1"
    minimax_chat_model: str = "MiniMax-M2.7"
    minimax_chat_endpoint: str = "/chat/completions"
    minimax_temperature: float = 0.2
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "sk_agent_neo4j"
    repo_sync_url: str = "https://github.com/MRYGP/SK.git"
    repo_sync_path: str = "/repo-cache/SK"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        local_repo_path=os.getenv("LOCAL_REPO_PATH", "").strip(),
        github_repo=os.getenv("GITHUB_REPO", "").strip(),
        github_branch=os.getenv("GITHUB_BRANCH", "main").strip() or "main",
        github_token=os.getenv("GITHUB_TOKEN", "").strip(),
        github_raw_base_url=os.getenv("GITHUB_RAW_BASE_URL", "").strip().rstrip("/"),
        database_url=os.getenv("DATABASE_URL", "").strip()
        or _build_database_url_from_parts(),
        llm_provider=os.getenv("LLM_PROVIDER", "minimax").strip() or "minimax",
        minimax_api_key=os.getenv("MINIMAX_API_KEY", "").strip(),
        minimax_base_url=os.getenv(
            "MINIMAX_BASE_URL",
            "https://api.minimax.io/v1",
        )
        .strip()
        .rstrip("/"),
        minimax_chat_model=os.getenv("MINIMAX_CHAT_MODEL", "MiniMax-M2.7").strip()
        or "MiniMax-M2.7",
        minimax_chat_endpoint=os.getenv(
            "MINIMAX_CHAT_ENDPOINT",
            "/chat/completions",
        ).strip()
        or "/chat/completions",
        minimax_temperature=float(os.getenv("MINIMAX_TEMPERATURE", "0.2")),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687").strip()
        or "bolt://neo4j:7687",
        neo4j_user=os.getenv("NEO4J_USER", "neo4j").strip() or "neo4j",
        neo4j_password=os.getenv("NEO4J_PASSWORD", "sk_agent_neo4j").strip()
        or "sk_agent_neo4j",
        repo_sync_url=os.getenv(
            "REPO_SYNC_URL",
            "https://github.com/MRYGP/SK.git",
        ).strip()
        or "https://github.com/MRYGP/SK.git",
        repo_sync_path=os.getenv("REPO_SYNC_PATH", "/repo-cache/SK").strip()
        or "/repo-cache/SK",
    )


def _build_database_url_from_parts() -> str:
    host = os.getenv("POSTGRES_HOST", "db").strip()
    port = os.getenv("POSTGRES_PORT", "5432").strip()
    db = os.getenv("POSTGRES_DB", "sk_agent").strip()
    user = os.getenv("POSTGRES_USER", "sk_agent").strip()
    password = os.getenv("POSTGRES_PASSWORD", "sk_agent").strip()
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"
