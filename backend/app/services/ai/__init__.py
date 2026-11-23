"""Model-assisted triage of findings and fix guidance.

`review_findings(findings, settings)` is the entry point; it sets
`ai_verdict` on every finding and appends fix snippets to `fix_guidance`.
"""

from .review import review_findings

__all__ = ["review_findings"]
