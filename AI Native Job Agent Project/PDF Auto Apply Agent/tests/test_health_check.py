from usher.health import AdapterHealthMonitor

def test_health_monitor_all_checks():
    monitor = AdapterHealthMonitor()
    report = monitor.run_all_checks()

    assert report.all_healthy is True
    assert len(report.adapters) == 7

    # Verify all expected adapters are present and healthy
    for adapter_name in [
        "NaukriAdapter",
        "IndeedAdapter",
        "LinkedInEasyApplyAdapter",
        "GreenhouseAdapter",
        "LeverAdapter",
        "WorkdayAdapter",
        "GenericATSAdapter",
    ]:
        assert adapter_name in report.adapters
        status = report.adapters[adapter_name]
        assert status.is_healthy is True
        assert status.url_detection_passed is True
        assert status.critical_fields_covered is True
        assert len(status.missing_fields) == 0

def test_health_monitor_broken_adapter_detection():
    monitor = AdapterHealthMonitor()
    # Check with an invalid required field
    naukri_status = monitor.check_adapter(
        name="NaukriAdapter",
        adapter=monitor.test_cases[0][1],
        sample_url="https://www.naukri.com/job-1",
        critical_fields=["unsupported_obscure_field_xyz"],
    )
    assert naukri_status.is_healthy is False
    assert naukri_status.critical_fields_covered is False
    assert "unsupported_obscure_field_xyz" in naukri_status.missing_fields
