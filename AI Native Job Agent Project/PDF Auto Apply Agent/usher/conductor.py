"""
Conductor Orchestrator (CONDUCTOR Component 6) integration seam.
Provides the standard LangGraph node function and shared-state contracts for orchestrating Usher.
"""

import logging
from typing import Any, Dict, Optional, Union

from .pipeline import AutoApplyPipeline
from .schemas import (
    ApplicationAttemptResult,
    CandidateProfile,
    ConductorState,
    JobApplicationTarget,
    ResumeArtifact,
    SubmissionMode,
)

logger = logging.getLogger(__name__)


def auto_apply_node(state: Union[Dict[str, Any], ConductorState]) -> Dict[str, Any]:
    """
    Standard LangGraph node interface for Conductor Orchestrator.
    Consumes ConductorState from shared graph state and writes back ApplicationAttemptResult.
    """
    logger.info("[ConductorSeam] auto_apply_node invoked by Conductor Orchestrator.")

    try:
        # Normalize input dictionary to ConductorState if needed
        if isinstance(state, dict):
            c_state = ConductorState(**state)
            raw_dict = state
        else:
            c_state = state
            raw_dict = state.model_dump()

        pipeline = AutoApplyPipeline()
        result: ApplicationAttemptResult = pipeline.execute(
            job=c_state.job,
            profile=c_state.profile,
            resume=c_state.resume,
            mode=c_state.submission_mode,
        )

        # Update shared state
        output_state = dict(raw_dict)
        output_state["attempt_result"] = result.model_dump(mode="json")
        output_state["error"] = result.error_message if result.status == "FAILED" else None

        logger.info(
            "[ConductorSeam] Execution finished with status '%s'. Updating shared graph state.",
            result.status
        )
        return output_state

    except Exception as e:
        logger.error("[ConductorSeam] auto_apply_node failed unexpectedly: %s", e)
        output_state = dict(state) if isinstance(state, dict) else state.model_dump()
        output_state["error"] = str(e)
        return output_state


def run_auto_apply_pipeline(
    job: JobApplicationTarget,
    profile: CandidateProfile,
    resume: ResumeArtifact,
    mode: Optional[SubmissionMode] = None,
) -> ApplicationAttemptResult:
    """Convenience helper for standalone direct execution without LangGraph wrapper."""
    pipeline = AutoApplyPipeline()
    return pipeline.execute(job=job, profile=profile, resume=resume, mode=mode)
