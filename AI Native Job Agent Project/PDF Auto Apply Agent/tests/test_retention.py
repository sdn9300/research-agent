import os
import time
from pathlib import Path
from usher.retention import RetentionManager

def test_retention_clean_screenshots(tmp_path):
    screenshots_dir = tmp_path / "screenshots"
    screenshots_dir.mkdir()

    # Create 1 recent file (now) and 1 old file (40 days ago)
    recent_file = screenshots_dir / "recent.png"
    recent_file.write_bytes(b"recent")

    old_file = screenshots_dir / "old.png"
    old_file.write_bytes(b"old_data_to_purge")
    # Set mtime to 40 days ago (40 * 86400 seconds)
    old_time = time.time() - (40 * 86400)
    os.utime(str(old_file), (old_time, old_time))

    manager = RetentionManager(
        screenshots_dir=screenshots_dir,
        attempts_dir=tmp_path / "attempts",
        max_screenshot_age_days=30
    )

    deleted_count, reclaimed_bytes = manager.clean_screenshots()
    assert deleted_count == 1
    assert reclaimed_bytes == len(b"old_data_to_purge")
    assert not old_file.exists()
    assert recent_file.exists()

def test_retention_protects_core_index_files(tmp_path):
    attempts_dir = tmp_path / "attempts"
    attempts_dir.mkdir()

    # Protected core files should never be deleted even if old
    memory_file = attempts_dir / "memory_module_records.json"
    memory_file.write_text("[]")
    old_time = time.time() - (100 * 86400)
    os.utime(str(memory_file), (old_time, old_time))

    # Old attempt file that SHOULD be purged
    old_attempt = attempts_dir / "att_old.json"
    old_attempt.write_text("{}")
    os.utime(str(old_attempt), (old_time, old_time))

    manager = RetentionManager(
        screenshots_dir=tmp_path / "screenshots",
        attempts_dir=attempts_dir,
        max_attempt_age_days=90
    )

    deleted_count, _ = manager.clean_attempt_logs()
    assert deleted_count == 1
    assert not old_attempt.exists()
    assert memory_file.exists()
