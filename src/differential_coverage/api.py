from pathlib import Path

from differential_coverage.files import read_campaign_dir
from differential_coverage.relcov import (
    performance_over_fuzzer,
    performance_over_input_corpus,
    reliability,
)
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


def run_relcov_reliability(campaign: CampaignMap) -> dict[FuzzerIdentifier, float]:
    """Compute relcov-based reliability for each fuzzer in a campaign."""
    return {name: reliability(trials) for name, trials in campaign.items()}


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


def run_relcov_performance_corpus(
    campaign: CampaignMap,
    input_corpus_fuzzer: FuzzerIdentifier,
) -> dict[FuzzerIdentifier, float]:
    """Compute relcov-based performance of each fuzzer relative to an input corpus."""
    if input_corpus_fuzzer not in campaign:
        raise ValueError(
            f"Input corpus fuzzer {input_corpus_fuzzer!r} not found in campaign."
        )

    corpus_trials = campaign[input_corpus_fuzzer]
    if len(corpus_trials) != 1:
        raise ValueError(
            f"Input corpus fuzzer {input_corpus_fuzzer!r} must have exactly one trial, "
            f"found {len(corpus_trials)}."
        )

    # Extract the single coverage map for the corpus.
    ((_, coverage_map),) = corpus_trials.items()

    return {
        name: performance_over_input_corpus(trials, coverage_map)
        for name, trials in campaign.items()
        if name != input_corpus_fuzzer
    }


def run_relcov_performance_corpus_all(
    campaign: CampaignMap,
) -> tuple[
    list[FuzzerIdentifier], dict[FuzzerIdentifier, dict[FuzzerIdentifier, float]]
]:
    """
    Compute relcov-based performance of each fuzzer relative to every input corpus.

    Corpus fuzzers are those with exactly one trial. Returns (corpus_fuzzers, table)
    where table[row_fuzzer][corpus_fuzzer] is the performance of row_fuzzer over
    that corpus (1.0 when row_fuzzer == corpus_fuzzer).
    """
    corpus_fuzzers = sorted(
        name for name, trials in campaign.items() if len(trials) == 1
    )
    # One run per corpus, then fill table by row
    table: dict[FuzzerIdentifier, dict[FuzzerIdentifier, float]] = {
        name: {} for name in campaign
    }
    for corpus_name in corpus_fuzzers:
        scores = run_relcov_performance_corpus(campaign, corpus_name)
        for fuzzer, score in scores.items():
            table[fuzzer][corpus_name] = score
        table[corpus_name][corpus_name] = 1.0
    return (corpus_fuzzers, table)
