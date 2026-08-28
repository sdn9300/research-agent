from unittest.mock import MagicMock
from usher.adapters.generic import GenericATSAdapter
from usher.schemas import CandidateProfile, FieldResolution, JobApplicationTarget, SubmissionMode

def make_job(**kwargs):
    defaults = {
        "job_id": "gen_404",
        "title": "Staff Software Engineer",
        "company": "StartupX",
        "apply_url": "https://careers.startupx.com/jobs/apply/404",
        "source_platform": "generic_ats_unknown"
    }
    defaults.update(kwargs)
    return JobApplicationTarget(**defaults)

def test_generic_ats_detect():
    adapter = GenericATSAdapter()
    assert adapter.detect(MagicMock(), "https://careers.startupx.com/apply") is True

def test_generic_ats_never_auto_submits():
    """
    PAA-EP-1.0 §5 & PAA-IP-1.0 §5:
    GenericATSAdapter fallback never exceeds DRAFT_PENDING_REVIEW — it is never eligible for AUTO mode.
    """
    adapter = GenericATSAdapter()
    page = MagicMock()
    page.locator.return_value.count.return_value = 0 # No signup wall

    resolutions = [
        FieldResolution(
            field_label="Email",
            resolution_tier="tier0_selector",
            resolved_value="test@example.com",
            confidence=1.0,
            source="candidate_profile"
        )
    ]

    job = make_job()
    # Even when mode is AUTO, GenericATSAdapter holds at DRAFT_PENDING_REVIEW
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, resolutions)
    assert res.status == "DRAFT_PENDING_REVIEW"

def test_generic_ats_signup_wall_triggers_manual():
    """EC-PAA-SUB-03: Signup wall on generic portal routes to MANUAL_REQUIRED."""
    adapter = GenericATSAdapter()
    page = MagicMock()

    def mock_locator(sel):
        mock_el = MagicMock()
        mock_el.count.return_value = 1 if "password" in sel else 0
        return mock_el

    page.locator.side_effect = mock_locator

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.DRAFT, job, None, [])
    assert res.status == "MANUAL_REQUIRED"
    assert res.error_code == "ACCOUNT_CREATION_REQUIRED"
