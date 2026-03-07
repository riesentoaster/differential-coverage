"""Unit tests for differential_coverage output helpers."""

import csv
import io
import sys

from differential_coverage.output import print_relcov_corpus_table

# Deliberately unsorted order for both corpus (columns) and table (rows)
_UNSORTED_CORPUS = ["z_approach", "a_approach", "m_approach"]
_UNSORTED_TABLE = {
    "z_approach": {"z_approach": 1.0, "a_approach": 0.2, "m_approach": 0.3},
    "a_approach": {"z_approach": 0.1, "a_approach": 1.0, "m_approach": 0.4},
    "m_approach": {"z_approach": 0.5, "a_approach": 0.6, "m_approach": 1.0},
}
_EXPECTED_ROWS = ["a_approach", "m_approach", "z_approach"]
_EXPECTED_COLS = ["a_approach", "m_approach", "z_approach"]


def test_relcov_table_sorted_stdout() -> None:
    """Relcov table stdout output has rows and columns sorted alphabetically."""
    out = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = out
        print_relcov_corpus_table(
            _UNSORTED_CORPUS,
            _UNSORTED_TABLE,
            output="stdout",
        )
    finally:
        sys.stdout = old_stdout

    lines = [s.strip() for s in out.getvalue().strip().splitlines()]
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
    out = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = out
        print_relcov_corpus_table(
            _UNSORTED_CORPUS,
            _UNSORTED_TABLE,
            output="csv",
        )
    finally:
        sys.stdout = old_stdout

    reader = csv.reader(io.StringIO(out.getvalue()))
    rows = list(reader)
    assert rows[0][0] == "approach"
    assert rows[0][1:] == _EXPECTED_COLS
    assert [r[0] for r in rows[1:]] == _EXPECTED_ROWS
