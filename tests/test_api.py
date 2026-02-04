"""Unit tests for the differential_coverage API using tests/sample_coverage data."""

from pathlib import Path

import pytest

from differential_coverage.api import (
    read_campaign,
    run_relcov_performance_corpus,
    run_relcov_performance_corpus_all,
    run_relcov_performance_fuzzer,
    run_relcov_performance_fuzzer_all,
    run_relcov_reliability,
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


def test_run_relcov_reliability() -> None:
    """relcov reliability on sample (no seeds) returns expected values."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    del campaign["seeds"]
    results = run_relcov_reliability(campaign)
    assert results.keys() == {"fuzzer_a", "fuzzer_b", "fuzzer_c"}
    assert results["fuzzer_a"] == pytest.approx(2 / 3)
    assert results["fuzzer_b"] == 1.0
    assert results["fuzzer_c"] == 1.0


def test_run_relcov_performance_fuzzer() -> None:
    """relcov performance vs reference fuzzer on sample (no seeds)."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    del campaign["seeds"]
    results = run_relcov_performance_fuzzer(campaign, "fuzzer_c")
    assert set(results.keys()) == {"fuzzer_a", "fuzzer_b"}
    assert results["fuzzer_a"] == pytest.approx(2 / 3)
    assert results["fuzzer_b"] == pytest.approx(2 / 3)


def test_run_relcov_performance_corpus() -> None:
    """relcov performance over input corpus (seeds) on full sample."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    scores = run_relcov_performance_corpus(campaign, input_corpus_fuzzer="seeds")
    assert scores == {
        "fuzzer_a": pytest.approx(1.0 / 3),
        "fuzzer_b": pytest.approx(1.0 / 2),
        "fuzzer_c": pytest.approx(1.0 / 3),
    }


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


def test_run_relcov_performance_corpus_missing_fuzzer() -> None:
    """run_relcov_performance_corpus raises if input corpus fuzzer not in campaign."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    with pytest.raises(ValueError, match="not found in campaign"):
        run_relcov_performance_corpus(campaign, input_corpus_fuzzer="nonexistent")


def test_run_relcov_performance_corpus_not_single_trial() -> None:
    """run_relcov_performance_corpus requires exactly one trial for input corpus."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    # fuzzer_a has two trials (t1, t2)
    with pytest.raises(ValueError, match="exactly one trial"):
        run_relcov_performance_corpus(campaign, input_corpus_fuzzer="fuzzer_a")


def test_run_relcov_performance_corpus_all() -> None:
    """run_relcov_performance_corpus_all returns table with one corpus (seeds)."""
    campaign = read_campaign_dir(SAMPLE_DIR)
    corpus_fuzzers, table = run_relcov_performance_corpus_all(campaign)
    assert corpus_fuzzers == ["seeds"]
    assert set(table.keys()) == {"fuzzer_a", "fuzzer_b", "fuzzer_c", "seeds"}
    assert table["seeds"]["seeds"] == 1.0
    assert table["fuzzer_a"]["seeds"] == pytest.approx(1.0 / 3)
    assert table["fuzzer_b"]["seeds"] == pytest.approx(1.0 / 2)
    assert table["fuzzer_c"]["seeds"] == pytest.approx(1.0 / 3)
