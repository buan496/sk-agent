from __future__ import annotations

import pytest

from app.services.repo_sync import RepoSyncError, _parse_github_repo


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("MRYGP/SK", ("MRYGP", "SK")),
        ("https://github.com/MRYGP/SK.git", ("MRYGP", "SK")),
        ("https://github.com/MRYGP/SK", ("MRYGP", "SK")),
        ("git@github.com:MRYGP/SK.git", ("MRYGP", "SK")),
    ],
)
def test_parse_github_repo(value: str, expected: tuple[str, str]) -> None:
    assert _parse_github_repo(value) == expected


def test_parse_github_repo_rejects_non_github_url() -> None:
    with pytest.raises(RepoSyncError):
        _parse_github_repo("https://example.com/MRYGP/SK.git")
