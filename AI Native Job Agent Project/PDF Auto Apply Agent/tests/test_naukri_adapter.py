from unittest.mock import MagicMock
from usher.adapters.naukri import NaukriAdapter
from usher.schemas import CandidateProfile, JobApplicationTarget, SubmissionMode

def make_job(**kwargs):
    defaults = {
        "job_id": "123",
        "title": "Software Engineer",
        "company": "Acme Corp",
        "apply_url": "https://naukri.com/123",
        "source_platform": "naukri"
    }
    defaults.update(kwargs)
    return JobApplicationTarget(**defaults)

def test_naukri_detect():
    adapter = NaukriAdapter()
    
    assert adapter.detect(MagicMock(), "https://www.naukri.com/job-listings-xyz") is True
    assert adapter.detect(MagicMock(), "https://www.linkedin.com/jobs/view/123") is False

def test_naukri_submit_or_hold_draft():
    adapter = NaukriAdapter()
    job = make_job()
    
    # Empty resolutions
    res = adapter.submit_or_hold(MagicMock(), SubmissionMode.DRAFT, job, None, [])
    assert res.status == "DRAFT_PENDING_REVIEW"
    assert res.job.job_id == "123"

def test_naukri_submit_or_hold_manual_forced():
    adapter = NaukriAdapter()
    job = make_job()
    
    from usher.schemas import FieldResolution
    resolutions = [
        FieldResolution(
            field_label="Test",
            resolution_tier="tier2_llm_light",
            resolved_value="value",
            confidence=0.5, # Below 0.85 threshold
            source="manual_required",
            reasoning="test"
        )
    ]
    
    # Even if mode is AUTO, low confidence should force MANUAL_REQUIRED
    res = adapter.submit_or_hold(MagicMock(), SubmissionMode.AUTO, job, None, resolutions)
    assert res.status == "MANUAL_REQUIRED"
