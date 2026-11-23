"""Tests for the native code scan rules (CONTRACT.md rules 1-10).

Fake key-shaped values in this file carry an inline `gitleaks:allow`
comment so the repo's own secret scan does not flag test data.
"""

from pathlib import Path

import pytest

from app.schemas.finding import Confidence, Finding, Severity
from app.services.scan import run_code_scan
from app.services.scan.native import scan_native_files

FIXTURES = Path(__file__).parent / "fixtures"


def _scan(content: str, filename: str = "app.py") -> list[Finding]:
    return scan_native_files({filename: content.splitlines()})


def _rule_ids(findings: list[Finding]) -> list[str]:
    return [f.rule_id for f in findings]


# --- Rule 1: SECRET_GENERIC ---------------------------------------------


def test_secret_generic_flags_long_value() -> None:
    findings = _scan('API_KEY = "abcdefghijklmnop1234"\n')  # gitleaks:allow
    assert _rule_ids(findings) == ["SECRET_GENERIC"]
    finding = findings[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.file == "app.py"
    assert finding.start_line == 1
    assert finding.snippet == 'API_KEY = "abcd****"'
    assert finding.fix_guidance is not None
    assert "## Why it matters" in finding.fix_guidance
    assert "## How to fix" in finding.fix_guidance


def test_secret_generic_flags_unquoted_env_assignment() -> None:
    findings = _scan("API_KEY=abcdefghijklmnop1234\n", ".env")  # gitleaks:allow
    assert _rule_ids(findings) == ["SECRET_GENERIC"]


def test_secret_generic_flags_yaml_assignment() -> None:
    findings = _scan("api_key: abcdefghijklmnop1234\n", "config.yaml")  # gitleaks:allow
    assert _rule_ids(findings) == ["SECRET_GENERIC"]


def test_secret_generic_skips_short_value() -> None:
    assert _scan('API_KEY = "short"\n') == []


@pytest.mark.parametrize(
    "value",
    [
        "your-api-key-123",
        "xxxxxxxxxxxx",
        "changeme-12345",
        "example-key-99",
        "placeholder-12",
        "todo-do-this-now",
        "change-me-12345",
    ],
)
def test_secret_generic_skips_placeholders(value: str) -> None:
    assert _scan(f'API_KEY = "{value}"\n') == []


@pytest.mark.parametrize(
    "line",
    [
        'API_KEY = os.environ.get("API_KEY")',
        'API_KEY = os.getenv("API_KEY")',
        "const key = process.env.API_KEY;",
    ],
)
def test_secret_generic_skips_env_reads(line: str) -> None:
    assert _scan(line + "\n") == []


def test_secret_generic_ignores_bare_expression_in_code() -> None:
    # In code files a bare assignment is an expression, not a literal.
    assert _scan("token = get_secret_token_value\n") == []
    # random.random() still flags WEAK_CRYPTO, but never SECRET_GENERIC.
    assert _rule_ids(_scan("token = str(random.random())\n")) == ["WEAK_CRYPTO"]


def test_secret_generic_ignores_token_inside_url_string() -> None:
    # A token query param inside a quoted URL is not an assignment.
    findings = _scan('url = "https://example.com/?token=abcdefghijklmnop"\n')
    assert findings == []


# --- Rule 2: SECRET_KNOWN_PREFIX -----------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        'KEY = "sk_live_abcdefgh12345678"',  # gitleaks:allow
        'KEY = "sk_test_abcdefgh12345678"',  # gitleaks:allow
        'KEY = "AKIAZZZZZZZZZZZZZZZZ"',  # gitleaks:allow
        'KEY = "ghp_abcdefghij1234567890"',  # gitleaks:allow
        'KEY = "github_pat_abcdefghij1234567890"',  # gitleaks:allow
        'KEY = "xoxb-123456789012"',  # gitleaks:allow
    ],
)
def test_secret_known_prefix(line: str) -> None:
    findings = _scan(line + "\n")
    assert _rule_ids(findings) == ["SECRET_KNOWN_PREFIX"]
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].confidence == Confidence.HIGH


def test_secret_known_prefix_pem_header() -> None:
    # Built from parts so the repo's own detect-private-key hook does not
    # flag this test file; the scanned line still carries the full header.
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    findings = _scan(header + "\n")
    assert _rule_ids(findings) == ["SECRET_KNOWN_PREFIX"]


def test_known_prefix_suppresses_generic_on_same_line() -> None:
    findings = _scan('STRIPE_SECRET_KEY = "sk_test_abcdefgh12345678"\n')  # gitleaks:allow
    assert _rule_ids(findings) == ["SECRET_KNOWN_PREFIX"]


# --- Rule 10: HARDCODED_CREDENTIAL ---------------------------------------


def test_hardcoded_credential_short_value() -> None:
    # 8-11 chars: too short for SECRET_GENERIC, long enough for rule 10.
    findings = _scan('password = "s3cretpw1"\n')  # gitleaks:allow
    assert _rule_ids(findings) == ["HARDCODED_CREDENTIAL"]
    assert findings[0].severity == Severity.CRITICAL


def test_hardcoded_credential_long_value_is_generic_secret() -> None:
    findings = _scan('password = "hunter2hunter2"\n')  # gitleaks:allow
    assert _rule_ids(findings) == ["SECRET_GENERIC"]


def test_hardcoded_credential_skips_placeholder_and_short() -> None:
    assert _scan('password = "changeme123"\n') == []
    assert _scan('password = "abc123"\n') == []


# --- Rule 3: WEAK_PASSWORD_RULE ------------------------------------------


@pytest.mark.parametrize("line", ["if len(password) < 4:", "if password.length < 6 {"])
def test_weak_password_rule(line: str) -> None:
    findings = _scan(line + "\n")
    assert _rule_ids(findings) == ["WEAK_PASSWORD_RULE"]
    assert findings[0].severity == Severity.MEDIUM


@pytest.mark.parametrize(
    "line", ["if len(password) < 8:", "if len(password) < 12:", "if password.length < 8 {"]
)
def test_weak_password_rule_minimum_8_is_fine(line: str) -> None:
    assert _scan(line + "\n") == []


# --- Rule 4: DEBUG_MODE ---------------------------------------------------


@pytest.mark.parametrize("line", ["DEBUG = True", "debug=True", "app.run(debug=True)"])
def test_debug_mode(line: str) -> None:
    findings = _scan(line + "\n")
    assert _rule_ids(findings) == ["DEBUG_MODE"]
    assert findings[0].severity == Severity.LOW


@pytest.mark.parametrize("line", ["DEBUG = False", "debug: false", "DEBUG = os.getenv('X')"])
def test_debug_mode_off_not_flagged(line: str) -> None:
    assert _scan(line + "\n") == []


# --- Rule 5: CORS_WILDCARD -----------------------------------------------


@pytest.mark.parametrize("line", ['allow_origins=["*"]', "allow_origins=['*']"])
def test_cors_wildcard(line: str) -> None:
    findings = _scan(line + "\n")
    assert _rule_ids(findings) == ["CORS_WILDCARD"]
    assert findings[0].severity == Severity.MEDIUM


def test_cors_specific_origin_not_flagged() -> None:
    assert _scan('allow_origins=["https://example.com"]\n') == []


# --- Rule 6: SQL_INJECTION -----------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")',
        'cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)',
        'cursor.execute("SELECT * FROM users WHERE id = " + user_id)',
        'cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))',
    ],
)
def test_sql_injection_built_strings(line: str) -> None:
    findings = _scan(line + "\n")
    assert _rule_ids(findings) == ["SQL_INJECTION"]
    assert findings[0].severity == Severity.HIGH


def test_sql_injection_built_variable_passed_to_sink() -> None:
    content = 'query = f"SELECT * FROM users WHERE id = {user_id}"\ncursor.execute(query)\n'
    findings = _scan(content)
    assert _rule_ids(findings) == ["SQL_INJECTION"]
    assert findings[0].start_line == 2


def test_sql_injection_traces_request_data() -> None:
    content = (
        'user_id = request.args.get("id")\n'
        'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n'
    )
    findings = _scan(content)
    assert len(findings) == 1
    assert findings[0].confidence == Confidence.HIGH
    assert len(findings[0].trace) == 2
    assert findings[0].trace[0].line == 1
    assert findings[0].trace[1].line == 2


@pytest.mark.parametrize(
    "line",
    [
        'cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))',
        'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))',
        'cursor.execute("SELECT * FROM products")',
    ],
)
def test_sql_injection_parameterized_not_flagged(line: str) -> None:
    assert _scan(line + "\n") == []


# --- Rule 7: XSS ----------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "el.innerHTML = userInput;",
        "document.write(userInput);",
        "dangerouslySetInnerHTML={{ __html: userInput }}",
        "{{ user.bio|safe }}",
        "render_template_string(template)",
        'render_template_string(f"<p>{name}</p>")',
    ],
)
def test_xss_variable_values(line: str) -> None:
    findings = _scan(line + "\n")
    assert _rule_ids(findings) == ["XSS"]
    assert findings[0].severity == Severity.HIGH


@pytest.mark.parametrize(
    "line",
    [
        'el.innerHTML = "<b>hello</b>";',
        'document.write("hello");',
        "el.textContent = userInput;",
    ],
)
def test_xss_literals_not_flagged(line: str) -> None:
    assert _scan(line + "\n") == []


# --- Rule 8: COMMAND_INJECTION -------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "os.system(command)",
        "os.popen(command)",
        "subprocess.run(command, shell=True)",
        "eval(user_code)",
        "exec(user_code)",
    ],
)
def test_command_injection_variable_arguments(line: str) -> None:
    findings = _scan(line + "\n")
    assert _rule_ids(findings) == ["COMMAND_INJECTION"]
    assert findings[0].severity == Severity.HIGH


@pytest.mark.parametrize(
    "line",
    [
        'os.system("ls -la")',
        'subprocess.run("ls -la", shell=True)',
        'eval("1 + 1")',
        'subprocess.run(["ls", "-la"])',
    ],
)
def test_command_injection_literals_not_flagged(line: str) -> None:
    assert _scan(line + "\n") == []


# --- Rule 9: WEAK_CRYPTO --------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "hashlib.md5(data).hexdigest()",
        "hashlib.sha1(data).hexdigest()",
        "Crypto.Cipher.DES.new(key)",
        "ARC4.new(key)",
        "token = str(random.random())",
        "const password = Math.random().toString(36);",
    ],
)
def test_weak_crypto(line: str) -> None:
    findings = _scan(line + "\n")
    assert _rule_ids(findings) == ["WEAK_CRYPTO"]
    assert findings[0].severity == Severity.MEDIUM


@pytest.mark.parametrize(
    "line",
    [
        "hashlib.sha256(data).hexdigest()",
        "secrets.token_hex(16)",
        "value = random.random()",
    ],
)
def test_weak_crypto_strong_alternatives_not_flagged(line: str) -> None:
    assert _scan(line + "\n") == []


# --- Finding shape --------------------------------------------------------


def test_every_finding_has_location_snippet_and_guidance() -> None:
    content = (
        'API_KEY = "abcdefghijklmnop1234"\n'  # gitleaks:allow
        "DEBUG = True\n"
        "if len(password) < 4:\n"
        "    pass\n"
    )
    findings = _scan(content)
    assert len(findings) == 3
    for finding in findings:
        assert finding.file == "app.py"
        assert finding.start_line is not None and finding.start_line >= 1
        assert finding.end_line == finding.start_line
        assert finding.snippet
        assert len(finding.snippet) <= 500
        assert finding.fix_guidance is not None
        assert finding.fix_guidance.startswith("## Why it matters")
        assert "## How to fix" in finding.fix_guidance


# --- Demo replicas (CONTRACT.md targets) ----------------------------------


def test_demo_broken_replica_findings() -> None:
    outcome = run_code_scan(FIXTURES / "demo_broken", run_external=False)
    found = {(f.rule_id, f.severity.value, f.file, f.start_line) for f in outcome.findings}
    assert found == {
        ("SECRET_KNOWN_PREFIX", "critical", "app.py", 16),
        ("WEAK_PASSWORD_RULE", "medium", "app.py", 29),
        ("DEBUG_MODE", "low", "app.py", 18),
    }


def test_demo_fixed_replica_only_cors() -> None:
    outcome = run_code_scan(FIXTURES / "demo_fixed", run_external=False)
    assert [(f.rule_id, f.severity.value) for f in outcome.findings] == [
        ("CORS_WILDCARD", "medium")
    ]
