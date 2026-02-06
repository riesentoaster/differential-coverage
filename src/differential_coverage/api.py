from pathlib import Path

from differential_coverage.files import read_campaign_dir
from differential_coverage.relcov import performance_over_fuzzer, reliability
from differential_coverage.relscore import calculate_differential_coverage_scores
from differential_coverage.types import (
    CampaignMap,
    FuzzerIdentifier,
)


def read_campaign(path: Path) -> CampaignMap:
    """Public helper to read a campaign directory into an in-memory map."""
    return read_campaign_dir(path)


def run_relscore(campaign: CampaignMap) -> dict[FuzzerIdentifier, float]:
    """Compute relscore (SBFT'25) for each fuzzer in a campaign."""
    return calculate_differential_coverage_scores(campaign)


def run_relcov_performance_fuzzer(
    campaign: CampaignMap,
    against: FuzzerIdentifier,
) -> dict[FuzzerIdentifier, float]:
    """Compute relcov-based performance of each fuzzer relative to another."""
    if against not in campaign:
        raise ValueError(f"Reference fuzzer {against!r} not found in campaign.")
    ref = campaign[against]
    return {
        name: performance_over_fuzzer(trials, ref)
        for name, trials in campaign.items()
        if name != against
    }


def run_relcov_performance_fuzzer_all(
    campaign: CampaignMap,
) -> tuple[
    list[FuzzerIdentifier], dict[FuzzerIdentifier, dict[FuzzerIdentifier, float]]
]:
    """
    Compute relcov-based performance of each fuzzer relative to every other as reference.

    Returns (ref_fuzzers, table) where table[row_fuzzer][ref_fuzzer] is the performance
    of row_fuzzer relative to ref_fuzzer (1.0 when row_fuzzer == ref_fuzzer).
    """
    ref_fuzzers = sorted(campaign.keys())
    table: dict[FuzzerIdentifier, dict[FuzzerIdentifier, float]] = {
        name: {} for name in campaign
    }
    for against in ref_fuzzers:
        scores = run_relcov_performance_fuzzer(campaign, against)
        for fuzzer, score in scores.items():
            table[fuzzer][against] = score
        table[against][against] = reliability(campaign[against])
    return (ref_fuzzers, table)
