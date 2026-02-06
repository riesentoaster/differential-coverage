"""Unit tests for the differential_coverage API using tests/sample_coverage data."""

from pathlib import Path

import pytest

from differential_coverage.api import (
    read_campaign,
    run_relcov_performance_fuzzer,
    run_relcov_performance_fuzzer_all,
    run_relscore,
)
from differential_coverage.files import read_campaign_dir
from differential_coverage.relcov import reliability

SAMPLE_DIR = (Path(__file__).parent / "sample_coverage").resolve()


def test_read_campaign() -> None:
    """read_campaign returns same structure as read_campaign_dir."""
    from_campaign = read_campaign(SAMPLE_DIR)
    from_files = read_campaign_dir(SAMPLE_DIR)
    assert from_campaign.keys() == from_files.keys()
    for name in from_campaign:
        assert from_campaign[name].keys() == from_files[name].keys()


def test_run_relscore() -> None:
    """relscore (SBFT'25) on sample without seeds matches expected ordering."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    del campaign["seeds"]
    scores = run_relscore(campaign)
    assert scores == {
        "fuzzer_c": 1.0,
        "fuzzer_a": 0.5,
        "fuzzer_b": 0.0,
    }


def test_run_relcov_performance_fuzzer() -> None:
    """relcov performance vs reference fuzzer on sample (no seeds)."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    del campaign["seeds"]
    results = run_relcov_performance_fuzzer(campaign, "fuzzer_c")
    assert set(results.keys()) == {"fuzzer_a", "fuzzer_b"}
    assert results["fuzzer_a"] == pytest.approx(2 / 3)
    assert results["fuzzer_b"] == pytest.approx(2 / 3)


def test_run_relcov_performance_fuzzer_all() -> None:
    """run_relcov_performance_fuzzer_all returns N×N table (all fuzzers as reference)."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    del campaign["seeds"]
    ref_fuzzers, table = run_relcov_performance_fuzzer_all(campaign)
    assert ref_fuzzers == ["fuzzer_a", "fuzzer_b", "fuzzer_c"]
    assert set(table.keys()) == {"fuzzer_a", "fuzzer_b", "fuzzer_c"}
    for name in ref_fuzzers:
        assert table[name][name] == reliability(campaign[name])
    assert table["fuzzer_a"]["fuzzer_c"] == pytest.approx(2 / 3)
    assert table["fuzzer_b"]["fuzzer_c"] == pytest.approx(2 / 3)


def test_run_relcov_performance_fuzzer_missing_reference() -> None:
    """run_relcov_performance_fuzzer raises if reference fuzzer not in campaign."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    del campaign["seeds"]
    with pytest.raises(ValueError, match="not found in campaign"):
        run_relcov_performance_fuzzer(campaign, "nonexistent")
