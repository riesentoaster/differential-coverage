from differential_coverage.types import (
    CampaignMap,
    EdgeIdentifier,
    FuzzerIdentifier,
    FuzzerMap,
)


def calculate_fuzzer_score(
    trials: FuzzerMap,
    all_edges: set[EdgeIdentifier],
    fuzzers_that_never_hit_edge: dict[EdgeIdentifier, set[FuzzerIdentifier]],
) -> float:
    score = 0.0
    for e in all_edges:
        fuzzers_that_never_hit_e = len(fuzzers_that_never_hit_edge[e])
        trials_that_hit_e = len([trial for trial in trials.values() if trial.get(e, 0)])
        trials_with_non_empty_cov = len(
            [trial for trial in trials.values() if any(trial.values())]
        )
        score += (
            fuzzers_that_never_hit_e * trials_that_hit_e / trials_with_non_empty_cov
        )
    return score


def calculate_differential_coverage_scores(
    campaign: CampaignMap,
) -> dict[FuzzerIdentifier, float]:
    """
    differential_coverage(f,e) = (# fuzzers that never hit e) * (# trials of f that hit e) / (# trials of f with non-empty cov).
    score(f) = sum of differential_coverage(f,e) over all edges e.
    Returns scores for each fuzzer run.
    """
    all_edges = set(
        edge
        for fuzzer in campaign.values()
        for trial in fuzzer.values()
        for edge in trial.keys()
    )

    fuzzers_that_never_hit_edge: dict[EdgeIdentifier, set[FuzzerIdentifier]] = {
        edge: set(
            fuzzer
            for fuzzer, trials in campaign.items()
            if not any(trial.get(edge, 0) for trial in trials.values())
        )
        for edge in all_edges
    }

    scores: dict[FuzzerIdentifier, float] = {
        fuzzer: calculate_fuzzer_score(trials, all_edges, fuzzers_that_never_hit_edge)
        for fuzzer, trials in campaign.items()
    }
    return scores
