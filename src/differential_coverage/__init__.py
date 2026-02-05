#!/usr/bin/env python3
"""
CLI for computing differential coverage scores (relscore, SBFT'25)
and related relcov-based measures from afl-showmap coverage data.

Input: directory of subdirectories (one per fuzzer), each containing coverage files.

API functions live in differential_coverage.api (and are re-exported here).
"""

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Sequence

from differential_coverage.api import (
    run_relcov_performance_corpus,
    run_relcov_performance_corpus_all,
    run_relcov_performance_fuzzer,
    run_relcov_performance_fuzzer_all,
    run_relcov_reliability,
    run_relscore,
)

from differential_coverage.files import read_campaign_dir
from differential_coverage.output import print_relcov_corpus_table, print_scores
from differential_coverage.types import CampaignMap, FuzzerIdentifier

# All subcommands expect this directory layout (one campaign dir, no moving files).
CAMPAIGN_DIR_HELP = (
    "Campaign directory: one subdirectory per fuzzer, each containing "
    "afl-showmap coverage files (id:count per line)."
)


def _load_campaign(args: argparse.Namespace) -> CampaignMap:
    """Load a campaign directory and apply any CLI-level filters."""
    root = args.dir.resolve()
    campaign = read_campaign_dir(root)

    # Optionally exclude some fuzzers entirely from all computations.
    excluded = set(getattr(args, "exclude_fuzzer", []) or [])
    if excluded:
        campaign = {
            name: trials for name, trials in campaign.items() if name not in excluded
        }
        if not campaign:
            raise SystemExit(
                "All fuzzers were excluded via --exclude-fuzzer; nothing to do."
            )
    return campaign


# ---------------------------------------------------------------------------
# CLI entrypoints (delegate to API + print)
# ---------------------------------------------------------------------------


def cmd_relscore(args: argparse.Namespace) -> int:
    campaign = _load_campaign(args)
    scores = run_relscore(campaign)
    print_scores(
        scores,
        output=getattr(args, "output", None),
        colormap=getattr(args, "colormap", "viridis"),
    )
    return 0


def cmd_relcov_reliability(args: argparse.Namespace) -> int:
    try:
        campaign = _load_campaign(args)
        results = run_relcov_reliability(campaign)
    except ValueError as e:
        raise SystemExit(e) from e
    print_scores(
        results,
        output=getattr(args, "output", None),
        colormap=getattr(args, "colormap", "viridis"),
    )
    return 0


def cmd_relcov_performance_over_fuzzer(args: argparse.Namespace) -> int:
    try:
        campaign = _load_campaign(args)
    except ValueError as e:
        raise SystemExit(e) from e

    single: FuzzerIdentifier | None = getattr(args, "single", None)
    output = getattr(args, "output", None)
    colormap = getattr(args, "colormap", "viridis")
    if single is not None:
        if single not in campaign:
            raise SystemExit(
                f"Reference fuzzer {single!r} not found in campaign "
                "(it may have been excluded)."
            )
        results = run_relcov_performance_fuzzer(campaign, single)
        print_scores(results, output=output, colormap=colormap)
        return 0

    ref_fuzzers, table = run_relcov_performance_fuzzer_all(campaign)
    print_relcov_corpus_table(ref_fuzzers, table, output=output, colormap=colormap)
    return 0


def cmd_relcov_performance_over_input_corpus(args: argparse.Namespace) -> int:
    try:
        campaign = _load_campaign(args)
    except ValueError as e:
        raise SystemExit(e) from e

    single: FuzzerIdentifier | None = getattr(args, "single", None)
    output = getattr(args, "output", None)
    colormap = getattr(args, "colormap", "viridis")
    if single is not None:
        if single not in campaign:
            raise SystemExit(
                f"Input corpus fuzzer {single!r} not found in campaign "
                "(it may have been excluded)."
            )
        try:
            results = run_relcov_performance_corpus(campaign, single)
        except ValueError as e:
            raise SystemExit(e) from e
        print_scores(results, output=output, colormap=colormap)
        return 0

    corpus_fuzzers, table = run_relcov_performance_corpus_all(campaign)
    print_relcov_corpus_table(corpus_fuzzers, table, output=output, colormap=colormap)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="differential-coverage",
        description=(
            "Compute differential coverage relscore and relcov-based measures "
            "from afl-showmap coverage. All commands take one campaign directory: "
            "one subdir per fuzzer, each with coverage files."
        ),
    )

    # Global options (apply to all subcommands).
    parser.add_argument(
        "-x",
        "--exclude-fuzzer",
        action="append",
        metavar="FUZZER",
        help=(
            "Exclude a fuzzer (subdirectory name) from the analysis. "
            "Can be specified multiple times."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["csv", "latex", "latex-color"],
        metavar="FORMAT",
        default=None,
        help=(
            "Output format: csv for CSV, latex for LaTeX tabular, "
            "latex-color for LaTeX tabular with cell colors scaled "
            "between global min and max "
            "(default: human-readable text to stdout)."
        ),
    )
    parser.add_argument(
        "--colormap",
        "-c",
        metavar="NAME",
        default="viridis",
        help=(
            "Matplotlib colormap name for latex-color output (e.g. viridis, "
            "plasma, magma, inferno). Default: viridis."
        ),
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="command",
        metavar="command",
    )

    # relscore: original behaviour
    p_relscore = subparsers.add_parser(
        "relscore",
        help=(
            "Compute relscore (SBFT'25) from a campaign directory containing "
            "one subdirectory per fuzzer with afl-showmap files."
        ),
    )
    p_relscore.add_argument("dir", type=Path, help=CAMPAIGN_DIR_HELP)
    p_relscore.set_defaults(func=cmd_relscore)

    # relcov: reliability
    p_reliability = subparsers.add_parser(
        "relcov-reliability",
        help="Compute relcov-based reliability for each fuzzer.",
    )
    p_reliability.add_argument("dir", type=Path, help=CAMPAIGN_DIR_HELP)
    p_reliability.set_defaults(func=cmd_relcov_reliability)

    # relcov: performance over fuzzer
    p_perf_fuzzer = subparsers.add_parser(
        "relcov-performance-fuzzer",
        help=(
            "Compute relcov-based performance of each fuzzer relative to "
            "reference fuzzers. By default prints a table (all fuzzers × all "
            "fuzzers as reference). Use --single to get scores for one reference only."
        ),
    )
    p_perf_fuzzer.add_argument("dir", type=Path, help=CAMPAIGN_DIR_HELP)
    p_perf_fuzzer.add_argument(
        "-s",
        "--single",
        metavar="FUZZER",
        help=(
            "Compute and print scores relative to this reference fuzzer only. "
            "Omit to print the full table."
        ),
    )
    p_perf_fuzzer.set_defaults(func=cmd_relcov_performance_over_fuzzer)

    # relcov: performance over input corpus
    p_perf_corpus = subparsers.add_parser(
        "relcov-performance-corpus",
        help=(
            "Compute relcov-based performance of each fuzzer relative to input "
            "corpora. By default prints a table (all fuzzers × all single-trial "
            "corpus fuzzers). Use --single to get scores for one corpus only."
        ),
    )
    p_perf_corpus.add_argument("dir", type=Path, help=CAMPAIGN_DIR_HELP)
    p_perf_corpus.add_argument(
        "-s",
        "--single",
        metavar="FUZZER",
        help=(
            "Compute and print scores for this corpus fuzzer only (single-trial "
            "subdir). Omit to print the full table for all corpus fuzzers."
        ),
    )
    p_perf_corpus.set_defaults(func=cmd_relcov_performance_over_input_corpus)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func: Callable[[argparse.Namespace], int] | None = getattr(args, "func", None)
    if func is None:
        # No subcommand was provided; show help and return a non-zero exit code
        parser.print_help()
        return 1
    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())
