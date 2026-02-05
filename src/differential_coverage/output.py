"""Output helpers for the differential_coverage CLI."""

from __future__ import annotations

import csv
import sys
from collections.abc import Mapping, Sequence
from typing import Literal

import matplotlib.colors as mcolors
from matplotlib import colormaps

from differential_coverage.types import FuzzerIdentifier

OutputFormat = Literal["csv", "latex", "latex-color"]


def print_scores(
    scores: Mapping[FuzzerIdentifier, float],
    *,
    output: OutputFormat | None = None,
    colormap: str = "viridis",
) -> None:
    """Print one score per fuzzer, in the requested output format."""
    name_sorted = sorted(scores.items(), key=lambda x: x[0])
    performance_sorted = sorted(name_sorted, key=lambda x: x[1], reverse=True)

    if output == "csv":
        _print_scores_csv(performance_sorted)
    elif output == "latex":
        _print_scores_latex(performance_sorted)
    elif output == "latex-color":
        _print_scores_latex_color(performance_sorted, colormap=colormap)
    else:
        _print_scores_plain(performance_sorted)


def _print_scores_plain(
    performance_sorted: Sequence[tuple[FuzzerIdentifier, float]],
) -> None:
    for fuzzer, score in performance_sorted:
        print(f"{fuzzer}: {score:.2f}")


def _print_scores_csv(
    performance_sorted: Sequence[tuple[FuzzerIdentifier, float]],
) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(("fuzzer", "score"))
    for fuzzer, score in performance_sorted:
        writer.writerow((fuzzer, f"{score:.2f}"))


def _print_scores_latex(
    performance_sorted: Sequence[tuple[FuzzerIdentifier, float]],
) -> None:
    # Simple LaTeX table without requiring additional packages.
    print(r"\begin{tabular}{lr}")
    print(r"fuzzer & score \\")
    print(r"\hline")
    for fuzzer, score in performance_sorted:
        print(f"{fuzzer} & {score:.2f} \\\\")
    print(r"\end{tabular}")


def _print_scores_latex_color(
    performance_sorted: Sequence[tuple[FuzzerIdentifier, float]],
    *,
    colormap: str = "viridis",
) -> None:
    """LaTeX table where score cells are colored by value."""
    if not performance_sorted:
        print(r"\begin{tabular}{lr}")
        print(r"fuzzer & score \\")
        print(r"\end{tabular}")
        return

    values = [score for _, score in performance_sorted]
    min_v = min(values)
    max_v = max(values)

    def _norm(v: float) -> float:
        if max_v <= min_v:
            return 0.5
        return (v - min_v) / (max_v - min_v)

    print(r"\begin{tabular}{lr}")
    print(r"fuzzer & score \\")
    print(r"\hline")
    for fuzzer, score in performance_sorted:
        n = _norm(score)
        hex_color = _colormap_light_hex(n, colormap=colormap)
        print(rf"{fuzzer} & \cellcolor[HTML]{{{hex_color}}}{{{score:.2f}}} \\")
    print(r"\end{tabular}")


def print_relcov_corpus_table(
    corpus_fuzzers: Sequence[FuzzerIdentifier],
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
    *,
    output: OutputFormat | None = None,
    colormap: str = "viridis",
) -> None:
    """Print a table of relcov performance: rows = fuzzers, columns = corpus fuzzers."""
    if not corpus_fuzzers:
        print("No corpus fuzzers (single-trial subdirs) found.")
        return

    if output == "csv":
        _print_relcov_corpus_table_csv(corpus_fuzzers, table)
    elif output == "latex":
        _print_relcov_corpus_table_latex(corpus_fuzzers, table)
    elif output == "latex-color":
        _print_relcov_corpus_table_latex_color(corpus_fuzzers, table, colormap=colormap)
    else:
        _print_relcov_corpus_table_plain(corpus_fuzzers, table)


def _print_relcov_corpus_table_plain(
    corpus_fuzzers: Sequence[FuzzerIdentifier],
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
) -> None:
    row_labels = sorted(table.keys())
    col_width = max(
        (len(str(c)) for c in list(corpus_fuzzers) + ["fuzzer"]),
        default=7,
    )
    num_width = 10  # e.g. " 1.00"
    header = "fuzzer".ljust(col_width)
    for c in corpus_fuzzers:
        header += str(c).rjust(num_width)
    print(header)
    for row in row_labels:
        line = str(row).ljust(col_width)
        for c in corpus_fuzzers:
            val = table[row].get(c)
            if val is not None:
                line += f"{val:>{num_width}.5f}"
            else:
                line += " " * num_width
        print(line)


def _print_relcov_corpus_table_csv(
    corpus_fuzzers: Sequence[FuzzerIdentifier],
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
) -> None:
    row_labels = sorted(table.keys())
    writer = csv.writer(sys.stdout)
    writer.writerow(["fuzzer"] + list(corpus_fuzzers))
    for row in row_labels:
        cells: list[str] = [str(row)]
        for c in corpus_fuzzers:
            val = table[row].get(c)
            cells.append(f"{val:.3f}" if val is not None else "")
        writer.writerow(cells)


def _latex_print_rotcol_command() -> None:
    """Emit the \\rotcol LaTeX command definition.
    Requires \\usepackage{graphicx} and \\usepackage{calc}.
    Rotated text is raised so it stays in the header row; row height is \\widthof{#1}.
    """
    # Raise rotated text by half its width so it doesn't extend below the baseline
    # into the first data row; then reserve full width as row height.
    print(
        r"""\newcolumntype{R}[2]{%
    >{\adjustbox{angle=#1,lap=\width-(#2)}\bgroup}%
    l%
    <{\egroup}%
}
\newcommand*\rotcol{\multicolumn{1}{R{45}{1em}}}%"""
    )


def _latex_rotcol(text: str) -> str:
    """Format text as a rotated column header using the \\rotcol command."""
    return r"\rotcol{" + text + r"}"


def _print_relcov_corpus_table_latex(
    corpus_fuzzers: Sequence[FuzzerIdentifier],
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
) -> None:
    row_labels = sorted(table.keys())
    num_cols = 1 + len(corpus_fuzzers)
    # Use a simple alignment: first column left, others right.
    align_spec = "l" + "r" * (num_cols - 1)
    _latex_print_rotcol_command()
    print(r"\begin{tabular}{" + align_spec + r"}")
    header_cells = [""] + [_latex_rotcol(str(c)) for c in corpus_fuzzers]
    print(" & ".join(header_cells) + r" \\")
    print(r"\hline")
    for row in row_labels:
        cells: list[str] = [str(row)]
        for c in corpus_fuzzers:
            val = table[row].get(c)
            cells.append(f"{val:.3f}" if val is not None else "")
        print(" & ".join(cells) + r" \\")
    print(r"\end{tabular}")


def _collect_numeric_values(
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
) -> list[float]:
    values: list[float] = []
    for row in table.values():
        for val in row.values():
            if isinstance(val, (int, float)):
                values.append(float(val))
    return values


def _print_relcov_corpus_table_latex_color(
    corpus_fuzzers: Sequence[FuzzerIdentifier],
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
    *,
    colormap: str = "viridis",
) -> None:
    """LaTeX table where data cells are colored by global min/max."""
    row_labels = sorted(table.keys())
    all_values = _collect_numeric_values(table)
    if all_values:
        min_v = min(all_values)
        max_v = max(all_values)
    else:
        min_v = max_v = 0.0

    def _norm(v: float | None) -> float:
        if v is None:
            return 0.0
        if max_v <= min_v:
            return 0.5
        return (v - min_v) / (max_v - min_v)

    num_cols = 1 + len(corpus_fuzzers)
    align_spec = "l" + "r" * (num_cols - 1)
    _latex_print_rotcol_command()
    print(r"\begin{tabular}{" + align_spec + r"}")
    header_cells = [""] + [_latex_rotcol(str(c)) for c in corpus_fuzzers]
    print(" & ".join(header_cells) + r" \\")
    print(r"\hline")
    for row in row_labels:
        cells: list[str] = [str(row)]
        for c in corpus_fuzzers:
            val = table[row].get(c)
            if val is None:
                cells.append("")
            else:
                n = _norm(val)
                hex_color = _colormap_light_hex(n, colormap=colormap)
                cells.append(rf"\cellcolor[HTML]{{{hex_color}}}{{{val:.3f}}}")
        print(" & ".join(cells) + r" \\")
    print(r"\end{tabular}")


def _colormap_light_hex(t: float, *, colormap: str = "viridis") -> str:
    """
    Return a hex color for t in [0, 1] using the light portion (60%–100%) of a
    matplotlib colormap so backgrounds stay light enough for black text.
    colormap is any matplotlib colormap name (e.g. 'viridis', 'plasma', 'magma').
    """
    t = max(0.0, min(1.0, t))
    t = 1 - t  # invert the color map
    if colormap not in colormaps:
        raise ValueError(f"Invalid colormap: {colormap}")
    cmap = colormaps[colormap]
    v = 0.6 + 0.4 * t
    rgba = cmap(v)
    return mcolors.to_hex((rgba[0], rgba[1], rgba[2]), keep_alpha=False)[1:].upper()
