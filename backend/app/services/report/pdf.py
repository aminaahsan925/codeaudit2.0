"""PDF download for a Launch Report, built with reportlab.

Shows the verdict and risk score, counts by severity, the fix-first
findings table, journey steps, and the resolved section on rerun reports.
No em dash in the PDF text.
"""

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.audit_run import Verdict
from app.schemas.finding import Finding, FindingEngine
from app.schemas.report import ReportResponse

VERDICT_LABELS = {
    Verdict.LAUNCH: "Launch",
    Verdict.FIX_FIRST: "Fix first",
    Verdict.DO_NOT_LAUNCH: "Do not launch",
}


def _text(value: object) -> str:
    return escape(str(value or ""))


def _where(finding: Finding) -> str:
    if finding.file:
        where = finding.file
        if finding.start_line:
            where += f":{finding.start_line}"
        return where
    if finding.engine == FindingEngine.JOURNEY and finding.evidence.notes:
        return finding.evidence.notes
    if finding.evidence.http is not None:
        return finding.evidence.http.url
    return ""


def _severity_label(finding: Finding) -> str:
    return finding.severity.value.capitalize()


def render_report_pdf(report: ReportResponse) -> bytes:
    """Build the report PDF from an assembled `ReportResponse`."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"LaunchAudit Report {report.run.id}",
        author="A&H Systems",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("LaunchTitle", parent=styles["Title"], fontSize=22, spaceAfter=4)
    heading_style = ParagraphStyle(
        "LaunchHeading", parent=styles["Heading2"], fontSize=14, spaceBefore=14
    )
    body_style = ParagraphStyle("LaunchBody", parent=styles["BodyText"], fontSize=10, leading=14)
    cell_style = ParagraphStyle("LaunchCell", parent=styles["BodyText"], fontSize=9, leading=12)

    counts = report.counts
    run = report.run

    story: list = []
    story.append(Paragraph("LaunchAudit Report", title_style))
    story.append(Paragraph("A&amp;H Systems", body_style))
    story.append(Spacer(1, 6))
    verdict = VERDICT_LABELS.get(run.verdict, "Not scored yet") if run.verdict else "Not scored yet"
    risk_text = f"{run.risk_score} / 10" if run.risk_score is not None else "Not scored yet"
    story.append(Paragraph(f"Verdict: <b>{_text(verdict)}</b>", body_style))
    story.append(Paragraph(f"Risk score: <b>{_text(risk_text)}</b>", body_style))
    story.append(
        Paragraph(
            f"Critical: {counts.get('critical', 0)} | High: {counts.get('high', 0)} | "
            f"Medium: {counts.get('medium', 0)} | Low: {counts.get('low', 0)}",
            body_style,
        )
    )
    story.append(Paragraph(f"Report ID: {run.id}", body_style))
    story.append(Paragraph(f"Project: {_text(run.project_name)}", body_style))
    if run.started_at is not None:
        story.append(Paragraph(f"Started: {_text(run.started_at.isoformat())}", body_style))
    if report.previous_risk_score is not None:
        change = report.score_change
        change_text = f"{change:+.1f}" if change is not None else "n/a"
        story.append(
            Paragraph(
                f"Rerun. Previous risk score: {report.previous_risk_score} / 10. "
                f"Risk change: {change_text}",
                body_style,
            )
        )

    story.append(Paragraph("Findings", heading_style))
    if report.previous_risk_score is not None:
        story.append(
            Paragraph(
                "The findings below are still open or new in this run.",
                body_style,
            )
        )
    if report.findings:
        rows = [["Risk", "Finding", "Where", "Fix"]]
        for finding in report.findings:
            rows.append(
                [
                    Paragraph(_text(_severity_label(finding)), cell_style),
                    Paragraph(_text(finding.title), cell_style),
                    Paragraph(_text(_where(finding)), cell_style),
                    Paragraph(_text(finding.fix_guidance or ""), cell_style),
                ]
            )
        table = Table(
            rows,
            colWidths=[16 * mm, 42 * mm, 42 * mm, 74 * mm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No problems found.", body_style))

    if report.resolved_findings:
        story.append(Paragraph("Resolved since the last run", heading_style))
        rows = [["Risk", "Finding", "Where"]]
        for finding in report.resolved_findings:
            rows.append(
                [
                    Paragraph(_text(_severity_label(finding)), cell_style),
                    Paragraph(_text(finding.title), cell_style),
                    Paragraph(_text(_where(finding)), cell_style),
                ]
            )
        table = Table(rows, colWidths=[20 * mm, 70 * mm, 84 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)

    if report.journey_steps:
        story.append(Paragraph("Journey test", heading_style))
        rows = [["Step", "Status", "Detail"]]
        for step in report.journey_steps:
            rows.append(
                [
                    Paragraph(_text(step.name), cell_style),
                    Paragraph(_text(step.status), cell_style),
                    Paragraph(_text(step.error or ""), cell_style),
                ]
            )
        table = Table(rows, colWidths=[30 * mm, 22 * mm, 122 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(Spacer(1, 6))
        story.append(table)

    doc.build(story)
    return buffer.getvalue()
