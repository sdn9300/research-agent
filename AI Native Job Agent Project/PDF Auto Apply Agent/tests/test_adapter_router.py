from usher.adapters import (
    GenericATSAdapter,
    GreenhouseAdapter,
    IndeedAdapter,
    LeverAdapter,
    LinkedInEasyApplyAdapter,
    NaukriAdapter,
    WorkdayAdapter,
    get_adapter_for_channel,
    get_adapter_for_url,
)
from usher.schemas import ApplicationChannel

def test_router_get_adapter_for_channel():
    assert isinstance(get_adapter_for_channel(ApplicationChannel.NAUKRI), NaukriAdapter)
    assert isinstance(get_adapter_for_channel(ApplicationChannel.INDEED), IndeedAdapter)
    assert isinstance(get_adapter_for_channel(ApplicationChannel.LINKEDIN_EASY_APPLY), LinkedInEasyApplyAdapter)
    assert isinstance(get_adapter_for_channel(ApplicationChannel.GENERIC_ATS_GREENHOUSE), GreenhouseAdapter)
    assert isinstance(get_adapter_for_channel(ApplicationChannel.GENERIC_ATS_LEVER), LeverAdapter)
    assert isinstance(get_adapter_for_channel(ApplicationChannel.GENERIC_ATS_WORKDAY), WorkdayAdapter)
    assert isinstance(get_adapter_for_channel(ApplicationChannel.GENERIC_ATS_UNKNOWN), GenericATSAdapter)
    assert get_adapter_for_channel(ApplicationChannel.UNSUPPORTED) is None

def test_router_get_adapter_for_url():
    assert isinstance(get_adapter_for_url("https://www.naukri.com/job-listings-ai-engineer"), NaukriAdapter)
    assert isinstance(get_adapter_for_url("https://www.indeed.com/viewjob?jk=abcdef"), IndeedAdapter)
    assert isinstance(get_adapter_for_url("https://www.linkedin.com/jobs/view/123456"), LinkedInEasyApplyAdapter)
    assert isinstance(get_adapter_for_url("https://boards.greenhouse.io/stripe/jobs/123"), GreenhouseAdapter)
    assert isinstance(get_adapter_for_url("https://grnh.se/xyz"), GreenhouseAdapter)
    assert isinstance(get_adapter_for_url("https://jobs.lever.co/figma/abc"), LeverAdapter)
    assert isinstance(get_adapter_for_url("https://company.myworkdayjobs.com/careers/job/1"), WorkdayAdapter)
    # Generic fallback
    assert isinstance(get_adapter_for_url("https://careers.startup.io/apply/123"), GenericATSAdapter)
    # Without generic fallback
    assert get_adapter_for_url("https://careers.startup.io/apply/123", fallback_to_generic=False) is None
