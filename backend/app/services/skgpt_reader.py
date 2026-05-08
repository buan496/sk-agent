from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from app.config import Settings


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
UNREAD_MESSAGE = "本次未读取到；这只代表本次没有成功读取 SKGPT 指令文件"
NOT_CONFIGURED_MESSAGE = "请配置 SKGPT_REPO_LOCAL_PATH 或 SKGPT_REPO_URL"
SKIP_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__"}


@dataclass(frozen=True)
class SKGPTFileMeta:
    path: str
    size: int
    last_modified: str | None
    source: str
    commit_hash: str | None = None


class SKGPTReader:
    """Read SKGPT role instructions without mixing them into SK content indexing."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list_files(self) -> dict[str, Any]:
        root = self._local_root()
        if root:
            files = [asdict(meta) for meta in self._list_local_files(root)]
            return {
                "status": "ok",
                "source": "local_skgpt",
                "root": str(root),
                "count": len(files),
                "files": files,
            }

        if self.settings.skgpt_repo_local_path:
            return {
                "status": "repo_path_unavailable",
                "source": "local_skgpt",
                "root": self.settings.skgpt_repo_local_path,
                "message": f"SKGPT_REPO_LOCAL_PATH 本次不可读取：{self.settings.skgpt_repo_local_path}",
                "count": 0,
                "files": [],
            }

        repo_slug = _github_repo_slug(self.settings.skgpt_repo_url)
        if repo_slug:
            return self._list_github_files(repo_slug)

        return {
            "status": "not_configured",
            "message": NOT_CONFIGURED_MESSAGE,
            "count": 0,
            "files": [],
        }

    def read_file(self, path: str) -> dict[str, Any]:
        normalized = _normalize_repo_path(path)
        if not normalized:
            return self._not_found(path)

        root = self._local_root()
        if root:
            return self._read_local_file(root, normalized)

        if self.settings.skgpt_repo_local_path:
            return {
                "status": "repo_path_unavailable",
                "source": "local_skgpt",
                "path": normalized,
                "message": f"SKGPT_REPO_LOCAL_PATH 本次不可读取：{self.settings.skgpt_repo_local_path}",
                "content": None,
                "file": None,
            }

        repo_slug = _github_repo_slug(self.settings.skgpt_repo_url)
        if repo_slug:
            return self._read_github_api_file(repo_slug, normalized)

        return {
            "status": "not_configured",
            "message": NOT_CONFIGURED_MESSAGE,
            "path": normalized,
            "content": None,
            "file": None,
        }

    def _local_root(self) -> Path | None:
        if not self.settings.skgpt_repo_local_path:
            return None
        root = Path(self.settings.skgpt_repo_local_path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return None
        return root

    def _list_local_files(self, root: Path) -> list[SKGPTFileMeta]:
        results: list[SKGPTFileMeta] = []
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            relative_parts = file_path.relative_to(root).parts
            if any(part in SKIP_DIRS for part in relative_parts):
                continue
            relative_path = "/".join(relative_parts)
            stat = file_path.stat()
            results.append(
                SKGPTFileMeta(
                    path=relative_path,
                    size=stat.st_size,
                    last_modified=_format_timestamp(stat.st_mtime),
                    source="local_skgpt",
                )
            )
        return sorted(results, key=lambda item: item.path.lower())

    def _read_local_file(self, root: Path, path: str) -> dict[str, Any]:
        file_path = (root / Path(path)).resolve()
        try:
            file_path.relative_to(root)
        except ValueError:
            return self._not_found(path)

        if not file_path.exists() or not file_path.is_file():
            return self._not_found(path, "local_skgpt")

        raw = file_path.read_bytes()
        stat = file_path.stat()
        return {
            "status": "ok",
            "path": path,
            "content": raw.decode("utf-8-sig", errors="replace"),
            "source": "local_skgpt",
            "last_modified": _format_timestamp(stat.st_mtime),
            "commit_hash": None,
            "file": asdict(
                SKGPTFileMeta(
                    path=path,
                    size=stat.st_size,
                    last_modified=_format_timestamp(stat.st_mtime),
                    source="local_skgpt",
                )
            ),
        }

    def _list_github_files(self, repo_slug: str) -> dict[str, Any]:
        url = (
            f"https://api.github.com/repos/{repo_slug}/git/trees/"
            f"{quote(self.settings.skgpt_branch, safe='')}?recursive=1"
        )
        try:
            payload = self._request_json(url)
        except HTTPError as exc:
            return self._github_error("github_skgpt_api", exc)
        except URLError as exc:
            return self._github_error("github_skgpt_api", exc)

        files: list[dict[str, Any]] = []
        for item in payload.get("tree", []):
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            if any(part in SKIP_DIRS for part in PurePosixPath(path).parts):
                continue
            files.append(
                asdict(
                    SKGPTFileMeta(
                        path=path,
                        size=int(item.get("size") or 0),
                        last_modified=None,
                        source="github_skgpt_api",
                        commit_hash=item.get("sha"),
                    )
                )
            )
        return {
            "status": "ok",
            "source": "github_skgpt_api",
            "repo": repo_slug,
            "branch": self.settings.skgpt_branch,
            "count": len(files),
            "files": sorted(files, key=lambda item: item["path"].lower()),
        }

    def _read_github_api_file(self, repo_slug: str, path: str) -> dict[str, Any]:
        url = (
            f"https://api.github.com/repos/{repo_slug}/contents/"
            f"{quote(path, safe='/')}?ref={quote(self.settings.skgpt_branch, safe='')}"
        )
        try:
            payload = self._request_json(url)
        except HTTPError as exc:
            if exc.code == 404:
                return self._not_found(path, "github_skgpt_api")
            return self._github_error("github_skgpt_api", exc, path)
        except URLError as exc:
            return self._github_error("github_skgpt_api", exc, path)

        encoded = payload.get("content", "")
        raw = base64.b64decode(encoded.encode("utf-8"), validate=False)
        return {
            "status": "ok",
            "path": path,
            "content": raw.decode("utf-8-sig", errors="replace"),
            "source": "github_skgpt_api",
            "last_modified": None,
            "commit_hash": payload.get("sha"),
            "file": asdict(
                SKGPTFileMeta(
                    path=path,
                    size=int(payload.get("size") or len(raw)),
                    last_modified=None,
                    source="github_skgpt_api",
                    commit_hash=payload.get("sha"),
                )
            ),
        }

    def _request_json(self, url: str) -> dict[str, Any]:
        return json.loads(self._request_bytes(url).decode("utf-8"))

    def _request_bytes(self, url: str) -> bytes:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "sk-agent-workbench",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        request = Request(url, headers=headers)
        with urlopen(request, timeout=20) as response:
            return response.read()

    def _github_error(self, source: str, exc: Exception, path: str | None = None) -> dict[str, Any]:
        message = str(exc)
        if isinstance(exc, HTTPError):
            message = f"SKGPT GitHub 读取失败：HTTP {exc.code}"
        return {
            "status": "error",
            "source": source,
            "path": path,
            "message": message,
        }

    def _not_found(self, path: str, source: str | None = None) -> dict[str, Any]:
        return {
            "status": "not_found",
            "source": source,
            "path": path,
            "message": UNREAD_MESSAGE,
            "content": None,
            "file": None,
            "last_modified": None,
            "commit_hash": None,
        }


def _github_repo_slug(repo_url: str) -> str:
    cleaned = (repo_url or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("git@github.com:"):
        cleaned = cleaned.removeprefix("git@github.com:")
        return cleaned.removesuffix(".git").strip("/")
    parsed = urlparse(cleaned)
    if parsed.netloc.lower() != "github.com":
        return ""
    path = parsed.path.strip("/").removesuffix(".git")
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return ""
    return f"{parts[0]}/{parts[1]}"


def _normalize_repo_path(path: str) -> str:
    cleaned = (path or "").replace("\\", "/").strip().lstrip("/")
    if not cleaned:
        return ""
    pure_path = PurePosixPath(cleaned)
    if any(part in {"", ".", ".."} for part in pure_path.parts):
        return ""
    return str(pure_path)


def _format_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=SHANGHAI_TZ).isoformat(timespec="seconds")
