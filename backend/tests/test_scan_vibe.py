"""Tests for the vibe-coding checks (CONTRACT.md, engine "vibe").

Fake key-shaped values in this file carry an inline `gitleaks:allow`
comment so the repo's own secret scan does not flag test data.
"""

from pathlib import Path

import pytest

from app.schemas.finding import Finding
from app.services.scan import run_code_scan
from app.services.scan.runner import collect_files
from app.services.scan.vibe import scan_vibe_files

FIXTURES = Path(__file__).parent / "fixtures"


def _vibe_findings(root: Path) -> list[Finding]:
    outcome = run_code_scan(root, run_external=False)
    return [f for f in outcome.findings if f.engine.value == "vibe"]


def _found(root: Path) -> set[tuple[str, str, int]]:
    return {(f.rule_id, f.file or "", f.start_line or 0) for f in _vibe_findings(root)}


def test_vibe_app_fixture() -> None:
    found = _found(FIXTURES / "vibe_app")
    assert ("SUPABASE_NO_RLS", "supabase/migrations/0001_create_posts.sql", 1) in found
    assert (
        "SUPABASE_SERVICE_KEY_FRONTEND",
        "src/components/admin.tsx",
        4,
    ) in found
    assert ("SECRET_IN_PUBLIC_VAR", ".env.local", 1) in found
    assert ("FIREBASE_OPEN_RULES", "firestore.rules", 5) in found
    assert ("API_ROUTE_NO_AUTH", "src/app/api/posts/route.ts", 1) in found
    assert ("LLM_KEY_FROM_BROWSER", "src/lib/chat.ts", 2) in found
    assert ("LLM_KEY_FROM_BROWSER", "src/lib/chat.ts", 5) in found


def test_vibe_app_negative_cases() -> None:
    found = _found(FIXTURES / "vibe_app")
    # Migration with RLS enabled is not flagged.
    assert not any(
        rule == "SUPABASE_NO_RLS" and "0002_create_profiles" in file for rule, file, _ in found
    )
    # API route with a session check is not flagged.
    assert not any(rule == "API_ROUTE_NO_AUTH" and "protected" in file for rule, file, _ in found)
    # NEXT_PUBLIC_/VITE_ vars with ordinary values are not flagged.
    public_var_lines = {line for rule, file, line in found if rule == "SECRET_IN_PUBLIC_VAR"}
    assert public_var_lines == {1}


def test_fastapi_app_is_not_flagged_by_vibe() -> None:
    assert _vibe_findings(FIXTURES / "demo_fixed") == []
    assert _vibe_findings(FIXTURES / "demo_broken") == []


def test_supabase_no_rls_needs_supabase_in_use() -> None:
    # A CREATE TABLE with no Supabase marker anywhere is not flagged.
    files = {"schema.sql": ["CREATE TABLE posts (id uuid primary key);"]}
    assert scan_vibe_files(files) == []


def test_supabase_no_rls_one_finding_per_file() -> None:
    files = {
        "app.ts": ['import { createClient } from "@supabase/supabase-js";'],
        "migrations/0001.sql": [
            "CREATE TABLE a (id int);",
            "CREATE TABLE b (id int);",
        ],
    }
    findings = scan_vibe_files(files)
    assert [(f.rule_id, f.start_line) for f in findings] == [("SUPABASE_NO_RLS", 1)]


def test_secret_in_public_var_vite() -> None:
    files = {".env": ["VITE_API_KEY=abcdefghij1234567890"]}  # gitleaks:allow
    findings = scan_vibe_files(files)
    assert [f.rule_id for f in findings] == ["SECRET_IN_PUBLIC_VAR"]


def test_secret_in_public_var_placeholder_not_flagged() -> None:
    files = {".env": ["NEXT_PUBLIC_API_KEY=your-api-key-here"]}
    assert scan_vibe_files(files) == []


def test_firebase_open_rules_json_style() -> None:
    files = {"database.rules.json": ['{".read": true, ".write": true}']}
    findings = scan_vibe_files(files)
    assert [f.rule_id for f in findings] == ["FIREBASE_OPEN_RULES"]


def test_firebase_locked_rules_not_flagged() -> None:
    files = {"firestore.rules": ["allow read, write: if request.auth != null;"]}
    assert scan_vibe_files(files) == []


def test_api_route_with_auth_check_not_flagged() -> None:
    files = {
        "src/app/api/orders/route.ts": [
            "export async function POST(request: Request) {",
            "  const token = request.headers.get('Authorization');",
            "  if (!token) return new Response('nope', { status: 401 });",
            "}",
        ]
    }
    assert scan_vibe_files(files) == []


def test_llm_key_bare_sk_key_in_browser_file() -> None:
    files = {"src/lib/chat.ts": ['const key = "sk-abcdefghij1234567890";']}  # gitleaks:allow
    findings = scan_vibe_files(files)
    assert [f.rule_id for f in findings] == ["LLM_KEY_FROM_BROWSER"]


def test_vibe_findings_carry_guidance() -> None:
    findings = _vibe_findings(FIXTURES / "vibe_app")
    assert findings
    for finding in findings:
        assert finding.fix_guidance is not None
        assert "## Why it matters" in finding.fix_guidance
        assert "## How to fix" in finding.fix_guidance
        assert finding.file and finding.start_line


@pytest.mark.parametrize("filename", ["firestore.rules", "database.rules.json"])
def test_collect_files_includes_rule_files(filename: str) -> None:
    # The runner must collect .rules/.json files or vibe rule 4 never runs.
    files = collect_files(FIXTURES / "vibe_app")
    assert any(name.endswith(filename) for name in files)
