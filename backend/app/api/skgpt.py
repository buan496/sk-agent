from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.config import Settings, get_settings
from app.roles.role_prompt_loader import RolePromptLoader
from app.services.skgpt_reader import SKGPTReader

router = APIRouter(prefix="/skgpt", tags=["skgpt"])


def get_skgpt_reader(settings: Settings = Depends(get_settings)) -> SKGPTReader:
    return SKGPTReader(settings)


@router.get("/files")
def list_skgpt_files(reader: SKGPTReader = Depends(get_skgpt_reader)) -> dict:
    return reader.list_files()


@router.get("/file")
def read_skgpt_file(
    path: str = Query(..., description="SKGPT repository-relative instruction path"),
    reader: SKGPTReader = Depends(get_skgpt_reader),
) -> dict:
    return reader.read_file(path)


@router.get("/role-prompts")
def role_prompts(settings: Settings = Depends(get_settings)) -> dict:
    prompts = RolePromptLoader(settings=settings).load_all_prompts()
    return {
        "status": "ok",
        "count": len(prompts),
        "prompts": prompts,
        "principle": "SKGPT 只作为角色指令来源；SK canonical files 仍然是当前状态最高优先级。",
    }
