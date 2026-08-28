from unittest.mock import MagicMock
from usher.adapters.linkedin import LinkedInEasyApplyAdapter
from usher.schemas import CandidateProfile, FieldResolution, JobApplicationTarget, SubmissionMode

def make_job(**kwargs):
    defaults = {
        "job_id": "li_999",
        "title": "Senior AI Engineer",
        "company": "Enterprise AI",
        "apply_url": "https://www.linkedin.com/jobs/view/999888",
        "source_platform": "linkedin"
    }
    defaults.update(kwargs)
    return JobApplicationTarget(**defaults)

def test_linkedin_detect():
    adapter = LinkedInEasyApplyAdapter()
    assert adapter.detect(MagicMock(), "https://www.linkedin.com/jobs/view/999888") is True
    assert adapter.detect(MagicMock(), "https://www.indeed.com/viewjob") is False

def test_linkedin_security_checkpoint_triggers_manual():
    adapter = LinkedInEasyApplyAdapter()
    page = MagicMock()

    # Mock security checkpoint detection
    def mock_locator(sel):
        mock_el = MagicMock()
        mock_el.count.return_value = 1 if "arkoselabs" in sel else 0
        return mock_el

    page.locator.side_effect = mock_locator

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, [])
    assert res.status == "MANUAL_REQUIRED"
    assert res.error_code == "SECURITY_CHECKPOINT"

def test_linkedin_tier3_free_text_forces_draft_in_auto_mode():
    """EC-PAA-MAP-03: Tier 3 answers ALWAYS route to review even in AUTO mode."""
    adapter = LinkedInEasyApplyAdapter()
    page = MagicMock()
    page.locator.return_value.count.return_value = 0 # No security checkpoint

    resolutions = [
        FieldResolution(
            field_label="Why are you a good fit for this role?",
            resolution_tier="tier3_llm_heavy",
            resolved_value="I have 5 years experience with LLMs...",
            confidence=0.0,
            source="generated"
        )
    ]

    job = make_job()
    # Even when mode is AUTO, Tier-3 forces DRAFT_PENDING_REVIEW
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, resolutions)
    assert res.status == "DRAFT_PENDING_REVIEW"

def test_linkedin_auto_mode_submits():
    adapter = LinkedInEasyApplyAdapter()
    page = MagicMock()
    def mock_locator(sel):
        mock_el = MagicMock()
        mock_el.count.return_value = 1 if "Submit application" in sel else 0
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
