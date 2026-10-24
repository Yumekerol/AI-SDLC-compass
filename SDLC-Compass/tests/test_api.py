"""
Automated End-to-End API Test Suite

Validates all 15 endpoints defined in the API contract against the FastAPI application.
"""

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


# A minimal but complete fake Agent Service response, matching exactly what
# backend/orchestrator/supervisor.py expects back from /pipeline/start and
# /pipeline/reply — see SDLC-Compass/agents/src/synthesizer.py for the real
# schema this mirrors. Tests mock the Agent Service at this HTTP boundary
# rather than needing a live service + a real Ollama model.
FAKE_NEEDS_INPUT = {
    "status": "needs_input",
    "role": "requirements_design",
    "question": "What is your team's sprint cadence?",
}

FAKE_COMPLETE = {
    "status": "complete",
    "reports": [
        {
            "role": "requirements_design",
            "label": "Requirements & Design",
            "findings": [
                {"claim": "No ADRs found in the repo.", "evidence_paths": [], "confidence": "low"}
            ],
            "questions_asked": ["What is your team's sprint cadence?"],
            "summary": "Requirements are informal.",
            "status": "complete",
        },
        {
            "role": "code_refactoring",
            "label": "Code & Refactoring",
            "findings": [],
            "questions_asked": [],
            "summary": "Codebase is reasonably organized.",
            "status": "complete",
        },
        {
            "role": "qa_testing",
            "label": "QA & Testing",
            "findings": [],
            "questions_asked": [],
            "summary": "Unit tests present, no integration tests.",
            "status": "complete",
        },
        {
            "role": "devops_monitoring",
            "label": "DevOps & Monitoring",
            "findings": [],
            "questions_asked": [],
            "summary": "CI pipeline present.",
            "status": "complete",
        },
    ],
    "synthesis": {
        "executive_summary": {
            "headline": "Early-stage AI readiness",
            "overall_readiness": "medium",
            "overall_readiness_score": 5.0,
            "summary_text": "The repository shows a mix of strengths and gaps across domains.",
        },
        "readiness_scorecard": {
            "requirements_design": {
                "domain": "requirements_design",
                "domain_label": "Requirements & Design",
                "readiness_score": 4,
                "opportunity_score": 7,
                "readiness_label": "Developing",
                "verdict": "Requirements are informal; little written evidence.",
            }
        },
        "phased_recommendations": {
            "phase_1_foundation": {
                "phase_label": "Foundation",
                "phase_description": "Prerequisites that block everything else.",
                "estimated_effort": "2 weeks",
                "recommendations": [
                    {
                        "id": "rec-1",
                        "title": "Adopt lightweight ADRs",
                        "domain": "requirements_design",
                        "description": "Record architectural decisions as they're made.",
                        "effort": "low",
                        "impact": "high",
                        "risk_level": "low",
                        "prerequisites": [],
                        "ai_relevance": "Gives future AI tools real context to work from.",
                        "is_foundation": True,
                    }
                ],
            },
            "phase_2_quick_wins": {
                "phase_label": "Quick wins",
                "phase_description": "",
                "estimated_effort": "unknown",
                "recommendations": [],
            },
            "phase_3_advanced": {
                "phase_label": "Advanced AI integration",
                "phase_description": "",
                "estimated_effort": "unknown",
                "recommendations": [],
            },
        },
        "disclaimers": {
            "scope": "This diagnostic reflects what the repository and the answers provided reveal.",
            "accuracy": "Findings are produced by an AI reviewer and may contain errors.",
            "affiliation": "AI-SDLC Compass is not affiliated with any tool or vendor it mentions.",
        },
    },
}


def _wait_until_not_processing(session_id: str, timeout_s: float = 5.0) -> dict:
    """Poll GET /conversation until the background task finishes, the same
    way the real frontend does."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        res = client.get(f"/api/v1/sessions/{session_id}/conversation")
        assert res.status_code == 200
        data = res.json()
        if not data["processing"]:
            return data
        time.sleep(0.05)
    raise AssertionError(f"Session {session_id} still processing after {timeout_s}s")


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_create_session_requires_consent():
    response = client.post(
        "/api/v1/sessions",
        json={"source_type": "git", "git_url": "https://github.com/fastapi/fastapi", "consent_given": False},
    )
    assert response.status_code == 400
    assert "Privacy and consent" in response.json()["detail"]


def test_create_session_success():
    response = client.post(
        "/api/v1/sessions",
        json={"source_type": "git", "git_url": "https://github.com/fastapi/fastapi", "consent_given": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "created"
    return data["session_id"]


def test_full_diagnostic_api_lifecycle():
    # 1. Create Session
    create_res = client.post(
        "/api/v1/sessions",
        json={"source_type": "git", "git_url": "https://github.com/fastapi/fastapi", "consent_given": True},
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["session_id"]

    # 2. Get Session status
    get_res = client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == session_id

    # 3. Simulate Light Scanner results.
    # The real scan is now done by the separate scanner microservice
    # (SDLC-Compass/scanner/), called over HTTP by backend/api/scan.py — not
    # an in-process `backend.scanner` module. This test doesn't need to
    # exercise that HTTP call; it only needs scanner_output to already exist
    # so later steps (signal review, diagnose) have something to work with.
    from backend.storage import get_storage
    import asyncio

    MINIMAL_SCAN_OUTPUT = {
        "repository": {"name": "fastapi", "branch": "main", "commit_hash": "abc1234"},
        "scope": {},
        "languages": {"data": {"primary_language": "Python"}},
        "size_and_structure": {"data": {"code_files": 42}},
        "stack_and_tooling": {"data": {}},
        "cicd_and_operations": {"data": {}},
        "quality_indicators": {"data": {}},
        "warnings_and_gaps": {"data": {}},
    }

    async def inject_scan():
        store = await get_storage()
        s = await store.get_session(session_id)
        s.scanner_output = MINIMAL_SCAN_OUTPUT
        s.status = "awaiting_signal_review"
        await store.update_session(s)

    asyncio.run(inject_scan())

    # 4. Get Review Signals (Step 2)
    sig_res = client.get(f"/api/v1/sessions/{session_id}/signals")
    assert sig_res.status_code == 200
    sig_data = sig_res.json()
    assert "signal_groups" in sig_data
    assert "languages" in sig_data["signal_groups"]
    assert "warnings_and_gaps" in sig_data["signal_groups"]

    # 5. Patch Signals (Step 2 edit)
    patch_res = client.patch(
        f"/api/v1/sessions/{session_id}/signals",
        json={"signal_groups": {"stack_and_tooling": {"data": {"frameworks": ["FastAPI", "React"]}}}},
    )
    assert patch_res.status_code == 200

    # 6. Confirm Signals (Step 2 -> 3)
    confirm_res = client.post(f"/api/v1/sessions/{session_id}/confirm-signals")
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "awaiting_team_context"

    # The real specialist pipeline lives in a separate Agent Service
    # (SDLC-Compass/agents/), called over HTTP by Supervisor._call_agents.
    # Mock that one boundary: /diagnose triggers the first call (a
    # clarifying question), /conversation's reply triggers the second
    # (the pipeline finishes and synthesizes).
    with patch(
        "backend.orchestrator.supervisor.Supervisor._call_agents",
        new_callable=AsyncMock,
        side_effect=[FAKE_NEEDS_INPUT, FAKE_COMPLETE],
    ):
        # 7. Start Diagnostic Q&A (Step 3) — returns immediately; the
        # pipeline call happens in a background task.
        diag_res = client.post(f"/api/v1/sessions/{session_id}/diagnose")
        assert diag_res.status_code == 200
        diag_data = diag_res.json()
        assert diag_data["processing"] is True
        assert len(diag_data["initial_messages"]) > 0

        conv_data = _wait_until_not_processing(session_id)
        # Welcome message + the specialist's clarifying question
        assert len(conv_data["messages"]) >= 2
        assert conv_data["status"] == "diagnosing"

        # 8. User Conversation Turn — answers the clarifying question;
        # this is the turn that completes the pipeline.
        msg_res = client.post(
            f"/api/v1/sessions/{session_id}/conversation",
            json={"content": "We use Jira tickets and manual testing by a QA engineer."},
        )
        assert msg_res.status_code == 200
        assert msg_res.json()["processing"] is True

        conv_data = _wait_until_not_processing(session_id)
        assert conv_data["status"] == "report_ready"

    # 9. Get Knowledge Gaps — fed by the specialists' own low-confidence
    # findings and the questions they had to ask (see FAKE_COMPLETE above).
    gaps_res = client.get(f"/api/v1/sessions/{session_id}/knowledge-gaps")
    assert gaps_res.status_code == 200
    gaps = gaps_res.json()["gaps"]
    assert any(descriptions for descriptions in gaps.values())

    # 10. Continue Diagnostic (Step 3 -> 4) — the pipeline already
    # synthesized as part of step 8; this just confirms the report is ready.
    synth_res = client.post(f"/api/v1/sessions/{session_id}/continue-diagnostic")
    assert synth_res.status_code == 200
    assert synth_res.json()["report_ready"] is True

    # 11. Get Final Report JSON (Step 4)
    report_res = client.get(f"/api/v1/sessions/{session_id}/report")
    assert report_res.status_code == 200
    report_data = report_res.json()
    assert "executive_summary" in report_data
    assert "readiness_scorecard" in report_data
    assert "phased_recommendations" in report_data

    # 12. View HTML Report
    html_res = client.get(f"/api/v1/sessions/{session_id}/report/html")
    assert html_res.status_code == 200
    assert "<html" in html_res.text.lower()
    assert "AI-SDLC COMPASS" in html_res.text

    print("ALL 12 LIFECYCLE TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    test_health_check()
    test_create_session_requires_consent()
    test_full_diagnostic_api_lifecycle()
