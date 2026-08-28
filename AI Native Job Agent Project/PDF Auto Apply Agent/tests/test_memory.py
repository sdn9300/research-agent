from pathlib import Path
from usher.memory import MemoryModuleAdapter
from usher.schemas import ApplicationAttemptResult, JobApplicationTarget

def make_attempt(job_id: str, company: str, title: str, status: str = "SUBMITTED"):
    job = JobApplicationTarget(
        job_id=job_id,
        title=title,
        company=company,
        apply_url=f"https://example.com/jobs/{job_id}",
        source_platform="naukri"
    )
    return ApplicationAttemptResult(
        attempt_id=f"att_{job_id}",
        job=job,
        status=status,
    )

def test_memory_persist_and_retrieve(tmp_path):
    storage_file = tmp_path / "memory_records.json"
    memory = MemoryModuleAdapter(storage_file_path=storage_file)

    assert len(memory.attempts) == 0

    att1 = make_attempt("job_001", "Google", "AI Engineer", status="DRAFT_PENDING_REVIEW")
    memory.persist_attempt(att1)

    assert len(memory.attempts) == 1
    assert memory.has_applied("job_001", "Google", "AI Engineer") is True

    # Reload from disk
    memory2 = MemoryModuleAdapter(storage_file_path=storage_file)
    assert len(memory2.attempts) == 1
    assert memory2.has_applied("job_001", "Google", "AI Engineer") is True

def test_memory_near_duplicate_detection(tmp_path):
    storage_file = tmp_path / "memory_records.json"
    memory = MemoryModuleAdapter(storage_file_path=storage_file)

    att1 = make_attempt("job_100", "Microsoft", "Prompt Engineer")
    memory.persist_attempt(att1)

    # Different job ID, same company and title (EC-PAA-DAT-04)
    assert memory.has_applied("job_200", "Microsoft", "Prompt Engineer") is True
    # Different title
    assert memory.has_applied("job_300", "Microsoft", "Data Scientist") is False

def test_memory_stats(tmp_path):
    storage_file = tmp_path / "memory_records.json"
    memory = MemoryModuleAdapter(storage_file_path=storage_file)

    memory.persist_attempt(make_attempt("j1", "Meta", "Engineer", status="SUBMITTED"))
    memory.persist_attempt(make_attempt("j2", "Apple", "Engineer", status="DRAFT_PENDING_REVIEW"))
    memory.persist_attempt(make_attempt("j3", "Amazon", "Engineer", status="MANUAL_REQUIRED"))

    stats = memory.get_stats()
    assert stats["total"] == 3
    assert stats["SUBMITTED"] == 1
    assert stats["DRAFT_PENDING_REVIEW"] == 1
    assert stats["MANUAL_REQUIRED"] == 1
    assert stats["FAILED"] == 0
