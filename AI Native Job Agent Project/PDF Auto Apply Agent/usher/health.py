"""
Adapter Health Check Monitor for Usher (Evaluation Plan §6).
Runs standalone smoke verification across registered adapters to detect upstream DOM drift
and selector breakages before real applications are attempted.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from .adapters import (
    GenericATSAdapter,
    GreenhouseAdapter,
    IndeedAdapter,
    LeverAdapter,
    LinkedInEasyApplyAdapter,
    NaukriAdapter,
    WorkdayAdapter,
)
from .config import config
from .schemas import ApplicationChannel, CandidateProfile, JobApplicationTarget

logger = logging.getLogger(__name__)


class AdapterHealthStatus(BaseModel):
    adapter_name: str
    channel: ApplicationChannel
    is_healthy: bool
    url_detection_passed: bool
    critical_fields_covered: bool
    missing_fields: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class HealthReport(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    adapters: Dict[str, AdapterHealthStatus] = Field(default_factory=dict)
    all_healthy: bool = True


class AdapterHealthMonitor:
    """Automated health and regression monitor for ATS platform adapters."""

    def __init__(self):
        self.sample_profile = CandidateProfile(
            full_name="Health Check Candidate",
            email="health@example.com",
            phone="+919876543210",
            location="Kolkata, India",
            portfolio_url="https://github.com/example",
            github_url="https://github.com/example",
            linkedin_url="https://linkedin.com/in/example",
            work_authorization="Authorized to work in India",
            salary_expectation="1000000",
            notice_period="30 Days",
        )
        self.test_cases = [
            (
                "NaukriAdapter",
                NaukriAdapter(),
                "https://www.naukri.com/job-listings-ai-dev",
                ["email id", "mobile number", "current location", "expected ctc"],
            ),
            (
                "IndeedAdapter",
                IndeedAdapter(),
                "https://www.indeed.com/viewjob?jk=12345",
                ["full name", "email", "phone", "location", "work authorization"],
            ),
            (
                "LinkedInEasyApplyAdapter",
                LinkedInEasyApplyAdapter(),
                "https://www.linkedin.com/jobs/view/99999",
                ["email address", "mobile phone number", "city", "work authorization"],
            ),
            (
                "GreenhouseAdapter",
                GreenhouseAdapter(),
                "https://boards.greenhouse.io/company/jobs/1",
                ["first name", "last name", "email", "phone", "linkedin profile"],
            ),
            (
                "LeverAdapter",
                LeverAdapter(),
                "https://jobs.lever.co/company/2",
                ["full name", "email", "phone", "linkedin url", "work authorization"],
            ),
            (
                "WorkdayAdapter",
                WorkdayAdapter(),
                "https://company.myworkdayjobs.com/careers/3",
                ["first name", "last name", "email address", "phone number", "city"],
            ),
            (
                "GenericATSAdapter",
                GenericATSAdapter(),
                "https://careers.example.com/apply",
                ["full name", "email", "phone", "location", "linkedin"],
            ),
        ]

    def check_adapter(
        self,
        name: str,
        adapter,
        sample_url: str,
        critical_fields: List[str],
    ) -> AdapterHealthStatus:
        """Runs smoke validation on a single adapter's detection and resolver coverage."""
        logger.info("[HealthMonitor] Running smoke check for %s...", name)

        # 1. URL Detection
        url_passed = adapter.detect(None, sample_url)

        # 2. Check Critical Field Resolvability in Tier 0 / Tier 1 (Offline Dictionary Check)
        missing = []
        for field in critical_fields:
            res = adapter.resolver.resolve(field_label=field, profile=self.sample_profile)
            if res.resolution_tier not in ["tier0_selector", "tier1_fuzzy"] or not res.resolved_value:
                missing.append(field)

        is_healthy = url_passed and len(missing) == 0
        error_msg = None if is_healthy else f"Missing Tier-0/1 coverage for: {', '.join(missing)}" if missing else "URL detection failed"

        return AdapterHealthStatus(
            adapter_name=name,
            channel=adapter.channel,
            is_healthy=is_healthy,
            url_detection_passed=url_passed,
            critical_fields_covered=(len(missing) == 0),
            missing_fields=missing,
            error_message=error_msg,
        )

    def run_all_checks(self) -> HealthReport:
        """Executes health checks across all registered platform adapters."""
        report = HealthReport()
        all_passed = True

        for name, adapter, sample_url, fields in self.test_cases:
            status = self.check_adapter(name, adapter, sample_url, fields)
            report.adapters[name] = status
            if not status.is_healthy:
                all_passed = False

        report.all_healthy = all_passed
        logger.info("[HealthMonitor] Health check complete. All healthy: %s", all_passed)
        return report
