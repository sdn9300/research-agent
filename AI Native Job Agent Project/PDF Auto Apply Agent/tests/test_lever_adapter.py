from unittest.mock import MagicMock
from usher.adapters.lever import LeverAdapter
from usher.schemas import CandidateProfile, FieldResolution, JobApplicationTarget, SubmissionMode

def make_job(**kwargs):
    defaults = {
        "job_id": "lev_202",
        "title": "Backend AI Developer",
        "company": "Figma",
        "apply_url": "https://jobs.lever.co/figma/202",
        "source_platform": "lever"
    }
    defaults.update(kwargs)
    return JobApplicationTarget(**defaults)

def test_lever_detect():
    adapter = LeverAdapter()
    assert adapter.detect(MagicMock(), "https://jobs.lever.co/figma/202") is True
    assert adapter.detect(MagicMock(), "https://boards.greenhouse.io/figma") is False

def test_lever_submit_or_hold_draft():
    adapter = LeverAdapter()
    page = MagicMock()
    job = make_job()

    res = adapter.submit_or_hold(page, SubmissionMode.DRAFT, job, None, [])
    assert res.status == "DRAFT_PENDING_REVIEW"
    assert res.job.job_id == "lev_202"

def test_lever_auto_mode_submits():
    adapter = LeverAdapter()
    page = MagicMock()

    mock_btn = MagicMock()
    mock_btn.count.return_value = 1
    page.locator.return_value = mock_btn

    resolutions = [
        FieldResolution(
            field_label="Full Name",
            resolution_tier="tier0_selector",
            resolved_value="Soumyadeep Nath",
            confidence=1.0,
            source="candidate_profile"
        )
    ]

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, resolutions)
    assert res.status == "SUBMITTED"
