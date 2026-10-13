"""
Diagnostic Report Generator

Renders full diagnostic reports into clean consulting deliverables (HTML / PDF).
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)


def generate_html_report(report_data: dict) -> str:
    """Generate professional HTML report from synthesis output dictionary."""
    repo = report_data.get("repository", {})
    exec_sum = report_data.get("executive_summary", {})
    scorecard = report_data.get("readiness_scorecard", {})
    phased = report_data.get("phased_recommendations", {})
    disclaimers = report_data.get("disclaimers", {})

    overall_score = exec_sum.get("overall_readiness_score", 0.0)
    headline = exec_sum.get("headline", "Diagnostic Report")
    summary_text = exec_sum.get("summary_text", "")

    # Scorecard rows
    scorecard_html = ""
    for key, card in scorecard.items():
        score = card.get("readiness_score", 0)
        opp = card.get("opportunity_score", 0)
        label = card.get("readiness_label", "Medium")
        color = "#10B981" if score >= 7 else "#F59E0B" if score >= 4 else "#EF4444"

        scorecard_html += f"""
        <div style="background: #1e293b; border-radius: 8px; padding: 16px; margin-bottom: 12px; border: 1px solid #334155;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 600; color: #f8fafc; font-size: 1.1rem;">{card.get('domain_label', key)}</span>
                <span style="background: {color}22; color: {color}; border: 1px solid {color}; padding: 2px 10px; border-radius: 9999px; font-size: 0.85rem; font-weight: 600;">{label} (Readiness: {score}/10)</span>
            </div>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 8px;">{card.get('verdict', '')}</p>
            <div style="display: flex; gap: 16px; font-size: 0.85rem; color: #cbd5e1;">
                <span>AI Opportunity Potential: <strong>{opp}/10</strong></span>
            </div>
        </div>
        """

        # Phased recommendations
    phases_html = ""
    for phase_key, phase_data in phased.items():
        recs = phase_data.get("recommendations", [])
        recs_list = ""
        for r in recs:
            impact_color = "#EF4444" if r.get("impact") in ("critical", "very_high") else "#3B82F6"
            recs_list += f"""
            <div style="background: #0f172a; border-radius: 6px; padding: 12px; margin-top: 10px; border-left: 4px solid {impact_color};">
                <div style="font-weight: 600; color: #f8fafc; font-size: 0.95rem;">{r.get('title')}</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin: 4px 0 8px 0;">{r.get('description')}</div>
                <div style="display: flex; gap: 12px; font-size: 0.75rem; color: #64748b;">
                    <span>Effort: <strong style="color: #cbd5e1;">{r.get('effort')}</strong></span>
                    <span>Impact: <strong style="color: {impact_color};">{r.get('impact', '').upper()}</strong></span>
                    <span>AI Relevance: <strong style="color: #cbd5e1;">{r.get('ai_relevance', '')}</strong></span>
                </div>
            </div>
            """

        phases_html += f"""
        <div style="margin-bottom: 24px;">
            <h3 style="color: #38bdf8; font-size: 1.15rem; margin-bottom: 4px;">{phase_data.get('phase_label')}</h3>
            <p style="color: #64748b; font-size: 0.85rem; margin-bottom: 8px;">{phase_data.get('phase_description')} • Estimated Effort: {phase_data.get('estimated_effort')}</p>
            {recs_list}
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI-SDLC Compass Report — {repo.get('name', 'Repository')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #0b0f19;
            color: #f1f5f9;
            margin: 0;
            padding: 40px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 1px solid #1e293b;
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}
        .badge {{
            display: inline-block;
            background: #6366f122;
            color: #818cf8;
            border: 1px solid #6366f1;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .card {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 28px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">AI-SDLC COMPASS DIAGNOSTIC REPORT</span>
            <h1 style="font-size: 2rem; margin: 8px 0; color: #ffffff;">{repo.get('name', 'Repository')}</h1>
            <p style="color: #64748b; margin: 0;">Branch: {repo.get('branch', 'main')} | Commit: {repo.get('commit_hash', 'latest')} | Stack: {', '.join(repo.get('languages', []))} ({', '.join(repo.get('frameworks', []))})</p>
        </div>

        <div class="card" style="border-left: 4px solid #6366f1;">
            <div style="font-size: 0.8rem; text-transform: uppercase; color: #818cf8; font-weight: 700; letter-spacing: 0.05em; margin-bottom: 4px;">Executive Verdict</div>
            <h2 style="margin: 0 0 12px 0; font-size: 1.4rem; color: #ffffff;">{headline}</h2>
            <p style="color: #cbd5e1; font-size: 1rem; margin: 0 0 16px 0;">{summary_text}</p>
            <div style="display: inline-block; background: #1e293b; padding: 6px 16px; border-radius: 8px; font-weight: 600;">
                Overall AI Readiness Index: <span style="color: #38bdf8; font-size: 1.2rem;">{overall_score} / 10</span>
            </div>
        </div>

        <div class="card">
            <h2 style="font-size: 1.25rem; margin-top: 0; color: #f8fafc; border-bottom: 1px solid #1e293b; padding-bottom: 12px;">Impact Evidence Scorecard</h2>
            {scorecard_html}
        </div>

        <div class="card">
            <h2 style="font-size: 1.25rem; margin-top: 0; color: #f8fafc; border-bottom: 1px solid #1e293b; padding-bottom: 12px;">Phased AI Adoption Roadmap</h2>
            {phases_html}
        </div>

        <div style="color: #475569; font-size: 0.75rem; text-align: center; margin-top: 40px; border-top: 1px solid #1e293b; padding-top: 20px;">
            {disclaimers.get('accuracy', '')} • {disclaimers.get('affiliation', '')}
        </div>
    </div>
</body>
</html>
    """
    return html


def save_report_files(session_id: str, report_data: dict) -> Path:
    """Save HTML and return file path."""
    reports_dir = settings.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)

    html_content = generate_html_report(report_data)
    html_file = reports_dir / f"report_{session_id}.html"
    html_file.write_text(html_content, encoding="utf-8")

    # Attempt PDF rendering via WeasyPrint if available
    try:
        from weasyprint import HTML
        pdf_file = reports_dir / f"report_{session_id}.pdf"
        HTML(string=html_content).write_pdf(pdf_file)
        logger.info(f"Generated PDF report at {pdf_file}")
        return pdf_file
    except Exception as ex:
        logger.info(f"PDF generation skipped ({ex}); saved HTML report at {html_file}")
        return html_file
