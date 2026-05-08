from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from app.config import CANONICAL_FILES, Settings


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
UNREAD_MESSAGE = "本次未读取到，文件未读取到不等于文件不存在"
NOT_CONFIGURED_MESSAGE = "请配置 LOCAL_REPO_PATH，或配置 GITHUB_RAW_BASE_URL / GITHUB_REPO"
SKIP_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__"}


@dataclass(frozen=True)
class FileMeta:
    path: str
    size: int
    last_modified: str | None
    source: str


class RepoReader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list_files(self) -> dict[str, Any]:
        root = self._local_root()
        if root:
            files = [asdict(meta) for meta in self._list_local_files(root)]
            return {
                "status": "ok",
                "source": "local",
                "root": str(root),
                "count": len(files),
                "files": files,
            }

        if self.settings.local_repo_path:
            result = self._local_root_unavailable()
            result.update({"count": 0, "files": []})
            return result

        if self._github_can_list():
            return self._list_github_files()

        return {
            "status": "not_configured",
            "message": NOT_CONFIGURED_MESSAGE,
            "count": 0,
            "files": [],
        }

    def read_file(self, path: str) -> dict[str, Any]:
        normalized = self._normalize_repo_path(path)
        if not normalized:
            return self._not_found(path)

        root = self._local_root()
        if root:
            return self._read_local_file(root, normalized)

        if self.settings.local_repo_path:
            return self._local_root_unavailable(normalized)

        if self.settings.github_raw_base_url:
            return self._read_github_raw_file(normalized)

        if self.settings.github_repo:
            return self._read_github_api_file(normalized)

        return {
            "status": "not_configured",
            "message": NOT_CONFIGURED_MESSAGE,
            "path": normalized,
            "file": None,
        }

    def read_canonical_files(self) -> dict[str, Any]:
        files = [self.read_file(path) for path in CANONICAL_FILES]
        read_count = sum(1 for item in files if item.get("status") == "ok")
        overall_status = "ok" if read_count == len(CANONICAL_FILES) else "partial"
        return {
            "status": overall_status,
            "canonical_files": CANONICAL_FILES,
            "read_count": read_count,
            "total": len(CANONICAL_FILES),
            "files": files,
        }

    def _local_root(self) -> Path | None:
        if not self.settings.local_repo_path:
            return None
        root = Path(self.settings.local_repo_path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return None
        return root

    def _list_local_files(self, root: Path) -> list[FileMeta]:
        results: list[FileMeta] = []
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            relative_parts = file_path.relative_to(root).parts
            if any(part in SKIP_DIRS for part in relative_parts):
                continue
            relative_path = "/".join(relative_parts)
            stat = file_path.stat()
            results.append(
                FileMeta(
                    path=relative_path,
                    size=stat.st_size,
                    last_modified=self._format_timestamp(stat.st_mtime),
                    source="local",
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
            return self._not_found(path)

        raw = file_path.read_bytes()
        stat = file_path.stat()
        return {
            "status": "ok",
            "path": path,
            "content": raw.decode("utf-8-sig", errors="replace"),
            "file": asdict(
                FileMeta(
                    path=path,
                    size=stat.st_size,
                    last_modified=self._format_timestamp(stat.st_mtime),
                    source="local",
                )
            ),
        }

    def _github_can_list(self) -> bool:
        return bool(self.settings.github_repo)

    def _list_github_files(self) -> dict[str, Any]:
        url = (
            f"https://api.github.com/repos/{self.settings.github_repo}/git/trees/"
            f"{quote(self.settings.github_branch, safe='')}?recursive=1"
        )
        try:
            payload = self._request_json(url)
        except HTTPError as exc:
            return self._github_error("github_api", exc)
        except URLError as exc:
            return self._github_error("github_api", exc)

        files = []
        for item in payload.get("tree", []):
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            if any(part in SKIP_DIRS for part in PurePosixPath(path).parts):
                continue
            files.append(
                asdict(
                    FileMeta(
                        path=path,
                        size=int(item.get("size") or 0),
                        last_modified=None,
                        source="github_api",
                    )
                )
            )
        return {
            "status": "ok",
            "source": "github_api",
            "repo": self.settings.github_repo,
            "branch": self.settings.github_branch,
            "count": len(files),
            "files": sorted(files, key=lambda item: item["path"].lower()),
        }

    def _read_github_raw_file(self, path: str) -> dict[str, Any]:
        url = f"{self.settings.github_raw_base_url}/{quote(path, safe='/')}"
        try:
            raw = self._request_bytes(url)
        except HTTPError as exc:
            if exc.code == 404:
                return self._not_found(path, "github_raw")
            return self._github_error("github_raw", exc, path)
        except URLError as exc:
            return self._github_error("github_raw", exc, path)

        return {
            "status": "ok",
            "path": path,
            "content": raw.decode("utf-8-sig", errors="replace"),
            "file": asdict(
                FileMeta(
                    path=path,
                    size=len(raw),
                    last_modified=None,
                    source="github_raw",
                )
            ),
        }

    def _read_github_api_file(self, path: str) -> dict[str, Any]:
        url = (
            f"https://api.github.com/repos/{self.settings.github_repo}/contents/"
            f"{quote(path, safe='/')}?ref={quote(self.settings.github_branch, safe='')}"
        )
        try:
            payload = self._request_json(url)
        except HTTPError as exc:
            if exc.code == 404:
                return self._not_found(path, "github_api")
            return self._github_error("github_api", exc, path)
        except URLError as exc:
            return self._github_error("github_api", exc, path)

        encoded = payload.get("content", "")
        raw = base64.b64decode(encoded.encode("utf-8"), validate=False)
        return {
            "status": "ok",
            "path": path,
            "content": raw.decode("utf-8-sig", errors="replace"),
            "file": asdict(
                FileMeta(
                    path=path,
                    size=int(payload.get("size") or len(raw)),
                    last_modified=None,
                    source="github_api",
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
            message = f"GitHub 读取失败：HTTP {exc.code}"
        return {
            "status": "error",
            "source": source,
            "path": path,
            "message": message,
        }

    def _local_root_unavailable(self, path: str | None = None) -> dict[str, Any]:
        return {
            "status": "repo_path_unavailable",
            "source": "local",
            "path": path,
            "message": f"LOCAL_REPO_PATH 本次不可读取：{self.settings.local_repo_path}",
            "file": None,
            "content": None,
        }

    def _not_found(self, path: str, source: str | None = None) -> dict[str, Any]:
        return {
            "status": "not_found",
            "source": source,
            "path": path,
            "message": UNREAD_MESSAGE,
            "file": None,
            "content": None,
        }

    def _normalize_repo_path(self, path: str) -> str:
        cleaned = (path or "").replace("\\", "/").strip().lstrip("/")
        if not cleaned:
            return ""
        pure_path = PurePosixPath(cleaned)
        if any(part in {"", ".", ".."} for part in pure_path.parts):
            return ""
        return str(pure_path)

    def _format_timestamp(self, value: float) -> str:
        return datetime.fromtimestamp(value, tz=SHANGHAI_TZ).isoformat(timespec="seconds")
