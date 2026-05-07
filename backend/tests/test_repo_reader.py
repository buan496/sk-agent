from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.services.repo_reader import RepoReader


def test_read_local_file(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_bytes("# SK\n".encode("utf-8"))

    reader = RepoReader(Settings(local_repo_path=str(tmp_path)))
    result = reader.read_file("README.md")

    assert result["status"] == "ok"
    assert result["path"] == "README.md"
    assert result["content"] == "# SK\n"
    assert result["file"]["source"] == "local"


def test_missing_file_is_not_found_without_claiming_absence(tmp_path: Path) -> None:
    reader = RepoReader(Settings(local_repo_path=str(tmp_path)))
    result = reader.read_file("missing.md")

    assert result["status"] == "not_found"
    assert "本次未读取到" in result["message"]


def test_list_local_files_skips_git_directory(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("private", encoding="utf-8")
    (tmp_path / "ops").mkdir()
    (tmp_path / "ops" / "执行状态总表.md").write_text("ok", encoding="utf-8")

    reader = RepoReader(Settings(local_repo_path=str(tmp_path)))
    result = reader.list_files()

    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["files"][0]["path"] == "ops/执行状态总表.md"


def test_configured_local_repo_path_must_be_readable(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing-root"

    reader = RepoReader(Settings(local_repo_path=str(missing_root)))
    result = reader.read_file("README.md")

    assert result["status"] == "repo_path_unavailable"
    assert "LOCAL_REPO_PATH" in result["message"]
