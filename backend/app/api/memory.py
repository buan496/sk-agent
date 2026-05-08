from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.memory_service import (
    create_external_agent_run,
    list_external_agent_runs,
    read_memory_file,
)

router = APIRouter(prefix="/memory", tags=["memory"])

AgentType = Literal[
    "chatgpt_project",
    "gpts",
    "claude",
    "codex",
    "hermes",
    "cursor",
    "sk_agent",
    "other",
]
RunStatus = Literal["draft", "reviewed", "ingested", "rejected", "archived"]


class ExternalRunRequest(BaseModel):
    agent_type: AgentType
    agent_name: str = Field(..., min_length=1)
    task_type: str = Field(..., min_length=1)
    input_summary: str = Field(..., min_length=1)
    output_summary: str = Field(..., min_length=1)
    source_link_or_file: str = ""
    related_sk_files: list[str] = Field(default_factory=list)
    status: RunStatus = "draft"
    should_ingest: bool = False
    ingested: bool = False
    notes: str = ""


@router.get("/core")
def memory_core() -> dict:
    return {
        "status": "ok",
        "core_memory": read_memory_file("core_memory"),
        "constitution": read_memory_file("constitution"),
    }


@router.get("/registries")
def memory_registries() -> dict:
    return {
        "status": "ok",
        "internal_roles": read_memory_file("internal_roles"),
        "agent_registry": read_memory_file("agent_registry"),
        "gpts_registry": read_memory_file("gpts_registry"),
        "external_tools": read_memory_file("external_tools"),
    }


@router.get("/episodes")
def memory_episodes() -> dict:
    return {
        "status": "ok",
        "drift_log": read_memory_file("drift_log"),
        "agent_lessons": read_memory_file("agent_lessons"),
        "role_lessons": read_memory_file("role_lessons"),
        "routing_lessons": read_memory_file("routing_lessons"),
    }


@router.post("/external-run")
def record_external_run(request: ExternalRunRequest) -> dict:
    return {
        "status": "ok",
        "run": create_external_agent_run(request.model_dump()),
    }


@router.get("/external-runs")
def external_runs(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    runs = list_external_agent_runs(limit=limit)
    return {
        "status": "ok",
        "count": len(runs),
        "runs": runs,
    }
