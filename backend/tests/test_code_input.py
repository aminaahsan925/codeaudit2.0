"""Zip uploads: .git/ members are stripped on extraction.

A malicious .git can carry hooks and git config that execute when a
scanner runs git in the extracted tree, so extract_zip drops every
member under .git/ and keeps the rest intact. Cloned repos keep their
full .git: the history scan needs it (see test_git_history_scan.py).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.services.runs.code_input import extract_zip


def _zip_with_git(tmp_path: Path) -> Path:
    zip_path = tmp_path / "upload.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        # A smuggled .git: hooks, config, objects, plus a bare .git file
        # (a gitdir pointer) at the top level.
        archive.writestr(".git/hooks/post-checkout", "#!/bin/sh\nid\n")
        archive.writestr(".git/config", "[core]\n\thooksPath = /tmp/evil\n")
        archive.writestr(".git/objects/aa/bb", "object bytes")
        archive.writestr(".git", "gitdir: /elsewhere\n")
        archive.writestr("app.py", 'print("hello")\n')
    return zip_path


def test_extract_zip_strips_git_dir(tmp_path) -> None:
    """No .git/ member survives extraction; normal files are intact."""
    target = tmp_path / "tree"
    extract_zip(_zip_with_git(tmp_path), target)
    assert not (target / ".git").exists()
    assert (target / "app.py").read_text(encoding="utf-8") == 'print("hello")\n'
