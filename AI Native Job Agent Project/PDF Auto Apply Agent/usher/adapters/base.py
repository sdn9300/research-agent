"""
Abstract base class for all platform and ATS adapters in Usher.
Authoritative contract defined in PAA-AD-1.0 §4.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from playwright.sync_api import Page

from ..schemas import (
    ApplicationAttemptResult,
    ApplicationChannel,
    CandidateProfile,
    FieldResolution,
    JobApplicationTarget,
    ResumeArtifact,
    SubmissionMode,
)


class BaseATSAdapter(ABC):
    """
    Abstract adapter interface for job application platforms.
    Every platform adapter (Naukri, Indeed, LinkedIn, Generic ATS) implements this contract.
    """

    def __init__(self, channel: ApplicationChannel):
        self.channel = channel

    @property
    def name(self) -> str:
        """Dynamic adapter name derived from class name."""
        return self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    def detect(self, page: Page, url: str) -> bool:
        """
        Inspects the current URL and DOM to verify if this adapter handles the target.
        Returns True if matched, False otherwise.
        """
        pass

    @abstractmethod
    def map_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        job: JobApplicationTarget,
    ) -> List[FieldResolution]:
        """
        Runs the tiered resolution ladder against detected form fields.
        Returns a list of resolved fields with confidence scores.
        """
        pass

    @abstractmethod
    def fill(
        self,
        page: Page,
        resolutions: List[FieldResolution],
    ) -> None:
        """
        Fills the form fields on the page based on high-confidence resolutions (>= 0.85).
        """
        pass

    @abstractmethod
    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        """
        Uploads the tailored PDF resume artifact to the application form.
        Verifies file existence and checksum integrity before attaching.
        """
        pass

    @abstractmethod
    def submit_or_hold(
        self,
        page: Page,
        mode: SubmissionMode,
        job: JobApplicationTarget,
        resume: Optional[ResumeArtifact] = None,
        resolutions: Optional[List[FieldResolution]] = None,
    ) -> ApplicationAttemptResult:
        """
        Executes the submission gatekeeper:
        - In DRAFT mode: pauses at confirmation page and returns DRAFT_PENDING_REVIEW.
        - In AUTO mode: submits and verifies confirmation signal, returning SUBMITTED.
        - Returns structured ApplicationAttemptResult in all cases.
        """
        pass
