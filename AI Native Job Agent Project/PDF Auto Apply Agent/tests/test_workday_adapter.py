from unittest.mock import MagicMock
from usher.adapters.workday import WorkdayAdapter
from usher.schemas import CandidateProfile, FieldResolution, JobApplicationTarget, SubmissionMode

def make_job(**kwargs):
    defaults = {
        "job_id": "wd_303",
        "title": "Data Platform Architect",
        "company": "Amazon",
        "apply_url": "https://amazon.myworkdayjobs.com/en-US/jobs/303",
        "source_platform": "workday"
    }
    defaults.update(kwargs)
    return JobApplicationTarget(**defaults)

def test_workday_detect():
    adapter = WorkdayAdapter()
    assert adapter.detect(MagicMock(), "https://amazon.myworkdayjobs.com/en-US/jobs/303") is True
    assert adapter.detect(MagicMock(), "https://boards.greenhouse.io/amazon") is False

def test_workday_account_wall_triggers_manual():
    """EC-PAA-SUB-03: Workday signup wall forces MANUAL_REQUIRED."""
    adapter = WorkdayAdapter()
    page = MagicMock()

    def mock_locator(sel):
        mock_el = MagicMock()
        mock_el.count.return_value = 1 if "createAccountLink" in sel else 0
        return mock_el

    page.locator.side_effect = mock_locator

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.AUTO, job, None, [])
    assert res.status == "MANUAL_REQUIRED"
    assert res.error_code == "ACCOUNT_CREATION_REQUIRED"

def test_workday_submit_or_hold_draft():
    adapter = WorkdayAdapter()
    page = MagicMock()
    page.locator.return_value.count.return_value = 0 # No account wall

    job = make_job()
    res = adapter.submit_or_hold(page, SubmissionMode.DRAFT, job, None, [])
    assert res.status == "DRAFT_PENDING_REVIEW"
