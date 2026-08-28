from unittest.mock import MagicMock
from usher.adapters.indeed import IndeedAdapter
from usher.schemas import CandidateProfile, FieldResolution, JobApplicationTarget, SubmissionMode, ResumeArtifact

def make_job(**kwargs):
    defaults = {
        "job_id": "ind_123",
        "title": "Full Stack Engineer",
        "company": "Tech Solutions",
        "apply_url": "https://www.indeed.com/viewjob?jk=12345",
        "source_platform": "indeed"
    }
    defaults.update(kwargs)
    return JobApplicationTarget(**defaults)

def test_indeed_detect():
    adapter = IndeedAdapter()
    assert adapter.detect(MagicMock(), "https://www.indeed.com/viewjob?jk=12345") is True
    assert adapter.detect(MagicMock(), "https://www.naukri.com/job-listings") is False

def test_indeed_submit_or_hold_draft():
    adapter = IndeedAdapter()
    page = MagicMock()
    page.locator.return_value.count.return_value = 0 # No captcha

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.DRAFT, job, None, [])
    assert res.status == "DRAFT_PENDING_REVIEW"
    assert res.job.job_id == "ind_123"

def test_indeed_security_challenge_triggers_manual():
    adapter = IndeedAdapter()
    page = MagicMock()
    # Mock presence of cloudflare challenge
    def mock_count(sel):
        mock_el = MagicMock()
        mock_el.count.return_value = 1 if "cloudflare" in sel else 0
        return mock_el

    page.locator.side_effect = mock_count

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, [])
    assert res.status == "MANUAL_REQUIRED"
    assert res.error_code == "CAPTCHA_CHALLENGE"

def test_indeed_low_confidence_triggers_manual():
    adapter = IndeedAdapter()
    page = MagicMock()
    page.locator.return_value.count.return_value = 0

    resolutions = [
        FieldResolution(
            field_label="Total Experience",
            resolution_tier="tier2_llm_light",
            resolved_value="3",
            confidence=0.60, # Below 0.85
            source="manual_required"
        )
    ]

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, resolutions)
    assert res.status == "MANUAL_REQUIRED"

def test_indeed_auto_mode_submits():
    adapter = IndeedAdapter()
    page = MagicMock()
    def mock_locator(sel):
        mock_el = MagicMock()
        mock_el.count.return_value = 1 if "Submit" in sel or "Apply" in sel or "[type='submit']" in sel else 0
        return mock_el
    page.locator.side_effect = mock_locator

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
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, resolutions)
    assert res.status == "SUBMITTED"
