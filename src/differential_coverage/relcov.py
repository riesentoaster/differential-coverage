from statistics import median
from differential_coverage.types import (
    CoverageMap,
    EdgeIdentifier,
    FuzzerMap,
)


def covered_edges(trial: CoverageMap) -> set[EdgeIdentifier]:
    return set(edge for edge, count in trial.items() if count > 0)


def upper_coverage(
    fuzzer: FuzzerMap,
) -> set[EdgeIdentifier]:
    return set(edge for trial in fuzzer.values() for edge in covered_edges(trial))


def lower_coverage(
    fuzzer: FuzzerMap,
) -> set[EdgeIdentifier]:
    return set(
        edge
        for edge in upper_coverage(fuzzer)
        if all(trial.get(edge, 0) > 0 for trial in fuzzer.values())
    )


def relcov(
    coverage: set[EdgeIdentifier],
    other_fuzzer: FuzzerMap,
) -> float:
    other_upper = upper_coverage(other_fuzzer)
    return len(coverage.intersection(other_upper)) / len(other_upper)


def reliability(fuzzer: FuzzerMap) -> float:
    return median(relcov(covered_edges(trial), fuzzer) for trial in fuzzer.values())


def performance_over_fuzzer(
    fuzzer: FuzzerMap,
    other_fuzzer: FuzzerMap,
) -> float:
    return median(
        relcov(covered_edges(trial), other_fuzzer) for trial in fuzzer.values()
    )


def performance_over_input_corpus(
    fuzzer: FuzzerMap,
    input_corpus_coverage: CoverageMap,
) -> float:
    return relcov(covered_edges(input_corpus_coverage), fuzzer)
