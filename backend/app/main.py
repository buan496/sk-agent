from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.graph import router as graph_router
from app.api.index import router as index_router
from app.api.llm import router as llm_router
from app.api.patch import router as patch_router
from app.api.repo import router as repo_router
from app.api.search import router as search_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(repo_router)
app.include_router(index_router)
app.include_router(llm_router)
app.include_router(search_router)
app.include_router(agents_router)
app.include_router(patch_router)
app.include_router(graph_router)
