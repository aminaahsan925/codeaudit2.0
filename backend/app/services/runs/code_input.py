"""Fetch the code a run scans: a shallow GitHub clone or a zip upload.

Scanned code is read, never run, never imported. Clones use an argument
list (never a shell) with a timeout, and zip extraction guards against
path traversal and zip bombs (same limits as PORTING-NOTES.md: max 50 MiB
total, max 2000 files).

Every failure here raises `CodeInputError` with a message that is safe to
show the user: no stack traces, no git stderr, no internals.
"""

from __future__ import annotations

import re
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

CLONE_TIMEOUT_SECONDS = 120
MAX_ZIP_BYTES = 50 * 1024 * 1024  # 50 MiB total uncompressed
MAX_ZIP_FILES = 2000
_CHUNK_BYTES = 64 * 1024

_GITHUB_URL_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


class CodeInputError(ValueError):
    """A code-fetch failure with a user-facing message."""


def validate_github_url(repo_url: str) -> tuple[str, str] | None:
    """Parse an https github.com URL into (owner, repo), else None.

    Only https github.com URLs are accepted: no other host, no other
    scheme, no credentials in the URL.
    """
    match = _GITHUB_URL_RE.match((repo_url or "").strip())
    if not match:
        return None
    return match.group(1), match.group(2)


def clone_repo(repo_url: str, target: Path, *, timeout: int = CLONE_TIMEOUT_SECONDS) -> None:
    """Shallow-clone a validated GitHub URL into `target` (must not exist)."""
    git = shutil.which("git")
    if git is None:
        raise CodeInputError("Git is not available on this server.")
    try:
        proc = subprocess.run(  # noqa: S603 - arg list, URL validated to github.com
            [git, "clone", "--depth", "1", repo_url, str(target)],
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CodeInputError("Fetching the repo timed out. Check the URL and try again.") from exc
    except OSError as exc:
        raise CodeInputError("Could not fetch the repo. Check the URL and try again.") from exc
    if proc.returncode != 0:
        raise CodeInputError("Could not fetch the repo. Check the URL and that the repo is public.")


def _is_symlink_member(member: zipfile.ZipInfo) -> bool:
    mode = (member.external_attr >> 16) & 0o170000
    return stat.S_ISLNK(mode)


def extract_zip(zip_path: Path, target: Path) -> None:
    """Extract a zip into `target`, guarding traversal, symlinks and bombs.

    Rejects absolute paths and ".." members, caps the total uncompressed
    size at 50 MiB and the file count at 2000. Symlink members are skipped.
    """
    if not zip_path.is_file():
        raise CodeInputError("The uploaded code is no longer available.")
    target.mkdir(parents=True, exist_ok=True)
    resolved_target = target.resolve()
    total_bytes = 0
    file_count = 0
    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise CodeInputError("The uploaded zip file is not valid.") from exc
    with archive:
        for member in archive.infolist():
            if member.is_dir() or _is_symlink_member(member):
                continue
            name = member.filename
            if name.startswith(("/", "\\")) or ".." in Path(name).parts:
                raise CodeInputError("The zip file contains unsafe paths.")
            file_count += 1
            if file_count > MAX_ZIP_FILES:
                raise CodeInputError("The uploaded zip has too many files.")
            if member.file_size > MAX_ZIP_BYTES:
                raise CodeInputError("The uploaded zip is too large.")
            dest = (target / name).resolve()
            if not dest.is_relative_to(resolved_target):
                raise CodeInputError("The zip file contains unsafe paths.")
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                with archive.open(member) as source, open(dest, "wb") as out:
                    while chunk := source.read(_CHUNK_BYTES):
                        total_bytes += len(chunk)
                        if total_bytes > MAX_ZIP_BYTES:
                            raise CodeInputError("The uploaded zip is too large.")
                        out.write(chunk)
            except zipfile.BadZipFile as exc:
                raise CodeInputError("The uploaded zip file is not valid.") from exc
            except OSError as exc:
                raise CodeInputError("The uploaded zip file could not be read.") from exc
