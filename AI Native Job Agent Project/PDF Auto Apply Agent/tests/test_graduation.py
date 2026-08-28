import json
from pathlib import Path
from usher.graduation import PlatformGraduationTracker
from usher.schemas import ApplicationChannel

def test_graduation_clean_streak_and_unlock(tmp_path):
    state_file = tmp_path / "graduation_state.json"
    tracker = PlatformGraduationTracker(state_file_path=state_file)

    channel = ApplicationChannel.NAUKRI
    assert not tracker.is_auto_mode_unlocked(channel)

    # Record 9 clean runs (threshold is 10)
    for _ in range(9):
        tracker.record_attempt(channel, status="DRAFT_PENDING_REVIEW", had_manual_corrections=False)
        assert not tracker.is_auto_mode_unlocked(channel)

    # 10th clean run unlocks AUTO mode
    tracker.record_attempt(channel, status="DRAFT_PENDING_REVIEW", had_manual_corrections=False)
    assert tracker.is_auto_mode_unlocked(channel)
    assert tracker.get_record(channel).consecutive_clean_runs == 10

def test_graduation_streak_reset_on_failure(tmp_path):
    state_file = tmp_path / "graduation_state.json"
    tracker = PlatformGraduationTracker(state_file_path=state_file)

    channel = ApplicationChannel.INDEED
    for _ in range(5):
        tracker.record_attempt(channel, status="DRAFT_PENDING_REVIEW", had_manual_corrections=False)

    assert tracker.get_record(channel).consecutive_clean_runs == 5

    # Failure resets streak to 0
    tracker.record_attempt(channel, status="FAILED")
    assert tracker.get_record(channel).consecutive_clean_runs == 0
    assert not tracker.is_auto_mode_unlocked(channel)

def test_graduation_streak_reset_on_manual_correction(tmp_path):
    state_file = tmp_path / "graduation_state.json"
    tracker = PlatformGraduationTracker(state_file_path=state_file)

    channel = ApplicationChannel.LINKEDIN_EASY_APPLY
    for _ in range(15):
        tracker.record_attempt(channel, status="SUBMITTED", had_manual_corrections=False)

    assert tracker.is_auto_mode_unlocked(channel)

    # Manual correction resets unlocked AUTO mode back to DRAFT
    tracker.record_attempt(channel, status="DRAFT_PENDING_REVIEW", had_manual_corrections=True)
    assert tracker.get_record(channel).consecutive_clean_runs == 0
    assert not tracker.is_auto_mode_unlocked(channel)

def test_graduation_lockout_and_persistence(tmp_path):
    state_file = tmp_path / "graduation_state.json"
    tracker = PlatformGraduationTracker(state_file_path=state_file)

    channel = ApplicationChannel.LINKEDIN_EASY_APPLY
    tracker.lockout_platform(channel, reason="Platform account warning received (EC-PAA-SEC-04)")

    assert not tracker.is_auto_mode_unlocked(channel)
    assert tracker.get_record(channel).is_locked_out is True

    # Reload from saved file
    tracker2 = PlatformGraduationTracker(state_file_path=state_file)
    assert tracker2.get_record(channel).is_locked_out is True
    assert tracker2.get_record(channel).lockout_reason == "Platform account warning received (EC-PAA-SEC-04)"
