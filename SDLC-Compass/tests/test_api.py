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
# /pipeline/reply â€” see SDLC-Compass/agents/src/synthesizer.py for the real
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
    # (SDLC-Compass/scanner/), called over HTTP by backend/api/scan.py â€” not
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
        # 7. Start Diagnostic Q&A (Step 3) â€” returns immediately; the
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

        # 8. User Conversation Turn â€” answers the clarifying question;
        # this is the turn that completes the pipeline.
        msg_res = client.post(
            f"/api/v1/sessions/{session_id}/conversation",
            json={"content": "We use Jira tickets and manual testing by a QA engineer."},
        )
        assert msg_res.status_code == 200
        assert msg_res.json()["processing"] is True

        conv_data = _wait_until_not_processing(session_id)
        assert conv_data["status"] == "report_ready"

    # 8b. Notifications - a specialist_question one from the clarifying question and
    # a report_ready one from the pipeline finishing should both be recorded.
    notif_res = client.get(f"/api/v1/sessions/{session_id}/notifications")
    assert notif_res.status_code == 200
    notifications = notif_res.json()["notifications"]
    assert [n["type"] for n in notifications] == ["specialist_question", "report_ready"]
    assert all(n["read"] is False for n in notifications)
    # New fields: level and created_at must be present on every notification.
    assert all("level" in n for n in notifications)
    assert all("created_at" in n for n in notifications)
    assert notifications[0]["level"] == "warning"   # specialist_question
    assert notifications[1]["level"] == "success"   # report_ready

    unread_res = client.get(f"/api/v1/sessions/{session_id}/notifications?unread_only=true")
    assert len(unread_res.json()["notifications"]) == 2

    first_id = notifications[0]["id"]
    read_res = client.post(f"/api/v1/sessions/{session_id}/notifications/{first_id}/read")
    assert read_res.status_code == 200
    assert read_res.json()["notification"]["read"] is True

    unread_res = client.get(f"/api/v1/sessions/{session_id}/notifications?unread_only=true")
    assert len(unread_res.json()["notifications"]) == 1

    read_all_res = client.post(f"/api/v1/sessions/{session_id}/notifications/read-all")
    assert read_all_res.status_code == 200
    assert all(n["read"] for n in read_all_res.json()["notifications"])

    # 8c. Delete individual notification and clear all notifications
    second_id = notifications[1]["id"]
    del_res = client.delete(f"/api/v1/sessions/{session_id}/notifications/{second_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    remaining_res = client.get(f"/api/v1/sessions/{session_id}/notifications")
    assert len(remaining_res.json()["notifications"]) == 1

    clear_res = client.delete(f"/api/v1/sessions/{session_id}/notifications")
    assert clear_res.status_code == 200
    assert clear_res.json()["notifications"] == []

    final_res = client.get(f"/api/v1/sessions/{session_id}/notifications")
    assert final_res.json()["notifications"] == []

    # 9. Get Knowledge Gaps â€” fed by the specialists' own low-confidence
    # findings and the questions they had to ask (see FAKE_COMPLETE above).
    gaps_res = client.get(f"/api/v1/sessions/{session_id}/knowledge-gaps")
    assert gaps_res.status_code == 200
    gaps = gaps_res.json()["gaps"]
    assert any(descriptions for descriptions in gaps.values())

    # 10. Continue Diagnostic (Step 3 -> 4) â€” the pipeline already
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


def test_agents_failure_creates_notification():
    """A failed pipeline turn must leave a notification, not just an error
    status: someone who chose "notify me when done" isn't watching the page."""
    import httpx

    create_res = client.post(
        "/api/v1/sessions",
        json={"source_type": "git", "git_url": "https://github.com/fastapi/fastapi", "consent_given": True},
    )
    session_id = create_res.json()["session_id"]

    with patch(
        "backend.orchestrator.supervisor.Supervisor._call_agents",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("agents down"),
    ):
        client.post(f"/api/v1/sessions/{session_id}/diagnose")
        conv = _wait_until_not_processing(session_id)

    assert conv["status"] == "error"
    notifications = client.get(f"/api/v1/sessions/{session_id}/notifications").json()["notifications"]
    failed = [n for n in notifications if n["type"] == "agents_failed"]
    assert len(failed) == 1
    assert failed[0]["level"] == "error"
    assert "agents down" in failed[0]["message"]


def _new_diagnosing_session() -> str:
    """A session that looks like it has a pipeline turn in flight."""
    import asyncio

    from backend.storage import get_storage

    session_id = client.post(
        "/api/v1/sessions",
        json={"source_type": "git", "git_url": "https://github.com/fastapi/fastapi", "consent_given": True},
    ).json()["session_id"]

    async def mark_running():
        store = await get_storage()
        s = await store.get_session(session_id)
        s.status = "diagnosing"
        s.processing = True
        await store.update_session(s)

    asyncio.run(mark_running())
    return session_id


def test_cancel_diagnostic():
    session_id = _new_diagnosing_session()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as agents_post:
        res = client.post(f"/api/v1/sessions/{session_id}/cancel-diagnostic")
    assert res.status_code == 200
    assert agents_post.await_args.args[0].endswith("/pipeline/cancel")
    assert agents_post.await_args.kwargs["json"] == {"session_id": session_id}

    conv = client.get(f"/api/v1/sessions/{session_id}/conversation").json()
    assert conv["status"] == "cancelled"
    assert conv["processing"] is False
    assert "Diagnostic stopped" in conv["messages"][-1]["content"]

    # Nothing left to cancel.
    assert client.post(f"/api/v1/sessions/{session_id}/cancel-diagnostic").status_code == 409


def test_starting_a_diagnostic_cancels_abandoned_ones():
    """The local model serves one request at a time, so an abandoned run
    would slow the new one down."""
    abandoned = _new_diagnosing_session()
    fresh = client.post(
        "/api/v1/sessions",
        json={"source_type": "git", "git_url": "https://github.com/fastapi/fastapi", "consent_given": True},
    ).json()["session_id"]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock), patch(
        "backend.orchestrator.supervisor.Supervisor._call_agents",
        new_callable=AsyncMock,
        return_value=FAKE_NEEDS_INPUT,
    ):
        client.post(f"/api/v1/sessions/{fresh}/diagnose")
        _wait_until_not_processing(fresh)

    assert client.get(f"/api/v1/sessions/{abandoned}/conversation").json()["status"] == "cancelled"
    assert client.get(f"/api/v1/sessions/{fresh}/conversation").json()["status"] == "diagnosing"


def test_cancelled_turn_does_not_record_an_error():
    """The turn that fails because it was cancelled must leave the
    cancellation alone: no error status, no "agents failed" notification."""
    import asyncio

    import httpx

    from backend.orchestrator.supervisor import Supervisor
    from backend.storage import get_storage

    session_id = _new_diagnosing_session()

    async def run():
        store = await get_storage()
        supervisor = Supervisor(store)

        async def cancelled_mid_turn(path, payload):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock):
                await supervisor.cancel_diagnostic(await store.get_session(session_id))
            raise httpx.HTTPStatusError("409 Pipeline cancelled", request=None, response=None)

        with patch.object(Supervisor, "_call_agents", side_effect=cancelled_mid_turn):
            await supervisor.continue_user_turn(session_id, "an answer")

    asyncio.run(run())

    conv = client.get(f"/api/v1/sessions/{session_id}/conversation").json()
    assert conv["status"] == "cancelled"
    notifications = client.get(f"/api/v1/sessions/{session_id}/notifications").json()["notifications"]
    assert not [n for n in notifications if n["type"] == "agents_failed"]


def _fake_status_response(status_code: int, body: dict | None = None):
    import httpx

    return httpx.Response(status_code, json=body or {}, request=httpx.Request("GET", "http://agents/pipeline/status"))


def test_pipeline_progress_mapping():
    """Supervisor.get_pipeline_progress turns the Agent Service's
    /pipeline/status into the phase/step shape the conversation poll exposes."""
    import asyncio

    from backend.orchestrator.supervisor import Supervisor

    supervisor = Supervisor(store=None)

    def progress_for(response):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=response):
            return asyncio.run(supervisor.get_pipeline_progress("s1"))

    # Still cloning: the Agent Service has no state for the session yet.
    assert progress_for(_fake_status_response(404))["phase"] == "starting"

    running = progress_for(_fake_status_response(200, {
        "status": "running", "current_index": 1, "current_role": "code_refactoring",
        "current_label": "Code & Refactoring", "completed_reports_count": 1,
    }))
    assert running == {
        "phase": "specialist", "step": 2, "total_steps": 4, "current_role": "code_refactoring",
        "current_label": "Code & Refactoring", "completed_specialists": 1,
    }

    waiting = progress_for(_fake_status_response(200, {
        "status": "needs_input", "current_index": 2, "current_role": "qa_testing",
        "current_label": "QA & Testing", "completed_reports_count": 2,
    }))
    assert (waiting["phase"], waiting["step"]) == ("waiting_for_answer", 3)

    synthesizing = progress_for(_fake_status_response(200, {
        "status": "running", "current_index": 3, "current_role": "devops_monitoring",
        "current_label": "DevOps & Monitoring", "completed_reports_count": 4,
    }))
    assert synthesizing["phase"] == "synthesizing"

    # The Agent Service being unreachable must not break the conversation poll.
    import httpx

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=httpx.ConnectError("down")):
        assert asyncio.run(supervisor.get_pipeline_progress("s1")) is None


if __name__ == "__main__":
    test_health_check()
    test_create_session_requires_consent()
    test_full_diagnostic_api_lifecycle()
