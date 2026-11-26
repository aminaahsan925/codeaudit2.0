# External scanner tools

The code scanner runs its native rules and vibe checks always. These
optional tools add findings when they are installed; a missing or failing
tool never fails an audit, it is recorded as skipped with a reason.

The scanner looks for each binary in this order:

1. On `PATH`
2. In this directory (`backend/tools/`)
3. In `backend/.venv/bin/`

Binaries in this directory are gitignored (see `.gitignore` here). Only
this README is committed.

## semgrep

Static analysis (`semgrep --config auto --json`, 120s timeout). Findings
are prefixed `semgrep:`, mapped ERROR to High, WARNING to Medium, INFO
to Low, and dropped when a native finding already covers the same
(file, line), or when the rule belongs to a framework the project does
not use (Django/Flask rules on other apps).

Install into a venv inside this directory (keeps it out of the project
venv, which must not gain extra dependencies):

```sh
cd backend/tools
python3 -m venv semgrep-venv
./semgrep-venv/bin/pip install semgrep
ln -s semgrep-venv/bin/semgrep semgrep
./semgrep --version
```

Note: `semgrep --config auto` downloads its rule set from the semgrep
registry on first run, so the first scan needs network access.

Verified with semgrep 1.186.0.

## gitleaks

Secret scanning of git history (only when the upload has a `.git`
directory). Findings become `SECRET_GIT_HISTORY` (Critical), masked.

```sh
# Linux amd64: download the release binary into this directory
curl -sL -o gitleaks.tar.gz \
  https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_VERSION_linux_x64.tar.gz
tar -xzf gitleaks.tar.gz gitleaks
./gitleaks version
```

Replace `VERSION` with the release tag, for example `v8.30.1`. Or
install it with your system package manager so it is on `PATH`.

Verified with gitleaks 8.30.1.

## osv-scanner

Dependency vulnerability scanning of `requirements.txt` /
`package.json`. Findings become `CVE_DEP` (Medium) with the CVE id and
fixed version. Direct dependencies only: transitive ones have no line
in the manifest to point at, so they are skipped.

```sh
# Linux amd64: download the release binary into this directory
curl -sL -o osv-scanner \
  https://github.com/google/osv-scanner/releases/latest/download/osv-scanner_linux_amd64
chmod +x osv-scanner
./osv-scanner --version
```

The `/releases/latest/download/` redirect avoids the GitHub API, which
is rate-limited for unauthenticated requests on shared IPs.

Verified with osv-scanner 2.7.1.

## pip-audit

Fallback CVE scanner when osv-scanner is not installed (needs a
`requirements.txt`). Install it into the same venv as semgrep:

```sh
cd backend/tools
./semgrep-venv/bin/pip install pip-audit
ln -s semgrep-venv/bin/pip-audit pip-audit
./pip-audit --version
```

Verified with pip-audit 2.10.1.
