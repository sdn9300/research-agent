import os
from pathlib import Path
from usher.attachment import AttachmentHandler
from usher.schemas import ResumeArtifact

def test_attachment_handler_valid(tmp_path):
    # Create a temporary PDF file
    test_file = tmp_path / "resume.pdf"
    test_file.write_bytes(b"%PDF-1.4 mock content")
    
    # Calculate expected checksum
    expected_checksum = AttachmentHandler.calculate_checksum(test_file)
    
    artifact = ResumeArtifact(
        tailoring_run_id="run_1",
        file_path=str(test_file),
        file_checksum=expected_checksum,
        profile_version="v1"
    )
    
    verified_path = AttachmentHandler.get_verified_path(artifact)
    assert verified_path is not None
    assert verified_path == test_file

def test_attachment_handler_invalid_checksum(tmp_path):
    test_file = tmp_path / "resume.pdf"
    test_file.write_bytes(b"%PDF-1.4 mock content")
    
    artifact = ResumeArtifact(
        tailoring_run_id="run_1",
        file_path=str(test_file),
        file_checksum="invalid_checksum_12345",
        profile_version="v1"
    )
    
    verified_path = AttachmentHandler.get_verified_path(artifact)
    assert verified_path is None

def test_attachment_handler_missing_file(tmp_path):
    test_file = tmp_path / "missing.pdf"
    
    artifact = ResumeArtifact(
        tailoring_run_id="run_1",
        file_path=str(test_file),
        file_checksum="does_not_matter",
        profile_version="v1"
    )
    
    verified_path = AttachmentHandler.get_verified_path(artifact)
    assert verified_path is None
