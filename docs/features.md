# Features

Status values: **Not started**, **In progress**, **Done**. Update the status in
the same PR that changes it.

| # | Feature | Description | Status |
|---|---|---|---|
| 0 | Project foundation | Repo structure, backend and frontend skeletons, design system, CI, security baseline | In progress |
| 1 | One-click audit run | Add a GitHub repo or zip plus the live URL, press Run, follow progress | Not started |
| 2 | Code scanner with evidence | Semgrep, gitleaks and OSV scans normalised into Findings with file, line, snippet and data-flow trace | Not started |
| 3 | Vibe-coding checks | Supabase RLS, exposed keys, open Firebase rules, unauthenticated routes | Not started |
| 4 | Live app security checks | Header, TLS, exposure and auth checks against the live URL, only after domain ownership verification, through an SSRF-safe client | Not started |
| 5 | Journey runner | Scripted user journeys against the live app with screenshots as evidence | Not started |
| 6 | Verdict and risk score | Launch / Fix first / Do not launch verdict and a 0-10 risk score derived from findings | Not started |
| 7 | Fix-first list | Ordered list of the findings to fix before launch | Not started |
| 8 | Review and fix suggestions | LLM review (Gemini, Groq fallback, rule-based fallback) that confirms findings and proposes fixes; every claim must quote code | Not started |
| 9 | Fix-and-verify rerun | Re-run the affected checks after a fix and mark findings fixed | Not started |
| 10 | Shareable report and PDF | Read-only shareable report link and PDF export | Not started |
