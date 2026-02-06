"""Output helpers for the differential_coverage CLI."""

from __future__ import annotations

import csv
import sys
from collections.abc import Mapping, Sequence
from typing import Literal


from differential_coverage.types import FuzzerIdentifier

OutputFormat = Literal["csv", "latex"]


def print_scores(
    scores: Mapping[FuzzerIdentifier, float],
    *,
    output: OutputFormat | None = None,
    colormap: str = "viridis",
    latex_enable_color: bool = False,
) -> None:
    """Print one score per fuzzer, in the requested output format."""
    name_sorted = sorted(scores.items(), key=lambda x: x[0])
    performance_sorted = sorted(name_sorted, key=lambda x: x[1], reverse=True)

    if output == "csv":
        _print_scores_csv(performance_sorted)
    elif output == "latex":
        _print_scores_latex(
            performance_sorted,
            enable_color=latex_enable_color,
            colormap=colormap,
        )
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


def _norm_minmax(values: Sequence[float]) -> tuple[float, float]:
    """Return (min, max); if empty or single value, return (0, 0) for safe norm."""
    if not values:
        return (0.0, 0.0)
    return (min(values), max(values))


def _norm_value(v: float, min_v: float, max_v: float) -> float:
    """Map v in [min_v, max_v] to [0, 1]; if min_v == max_v return 0.5."""
    if max_v <= min_v:
        return 0.5
    return (v - min_v) / (max_v - min_v)


def _print_scores_latex(
    performance_sorted: Sequence[tuple[FuzzerIdentifier, float]],
    *,
    enable_color: bool = False,
    colormap: str = "viridis",
) -> None:
    """LaTeX table (optionally with score cells colored by value)."""
    print(r"\begin{tabular}{lr}")
    print(r"fuzzer & score \\")
    if not performance_sorted:
        print(r"\end{tabular}")
        return
    print(r"\hline")
    min_v, max_v = (0.0, 0.0)
    if enable_color:
        values = [s for _, s in performance_sorted]
        min_v, max_v = _norm_minmax(values)
    for fuzzer, score in performance_sorted:
        if enable_color:
            n = _norm_value(score, min_v, max_v)
            hex_color = _colormap_light_hex(n, colormap=colormap)
            print(rf"{fuzzer} & \cellcolor[HTML]{{{hex_color}}}{{{score:.2f}}} \\")
        else:
            print(f"{fuzzer} & {score:.2f} \\\\")
    print(r"\end{tabular}")


def print_relcov_corpus_table(
    corpus_fuzzers: Sequence[FuzzerIdentifier],
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
    *,
    output: OutputFormat | None = None,
    colormap: str = "viridis",
    latex_rotate_headers: float | None = None,
    latex_enable_color: bool = False,
) -> None:
    """Print a table of relcov performance: rows = fuzzers, columns = corpus fuzzers."""
    if not corpus_fuzzers:
        print("No corpus fuzzers (single-trial subdirs) found.")
        return

    if output == "csv":
        _print_relcov_corpus_table_csv(corpus_fuzzers, table)
    elif output == "latex":
        _print_relcov_corpus_table_latex(
            corpus_fuzzers,
            table,
            rotate_headers=latex_rotate_headers,
            enable_color=latex_enable_color,
            colormap=colormap,
        )
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


def _latex_print_rotcol_command(*, angle: float | None) -> None:
    """Emit the \\rotcol LaTeX command definition.
    Requires \\usepackage{graphicx} and \\usepackage{calc}.
    Rotated text is raised so it stays in the header row; row height is \\widthof{#1}.
    """
    if angle is None:
        return

    # Raise rotated text by half its width so it doesn't extend below the baseline
    # into the first data row; then reserve full width as row height.
    print(
        r"""\newcolumntype{R}[2]{%
    >{\adjustbox{angle=#1,lap=\width-(#2)}\bgroup}%
    l%
    <{\egroup}%
}
"""
        + rf"\newcommand*\rotcol{{\multicolumn{{1}}{{R{{{angle:.0f}}}{{1em}}}}}}%"
    )


def _latex_rotcol(text: str, *, angle: float | None) -> str:
    """Format text as a (possibly rotated) column header using the \\rotcol command."""
    if angle is None:
        return text
    return r"\rotcol{" + text + r"}"


def _collect_numeric_values(
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
) -> list[float]:
    values: list[float] = []
    for row in table.values():
        for val in row.values():
            if isinstance(val, (int, float)):
                values.append(float(val))
    return values


def _print_relcov_corpus_table_latex(
    corpus_fuzzers: Sequence[FuzzerIdentifier],
    table: Mapping[FuzzerIdentifier, Mapping[FuzzerIdentifier, float]],
    *,
    rotate_headers: float | None,
    enable_color: bool = False,
    colormap: str = "viridis",
) -> None:
    try:
        from pylatex.utils import escape_latex  # type: ignore[import-untyped] # does not provide types
    except ImportError:
        raise ImportError('latex support requires the "latex" optional dependencies')

    """LaTeX table (optionally with data cells colored by global min/max)."""
    row_labels = sorted(table.keys())
    min_v, max_v = (0.0, 0.0)
    if enable_color:
        all_values = _collect_numeric_values(table)
        min_v, max_v = _norm_minmax(all_values)

    num_cols = 1 + len(corpus_fuzzers)
    align_spec = "l" + "r" * (num_cols - 1)
    _latex_print_rotcol_command(angle=rotate_headers)
    print(r"\begin{tabular}{" + align_spec + r"}")
    header_cells = [""] + [
        _latex_rotcol(escape_latex(str(c)), angle=rotate_headers)
        for c in corpus_fuzzers
    ]
    print(" & ".join(header_cells) + r" \\")
    print(r"\hline")
    for row in row_labels:
        cells: list[str] = [escape_latex(str(row))]
        for c in corpus_fuzzers:
            val = table[row].get(c)
            if val is None:
                cells.append("")
            elif enable_color:
                n = _norm_value(val, min_v, max_v)
                hex_color = _colormap_light_hex(n, colormap=colormap)
                cells.append(rf"\cellcolor[HTML]{{{hex_color}}}{{{val:.3f}}}")
            else:
                cells.append(f"{val:.3f}")
        print(" & ".join(cells) + r" \\")
    print(r"\end{tabular}")


def _colormap_light_hex(t: float, *, colormap: str = "viridis") -> str:
    """
    Return a hex color for t in [0, 1] using the light portion (60%–100%) of a
    matplotlib colormap so backgrounds stay light enough for black text.
    colormap is any matplotlib colormap name (e.g. 'viridis', 'plasma', 'magma').
    """
    try:
        import matplotlib.colors as mcolors
        from matplotlib import colormaps
    except ImportError:
        raise ImportError('latex support requires the "latex" optional dependencies')

    t = max(0.0, min(1.0, t))
    if colormap not in colormaps:
        raise ValueError(f"Invalid colormap: {colormap}")
    cmap = colormaps[colormap]
    [r, g, b, a] = cmap(t)
    [r, g, b] = [1 - ((1 - e) * 0.3) for e in [r, g, b]]

    return mcolors.to_hex((r, g, b), keep_alpha=False)[1:].upper()
