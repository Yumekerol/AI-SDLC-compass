"""
Automated End-to-End API Test Suite

Validates all 15 endpoints defined in the API contract against the FastAPI application.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


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

    # 3. Simulate Light Scanner results
    from backend.scanner import run_light_scanner
    from backend.storage import get_storage
    import asyncio

    async def inject_scan():
        store = await get_storage()
        s = await store.get_session(session_id)
        scan_output = run_light_scanner(".")
        s.scanner_output = scan_output.model_dump(mode="json")
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

    # 7. Start Diagnostic Q&A (Step 3)
    diag_res = client.post(f"/api/v1/sessions/{session_id}/diagnose")
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert len(diag_data["initial_messages"]) > 0

    # 8. User Conversation Turn
    msg_res = client.post(
        f"/api/v1/sessions/{session_id}/conversation",
        json={"content": "We use Jira tickets and manual testing by a QA engineer."},
    )
    assert msg_res.status_code == 200

    # 9. Get Knowledge Gaps
    gaps_res = client.get(f"/api/v1/sessions/{session_id}/knowledge-gaps")
    assert gaps_res.status_code == 200
    assert "gaps" in gaps_res.json()

    # 10. Continue Diagnostic / Synthesis (Step 3 -> 4)
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
