# Features

Status values: **Not started**, **In progress**, **Done**. Update the status in
the same PR that changes it.

| # | Feature | Description | Status |
|---|---|---|---|
| 0 | Project foundation | Repo structure, backend and frontend skeletons, design system, CI, security baseline | In progress |
| 1 | One-click audit run | Add a GitHub repo or zip plus the live URL, press Run, follow progress | Done |
| 2 | Code scanner with evidence | Semgrep, gitleaks and OSV scans normalised into Findings with file, line, snippet and data-flow trace | Done |
| 3 | Vibe-coding checks | Supabase RLS, exposed keys, open Firebase rules, unauthenticated routes | Done |
| 4 | Live app security checks | Header, TLS, exposure and auth checks against the live URL, only after domain ownership verification, through an SSRF-safe client | Done |
| 5 | Journey runner | Scripted user journeys against the live app with screenshots as evidence | Done |
| 6 | Verdict and risk score | Launch / Fix first / Do not launch verdict and a 0-10 risk score derived from findings | Done |
| 7 | Fix-first list | Ordered list of the findings to fix before launch | Done |
| 8 | Review and fix suggestions | LLM review (Gemini, Groq fallback, rule-based fallback) that confirms findings and proposes fixes; every claim must quote code | Done |
| 9 | Fix-and-verify rerun | Re-run the affected checks after a fix and mark findings fixed | Done |
| 10 | Shareable report and PDF | Read-only shareable report link and PDF export | Done |
| 11 | Google sign-in | Google OAuth2 login with signed sessions; demo sign-in fallback while Google is unconfigured; runs owned by the signed-in user's email | Done |
| 12 | Local CLI | Run an audit from the terminal (`python -m app.cli run --path ...`), no web UI and no database; live checks and journey only with `--confirm-owns-domain` | Done |
