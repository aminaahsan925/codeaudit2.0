# Fixtures

Small, deliberately vulnerable sample apps and files used by scanner tests.

Rules:

- Fixtures are **data**. Never install their dependencies, run their scripts or
  import them from application code.
- Any "secret" in a fixture must be an obviously fake value. Scenario folders
  (`fixtures/<scenario>/`) are allowlisted in `.gitleaks.toml`; secrets
  anywhere else in the repo are still caught.
- One folder per scenario, with a short `README.md` describing the expected
  findings (rule, file, line) so tests can assert on them.
