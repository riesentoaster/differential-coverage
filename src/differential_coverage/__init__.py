#!/usr/bin/env python3
"""
CLI for computing differential coverage scores (relscore, SBFT'25)
and related relcov-based measures from afl-showmap coverage data.

Input: directory of subdirectories (one per fuzzer), each containing coverage files.

API functions live in differential_coverage.api (and are re-exported here).
"""

import argparse
import re
from collections.abc import Callable
from pathlib import Path
from typing import Sequence

from differential_coverage.api import (
    run_relcov_performance_fuzzer,
    run_relcov_performance_fuzzer_all,
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


def _compile_patterns(patterns: list[str], flag_name: str) -> list[re.Pattern[str]]:
    """Compile regex patterns; raise SystemExit on invalid regex."""
    compiled: list[re.Pattern[str]] = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat))
        except re.error as e:
            raise SystemExit(f"Invalid regex for {flag_name} {pat!r}: {e}") from e
    return compiled


def _load_campaign(args: argparse.Namespace) -> CampaignMap:
    """Load a campaign directory and apply any CLI-level filters."""
    root = args.dir.resolve()
    campaign = read_campaign_dir(root)

    include_patterns = getattr(args, "include_fuzzer", []) or []
    exclude_patterns = getattr(args, "exclude_fuzzer", []) or []

    if include_patterns:
        compiled = _compile_patterns(include_patterns, "--include-fuzzer")
        campaign = {
            name: trials
            for name, trials in campaign.items()
            if any(p.search(str(name)) for p in compiled)
        }
        if not campaign:
            raise SystemExit("No fuzzers matched --include-fuzzer; nothing to do.")

    if exclude_patterns:
        compiled = _compile_patterns(exclude_patterns, "--exclude-fuzzer")
        campaign = {
            name: trials
            for name, trials in campaign.items()
            if not any(p.search(str(name)) for p in compiled)
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
        latex_enable_color=getattr(args, "latex_enable_color", False),
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
    latex_rotate_headers = getattr(args, "latex_rotate_headers", None)
    latex_enable_color = getattr(args, "latex_enable_color", False)
    if single is not None:
        if single not in campaign:
            raise SystemExit(
                f"Reference fuzzer {single!r} not found in campaign "
                "(it may have been excluded)."
            )
        results = run_relcov_performance_fuzzer(campaign, single)
        print_scores(
            results,
            output=output,
            colormap=colormap,
            latex_enable_color=latex_enable_color,
        )
        return 0

    ref_fuzzers, table = run_relcov_performance_fuzzer_all(campaign)
    print_relcov_corpus_table(
        ref_fuzzers,
        table,
        output=output,
        colormap=colormap,
        latex_rotate_headers=latex_rotate_headers,
        latex_enable_color=latex_enable_color,
    )
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
        "-i",
        "--include-fuzzer",
        action="append",
        metavar="PATTERN",
        help=(
            "Include only fuzzers whose name matches this regex (whitelist). "
            "Can be specified multiple times; a fuzzer is kept if it matches any pattern."
        ),
    )
    parser.add_argument(
        "-x",
        "--exclude-fuzzer",
        action="append",
        metavar="PATTERN",
        help=(
            "Exclude fuzzers whose name matches this regex. "
            "Can be specified multiple times; apply after --include-fuzzer."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["csv", "latex"],
        metavar="FORMAT",
        default=None,
        help=(
            'Output format: csv for CSV, latex for LaTeX tabular (requires "latex" optional dependencies)'
        ),
    )
    parser.add_argument(
        "--latex-rotate-headers",
        type=float,
        default=None,
        metavar="DEGREES",
        help=(
            "Rotate LaTeX table column headers by this angle in degrees (e.g. 45). "
            "Requires \\usepackage[table]{xcolor} and \\usepackage{adjustbox}."
        ),
    )
    parser.add_argument(
        "--latex-enable-color",
        action="store_true",
        help=(
            "Enable background colors for LaTeX tables and score outputs when "
            "using --output latex. Requires \\usepackage[table]{xcolor}."
        ),
    )
    parser.add_argument(
        "--latex-colormap",
        dest="colormap",
        metavar="NAME",
        default="viridis",
        help=(
            "Matplotlib colormap name to use for colored LaTeX output "
            "(e.g. viridis, plasma, magma, inferno). Default: viridis."
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

    # relcov: performance over fuzzer
    p_relcov = subparsers.add_parser(
        "relcov",
        help=(
            "Compute relcov-based performance of each fuzzer relative to "
            "reference fuzzers. By default prints a table (all fuzzers × all "
            "fuzzers as reference). Use --single to get scores for one reference only."
        ),
    )
    p_relcov.add_argument("dir", type=Path, help=CAMPAIGN_DIR_HELP)
    p_relcov.add_argument(
        "-s",
        "--single",
        metavar="FUZZER",
        help=(
            "Compute and print scores relative to this reference fuzzer only. "
            "Omit to print the full table."
        ),
    )
    p_relcov.set_defaults(func=cmd_relcov_performance_over_fuzzer)

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
