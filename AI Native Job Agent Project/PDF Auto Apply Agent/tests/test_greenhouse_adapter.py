from unittest.mock import MagicMock
from usher.adapters.greenhouse import GreenhouseAdapter
from usher.schemas import CandidateProfile, FieldResolution, JobApplicationTarget, SubmissionMode

def make_job(**kwargs):
    defaults = {
        "job_id": "gh_101",
        "title": "Machine Learning Engineer",
        "company": "Stripe",
        "apply_url": "https://boards.greenhouse.io/stripe/jobs/101",
        "source_platform": "greenhouse"
    }
    defaults.update(kwargs)
    return JobApplicationTarget(**defaults)

def test_greenhouse_detect():
    adapter = GreenhouseAdapter()
    assert adapter.detect(MagicMock(), "https://boards.greenhouse.io/stripe/jobs/101") is True
    assert adapter.detect(MagicMock(), "https://grnh.se/abc123xyz") is True
    assert adapter.detect(MagicMock(), "https://jobs.lever.co/example/123") is False

def test_greenhouse_submit_or_hold_draft():
    adapter = GreenhouseAdapter()
    page = MagicMock()
    job = make_job()

    res = adapter.submit_or_hold(page, SubmissionMode.DRAFT, job, None, [])
    assert res.status == "DRAFT_PENDING_REVIEW"
    assert res.job.job_id == "gh_101"

def test_greenhouse_auto_mode_submits():
    adapter = GreenhouseAdapter()
    page = MagicMock()

    mock_btn = MagicMock()
    mock_btn.count.return_value = 1
    page.locator.return_value = mock_btn

    resolutions = [
        FieldResolution(
            field_label="First Name",
            resolution_tier="tier0_selector",
            resolved_value="Soumyadeep",
            confidence=1.0,
            source="candidate_profile"
        )
    ]

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, resolutions)
    assert res.status == "SUBMITTED"
