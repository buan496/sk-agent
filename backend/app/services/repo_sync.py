from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.config import Settings


class RepoSyncError(RuntimeError):
    pass


def sync_repo(settings: Settings) -> dict:
    owner, repo = _parse_github_repo(settings.repo_sync_url or settings.github_repo)
    branch = settings.github_branch.strip() or "main"
    target = Path(settings.repo_sync_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    commit = _latest_commit(owner, repo, branch, settings.github_token)
    with tempfile.TemporaryDirectory(dir=str(target.parent)) as tmp_dir:
        archive_path = Path(tmp_dir) / "repo.zip"
        extract_dir = Path(tmp_dir) / "extract"
        _download_zipball(owner, repo, branch, settings.github_token, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extract_dir)
        roots = [item for item in extract_dir.iterdir() if item.is_dir()]
        if not roots:
            raise RepoSyncError("GitHub archive did not contain a repository directory")
        unpacked = roots[0]
        replacement = Path(tmp_dir) / "replacement"
        shutil.move(str(unpacked), str(replacement))
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(replacement), str(target))

    return {
        "status": "ok",
        "action": "download_zipball",
        "repo": f"{owner}/{repo}",
        "branch": branch,
        "target_path": str(target),
        "commit": commit,
        "message": "SK repository cache refreshed from GitHub zipball.",
    }


def _parse_github_repo(value: str) -> tuple[str, str]:
    cleaned = (value or "").strip()
    if not cleaned:
        raise RepoSyncError("REPO_SYNC_URL or GITHUB_REPO is not configured")
    if "/" in cleaned and not cleaned.startswith(("http://", "https://", "git@")):
        owner, repo = cleaned.strip("/").split("/", 1)
        return owner, repo.removesuffix(".git")
    if cleaned.startswith("git@github.com:"):
        path = cleaned.removeprefix("git@github.com:").removesuffix(".git")
        owner, repo = path.split("/", 1)
        return owner, repo
    parsed = urlparse(cleaned)
    parts = parsed.path.strip("/").removesuffix(".git").split("/")
    if parsed.netloc != "github.com" or len(parts) < 2:
        raise RepoSyncError("Only GitHub repository URLs are supported for /repo/sync")
    return parts[0], parts[1]


def _latest_commit(owner: str, repo: str, branch: str, token: str) -> str | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
    try:
        payload = json.loads(_request_bytes(url, token).decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError):
        return None
    return payload.get("sha")


def _download_zipball(owner: str, repo: str, branch: str, token: str, archive_path: Path) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"
    try:
        archive_path.write_bytes(_request_bytes(url, token))
    except HTTPError as exc:
        raise RepoSyncError(f"GitHub zipball download failed: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RepoSyncError(f"GitHub zipball download failed: {exc}") from exc


def _request_bytes(url: str, token: str) -> bytes:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "sk-agent-workbench",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=180) as response:
        return response.read()
