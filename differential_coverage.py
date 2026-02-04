#!/usr/bin/env python3
"""
Compute relscore (as defined in SBFT'25) from coverage in afl-showmap format (id:count per line).
Input: directory of subdirectories (one per fuzzer), each containing coverage files.
"""

import argparse
from pathlib import Path


def read_afl_showmap_file(file: Path) -> dict[int, int]:
    """Parse one afl-showmap file; return dict of edge ids to counts."""
    edges = {}
    for i, line in enumerate(file.read_text().strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        split = line.split(":")
        if len(split) != 2:
            raise ValueError(f"Invalid line {file}:{i}: {line}")
        id, count = split
        edges[int(id)] = int(count)
    return edges


def read_fuzzer_dir(path: Path) -> dict[str, dict[int, int]]:
    """Read all afl-showmap files in a directory; return dict of trial id to dict of edge ids to counts."""
    trials = {}
    for file in path.iterdir():
        if file.is_file():
            trials[file.name] = read_afl_showmap_file(file)
        else:
            raise ValueError(f"Invalid file: {file}")
    return trials


def read_campaign_dir(path: Path) -> dict[str, dict[str, dict[int, int]]]:
    """Read all fuzzer directories in a campaign directory; return dict of fuzzer name to dict of trial id to dict of edge ids to counts."""
    campaigns = {}
    for fuzzer_dir in path.iterdir():
        if fuzzer_dir.is_dir():
            campaigns[fuzzer_dir.name] = read_fuzzer_dir(fuzzer_dir)
        else:
            raise ValueError(f"Invalid file: {fuzzer_dir}")
    return campaigns


def calculate_fuzzer_score(
    trials: dict[str, dict[int, int]],
    all_edges: set[int],
    fuzzers_that_never_hit_edge: dict[int, set[str]],
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
    campaign: dict[str, dict[str, dict[int, int]]],
) -> dict[str, float]:
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

    fuzzers_that_never_hit_edge: dict[int, set[str]] = {
        edge: set(
            fuzzer
            for fuzzer, trials in campaign.items()
            if not any(trial.get(edge, 0) for trial in trials.values())
        )
        for edge in all_edges
    }

    scores = {
        fuzzer: calculate_fuzzer_score(trials, all_edges, fuzzers_that_never_hit_edge)
        for fuzzer, trials in campaign.items()
    }
    return scores


def main():
    p = argparse.ArgumentParser(
        description="Compute differential coverage from afl-showmap coverage dirs."
    )
    p.add_argument(
        "dir",
        type=Path,
        help="Directory containing one subdir per fuzzer with coverage files",
    )
    args = p.parse_args()
    root = args.dir.resolve()
    if not root.is_dir():
        p.error(f"Not a directory: {root}")

    campaign = read_campaign_dir(root)
    scores = calculate_differential_coverage_scores(campaign)
    for fuzzer, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        print(f"{fuzzer}: {score:.2f}")


if __name__ == "__main__":
    raise SystemExit(main())
