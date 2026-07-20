import argparse
import re
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import Optional, Sequence

from differential_coverage.api import DifferentialCoverage
from differential_coverage.fs import read_campaign_dir
from differential_coverage.output import print_relcov_corpus_table, print_scores

# All subcommands expect this directory layout (one campaign dir, no moving files).
CAMPAIGN_DIR_HELP = (
    "Campaign directory: one subdirectory per approach, each containing "
    "trial coverage files (afl-showmap id:count files, llvm-cov export JSON, "
    "or libFuzzer merge control files)."
)

try:
    PKG_VERSION = metadata.version("differential-coverage")
except metadata.PackageNotFoundError:
    PKG_VERSION = "unknown"


def _compile_patterns(patterns: list[str], flag_name: str) -> list[re.Pattern[str]]:
    """Compile regex patterns; raise SystemExit on invalid regex."""
    compiled: list[re.Pattern[str]] = []
    for pat in patterns:
        try:
            compiled.append(re.compile(pat))
        except re.error as e:
            raise SystemExit(f"Invalid regex for {flag_name} {pat!r}: {e}") from e
    return compiled


def _load_campaign(
    args: argparse.Namespace,
) -> dict[str, dict[str, set[str]]]:
    """Load a campaign directory and apply any CLI-level filters."""
    root = args.dir.resolve()
    try:
        campaign = read_campaign_dir(
            root,
            input_format=args.input_format,
            granularity=args.granularity,
            max_workers=args.max_workers,
        )
    except ValueError as e:
        raise SystemExit(e) from e

    include_patterns = getattr(args, "include_approach", []) or []
    exclude_patterns = getattr(args, "exclude_approach", []) or []

    if include_patterns:
        compiled = _compile_patterns(include_patterns, "--include-approach")
        campaign = {
            name: trials
            for name, trials in campaign.items()
            if any(p.search(str(name)) for p in compiled)
        }
        if not campaign:
            raise SystemExit("No approaches matched --include-approach; nothing to do.")

    if exclude_patterns:
        compiled = _compile_patterns(exclude_patterns, "--exclude-approach")
        campaign = {
            name: trials
            for name, trials in campaign.items()
            if not any(p.search(str(name)) for p in compiled)
        }
        if not campaign:
            raise SystemExit(
                "All approaches were excluded via --exclude-approach; nothing to do."
            )
    return campaign


# ---------------------------------------------------------------------------
# CLI entrypoints (delegate to API + print)
# ---------------------------------------------------------------------------


def cmd_relscore(args: argparse.Namespace) -> int:
    campaign = _load_campaign(args)
    dc = DifferentialCoverage(campaign)
    scores = dc.relscores()
    print_scores(
        scores,
        output=args.output,
        colormap=args.colormap,
        latex_enable_color=args.latex_enable_color,
        digits=args.digits,
    )
    return 0


def cmd_relcov_performance_over_approach(args: argparse.Namespace) -> int:
    campaign = _load_campaign(args)

    dc = DifferentialCoverage(campaign)
    ref_approaches = list(dc.approaches.keys())
    table = {
        f: {ref: dc.approaches[f].relcov(dc.approaches[ref]) for ref in ref_approaches}
        for f in dc.approaches
    }
    print_relcov_corpus_table(
        ref_approaches,
        table,
        output=args.output,
        colormap=args.colormap,
        latex_rotate_headers=args.latex_rotate_headers,
        latex_enable_color=args.latex_enable_color,
        digits=args.digits,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="differential-coverage",
        description=(
            "Compute differential coverage: A better way of comparing testing tools."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {PKG_VERSION}",
    )

    parser.add_argument(
        "--input-format",
        choices=["auto", "afl-showmap", "llvm-cov", "libfuzzer-merge"],
        default="auto",
        help=(
            "Input format for trial files: auto (default) detects from file "
            "content; afl-showmap for id:count files; llvm-cov for export JSON; "
            "libfuzzer-merge for -merge=1 control files."
        ),
    )
    parser.add_argument(
        "-j",
        "--jobs",
        dest="max_workers",
        type=int,
        default=None,
        metavar="N",
        help=("Maximum number of parallel workers (default: auto)."),
    )
    parser.add_argument(
        "--granularity",
        choices=["auto", "branch", "block", "edge"],
        default="auto",
        help=(
            "Coverage granularity: auto (default) uses edge for afl-showmap and "
            "libfuzzer-merge, branch for llvm-cov; branch/block for llvm-cov "
            "exports; edge for afl-showmap bitmap tuples and libFuzzer COV lines."
        ),
    )
    parser.add_argument(
        "-i",
        "--include-approach",
        action="append",
        metavar="PATTERN",
        help=(
            "Include only approaches whose name matches this regex (whitelist). "
            "Can be specified multiple times; a approach is kept if it matches any pattern."
        ),
    )
    parser.add_argument(
        "-x",
        "--exclude-approach",
        action="append",
        metavar="PATTERN",
        help=(
            "Exclude approaches whose name matches this regex. "
            "Can be specified multiple times; apply after --include-approach."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["stdout", "csv", "latex"],
        metavar="FORMAT",
        default="stdout",
        help=(
            "Output format: stdout (default) for plain text, csv for CSV, "
            'latex for LaTeX tabular (requires "latex" optional dependencies)'
        ),
    )
    parser.add_argument(
        "--digits",
        type=int,
        default=3,
        metavar="N",
        help=(
            "Number of digits after the decimal point for numeric results (default: 3)."
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

    p_relcov = subparsers.add_parser(
        "relcov",
        help=(
            "Compute relcov-based performance of each approach relative to "
            "reference approaches. Prints a table (all approaches × all approaches as reference)."
        ),
    )
    p_relcov.add_argument("dir", type=Path, help=CAMPAIGN_DIR_HELP)
    p_relcov.set_defaults(func=cmd_relcov_performance_over_approach)

    p_relscore = subparsers.add_parser(
        "relscore",
        help=(
            "Compute relscore values from a campaign directory. Prints one score per approach."
        ),
    )
    p_relscore.add_argument("dir", type=Path, help=CAMPAIGN_DIR_HELP)
    p_relscore.set_defaults(func=cmd_relscore)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func: Optional[Callable[[argparse.Namespace], int]] = getattr(args, "func", None)
    if func is None:
        # No subcommand was provided; show help and return a non-zero exit code
        parser.print_help()
        return 1
    return func(args)
