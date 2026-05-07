from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.patch_writer import PatchDraftInput, PatchWriter


class FakeReader:
    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = files or {}

    def read_file(self, path: str) -> dict:
        if path not in self.files:
            return {
                "status": "not_found",
                "path": path,
                "source": "fake",
                "message": "本次未读取到，文件未读取到不等于文件不存在",
                "file": None,
                "content": None,
            }
        content = self.files[path]
        return {
            "status": "ok",
            "path": path,
            "content": content,
            "file": {
                "path": path,
                "size": len(content.encode("utf-8")),
                "last_modified": None,
                "source": "fake",
            },
        }


def test_patch_writer_appends_when_target_was_read() -> None:
    writer = PatchWriter(FakeReader({"ops/status.md": "# Status\n"}))  # type: ignore[arg-type]

    result = writer.draft(
        PatchDraftInput(
            target_file="ops/status.md",
            intent="更新执行状态总表",
            new_content="- 001 已发布",
        )
    )

    assert result["status"] == "ok"
    assert result["operation"] == "append"
    assert result["suggested_save_path"] == "ops/status.md"
    assert result["read_files"][0]["status"] == "ok"
    assert "- 001 已发布" in result["markdown_body"]
    assert "+- 001 已发布" in result["diff_preview"]
    assert result["commit_message"].startswith("docs: update")


def test_patch_writer_creates_when_target_was_not_read() -> None:
    writer = PatchWriter(FakeReader())  # type: ignore[arg-type]

    result = writer.draft(
        PatchDraftInput(
            target_file="cases/2026/999-new.md",
            intent="新增轻量初拆文档",
            new_content="# New\n\nContent",
        )
    )

    assert result["operation"] == "create"
    assert result["read_files"][0]["status"] == "not_found"
    assert result["risk_notes"]
    assert "+# New" in result["diff_preview"]


def test_patch_draft_api_rejects_invalid_path() -> None:
    client = TestClient(app)

    response = client.post(
        "/patch/draft",
        json={
            "target_file": "../README.md",
            "intent": "bad path",
            "new_content": "content",
        },
    )

    assert response.status_code == 400
