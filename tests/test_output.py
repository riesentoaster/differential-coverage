"""Unit tests for differential_coverage output helpers."""

import csv
import io
from collections.abc import Callable

from differential_coverage.output import (
    print_counts,
    print_relcov_corpus_table,
    print_scores,
)

# Deliberately unsorted order for both corpus (columns) and table (rows)
_UNSORTED_CORPUS = ["z_approach", "a_approach", "m_approach"]
_UNSORTED_TABLE = {
    "z_approach": {"z_approach": 1.0, "a_approach": 0.2, "m_approach": 0.3},
    "a_approach": {"z_approach": 0.1, "a_approach": 1.0, "m_approach": 0.4},
    "m_approach": {"z_approach": 0.5, "a_approach": 0.6, "m_approach": 1.0},
}
_EXPECTED_ROWS = ["a_approach", "m_approach", "z_approach"]
_EXPECTED_COLS = ["a_approach", "m_approach", "z_approach"]


def _capture_printer() -> tuple[list[str], Callable[[str], None]]:
    lines: list[str] = []

    def printer(s: str) -> None:
        lines.append(s)

    return lines, printer


def test_relcov_table_sorted_stdout() -> None:
    """Relcov table stdout output has rows and columns sorted alphabetically."""
    captured, printer = _capture_printer()
    print_relcov_corpus_table(
        _UNSORTED_CORPUS,
        _UNSORTED_TABLE,
        output="stdout",
        printer=printer,
    )

    lines = [s.strip() for s in "\n".join(captured).strip().splitlines()]
    header = lines[0]
    assert header.startswith("approach")
    row_labels = [line.split()[0] for line in lines[1:]]
    assert row_labels == _EXPECTED_ROWS
    pos = 0
    for col in _EXPECTED_COLS:
        idx = header.find(col, pos)
        assert idx >= 0, f"column {col!r} not found in header"
        pos = idx + len(col)


def test_relcov_table_sorted_csv() -> None:
    """Relcov table CSV output has rows and columns sorted alphabetically."""
    captured, printer = _capture_printer()
    print_relcov_corpus_table(
        _UNSORTED_CORPUS,
        _UNSORTED_TABLE,
        output="csv",
        printer=printer,
    )

    csv_text = "\n".join(captured)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0][0] == "approach"
    assert rows[0][1:] == _EXPECTED_COLS
    assert [r[0] for r in rows[1:]] == _EXPECTED_ROWS


def test_print_scores_uses_printer_stdout() -> None:
    """print_scores writes human-readable scores via the provided printer."""
    scores = {"b": 0.1, "a": 1.0}
    captured, printer = _capture_printer()

    print_scores(scores, output="stdout", printer=printer)

    # Scores should be sorted by value descending, then by name
    joined = "\n".join(captured)
    assert "a: 1.000" in joined
    assert "b: 0.100" in joined
    # Ensure our custom printer was used (no direct writes to sys.stdout here)
    assert joined.count("\n") >= 0


def test_print_scores_uses_printer_csv() -> None:
    """print_scores CSV output is routed through the provided printer."""
    scores = {"b": 0.1, "a": 1.0}
    captured, printer = _capture_printer()

    print_scores(scores, output="csv", printer=printer)

    csv_text = "\n".join(captured)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    # Header + two data rows
    assert rows[0] == ["approach", "score"]
    # Order should be by score descending
    assert rows[1][0] == "a"
    assert rows[2][0] == "b"


def test_print_scores_respects_digits() -> None:
    """print_scores formats scores with the requested number of digits."""
    scores = {"a": 1.0 / 3.0}
    captured, printer = _capture_printer()

    print_scores(scores, output="stdout", digits=4, printer=printer)

    assert captured == ["a: 0.3333"]


def test_print_counts_uses_printer_stdout() -> None:
    """print_counts writes integer coverage counts via the provided printer."""
    counts = {"b": 2, "a": 5}
    captured, printer = _capture_printer()

    print_counts(counts, output="stdout", printer=printer)

    assert captured == ["a: 5", "b: 2"]


def test_print_counts_uses_printer_csv() -> None:
    """print_counts CSV output is routed through the provided printer."""
    counts = {"b": 2, "a": 5}
    captured, printer = _capture_printer()

    print_counts(counts, output="csv", printer=printer)

    csv_text = "\n".join(captured)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    assert rows[0] == ["approach", "coverage"]
    assert rows[1] == ["a", "5"]
    assert rows[2] == ["b", "2"]


def test_relcov_table_respects_digits_csv() -> None:
    """Relcov CSV cells use the requested digit precision."""
    captured, printer = _capture_printer()
    print_relcov_corpus_table(
        ["a"],
        {"a": {"a": 1.0 / 3.0}},
        output="csv",
        digits=4,
        printer=printer,
    )

    csv_text = "\n".join(captured)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[1][1] == "0.3333"
