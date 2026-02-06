"""Unit tests for the differential_coverage CLI using tests/sample_coverage data."""

import io
import sys
from pathlib import Path
import pytest

from differential_coverage import main

SAMPLE_DIR = (Path(__file__).parent / "sample_coverage").resolve()


def _run_cli(
    argv: list[str], capture_stderr: bool = False
) -> tuple[int | str, str, str]:
    """Run main with argv; return (exit_code, stdout, stderr)."""
    out = io.StringIO()
    err = io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    code: int | str
    try:
        sys.stdout = out
        sys.stderr = err if capture_stderr else old_stderr
        code = main(argv)
    except SystemExit as e:
        code = e.code if e.code is not None else 1
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr
    return (code, out.getvalue(), err.getvalue() if capture_stderr else "")


def test_cli_relscore() -> None:
    """CLI relscore prints all fuzzers sorted by score descending."""
    code, out, _ = _run_cli(["relscore", str(SAMPLE_DIR)])
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 4  # fuzzer_c, fuzzer_a, fuzzer_b, seeds
    # Scores are descending (relscore over full campaign including seeds)
    assert any(line.startswith("fuzzer_c:") for line in lines)
    assert any(line.startswith("fuzzer_a:") for line in lines)
    assert any(line.startswith("fuzzer_b:") for line in lines)
    assert any(line.startswith("seeds:") for line in lines)
    # First line is highest scorer
    assert lines[0].startswith("fuzzer_c:")


def test_cli_relcov_performance_fuzzer_single() -> None:
    """CLI relcov with --single prints other fuzzers."""
    code, out, _ = _run_cli(
        [
            "relcov",
            str(SAMPLE_DIR),
            "--single",
            "fuzzer_c",
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    # All fuzzers except fuzzer_c (and seeds)
    assert any("fuzzer_a" in line for line in lines)
    assert any("fuzzer_b" in line for line in lines)
    assert not any(line.startswith("fuzzer_c:") for line in lines)


def test_cli_relcov_performance_fuzzer_table() -> None:
    """CLI relcov without --single prints a table."""
    code, out, _ = _run_cli(
        [
            "relcov",
            str(SAMPLE_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    # Header: fuzzer + all fuzzers as columns
    assert "fuzzer" in lines[0].lower()
    assert "fuzzer_a" in lines[0] or "fuzzer_b" in lines[0]
    assert any("fuzzer_a" in line for line in lines)
    assert any("fuzzer_b" in line for line in lines)
    assert any("fuzzer_c" in line for line in lines)
    assert any("seeds" in line for line in lines)


def test_cli_exclude_fuzzer_relscore() -> None:
    """CLI --exclude-fuzzer removes fuzzers from relscore output."""
    code, out, _ = _run_cli(
        [
            "--exclude-fuzzer",
            "seeds",
            "--exclude-fuzzer",
            "fuzzer_b",
            "relscore",
            str(SAMPLE_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 2  # only fuzzer_a and fuzzer_c
    assert any("fuzzer_c" in line for line in lines)
    assert any("fuzzer_a" in line for line in lines)
    assert not any("fuzzer_b" in line for line in lines)
    assert not any("seeds" in line for line in lines)


def test_cli_exclude_fuzzer_performance_fuzzer() -> None:
    """CLI --exclude-fuzzer with relcov --single; reference must not be excluded."""
    code, _, _ = _run_cli(
        [
            "--exclude-fuzzer",
            "fuzzer_c",
            "relcov",
            str(SAMPLE_DIR),
            "--single",
            "fuzzer_c",
        ]
    )
    assert code != 0


@pytest.mark.parametrize(
    "pattern", ["fuzzer_[bc]", "fuzzer_b|fuzzer_c", "fuzzer_(b|c)"]
)
def test_cli_exclude_fuzzer_regex(pattern: str) -> None:
    """CLI --exclude-fuzzer accepts regex; one pattern can exclude multiple fuzzers."""
    code, out, _ = _run_cli(
        [
            "--exclude-fuzzer",
            pattern,  # regex: matches fuzzer_b and fuzzer_c
            "relscore",
            str(SAMPLE_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert any("fuzzer_a" in line for line in lines)
    assert any("seeds" in line for line in lines)
    assert not any("fuzzer_b" in line for line in lines)
    assert not any("fuzzer_c" in line for line in lines)


def test_cli_include_fuzzer_regex() -> None:
    """CLI --include-fuzzer whitelists by regex; only matching fuzzers are used."""
    code, out, _ = _run_cli(
        [
            "--include-fuzzer",
            "fuzzer_.*",  # only fuzzer_a, fuzzer_b, fuzzer_c (not seeds)
            "relscore",
            str(SAMPLE_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 3
    assert any("fuzzer_a" in line for line in lines)
    assert any("fuzzer_b" in line for line in lines)
    assert any("fuzzer_c" in line for line in lines)
    assert not any("seeds" in line for line in lines)


def test_cli_include_then_exclude() -> None:
    """Include applies first, then exclude (both regex)."""
    code, out, _ = _run_cli(
        [
            "--include-fuzzer",
            "fuzzer_.*",
            "--exclude-fuzzer",
            "fuzzer_b",
            "relscore",
            str(SAMPLE_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 2  # fuzzer_a, fuzzer_c
    assert any("fuzzer_a" in line for line in lines)
    assert any("fuzzer_c" in line for line in lines)
    assert not any("fuzzer_b" in line for line in lines)
    assert not any("seeds" in line for line in lines)


def test_cli_csv_relscore() -> None:
    """CLI --output csv with relscore outputs CSV with header fuzzer,score."""
    code, out, _ = _run_cli(["--output", "csv", "relscore", str(SAMPLE_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert lines[0] == "fuzzer,score"
    assert len(lines) == 5  # header + 4 fuzzers
    assert any("fuzzer_c," in line for line in lines[1:])
    assert any("fuzzer_a," in line for line in lines[1:])


def test_cli_csv_relcov_performance_fuzzer_table() -> None:
    """CLI --output csv with relcov (table) outputs CSV with header row."""
    code, out, _ = _run_cli(["--output", "csv", "relcov", str(SAMPLE_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert "fuzzer" in lines[0]
    assert "fuzzer_a" in lines[0] or "fuzzer_b" in lines[0]
    assert len(lines) >= 4  # header + data rows


def test_cli_latex_relcov_performance_fuzzer_table() -> None:
    """CLI --output latex with relcov (table) outputs LaTeX tabular."""
    code, out, _ = _run_cli(["--output", "latex", "relcov", str(SAMPLE_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert any(line.startswith(r"\begin{tabular}") for line in lines)
    assert any("fuzzer" in line for line in lines)
    assert lines[-1] == r"\end{tabular}"


def test_cli_latex_color_relcov_performance_fuzzer_table() -> None:
    """CLI --output latex with --latex-enable-color outputs colored LaTeX tabular."""
    code, out, _ = _run_cli(
        [
            "--output",
            "latex",
            "--latex-enable-color",
            "relcov",
            str(SAMPLE_DIR),
        ]
    )
    assert code == 0
    lines = out.strip().splitlines()
    assert any(line.startswith(r"\begin{tabular}") for line in lines)
    assert any(r"\cellcolor" in line for line in lines)
    assert lines[-1] == r"\end{tabular}"


def test_cli_latex_default_no_rotate_headers() -> None:
    """CLI LaTeX output without --latex-rotate-headers emits unrotated headers."""
    code, out, _ = _run_cli(["--output", "latex", "relcov", str(SAMPLE_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert any(line.startswith(r"\begin{tabular}") for line in lines)
    assert not any(r"\rotcol{" in line for line in lines)


def test_cli_latex_rotate_headers_angle() -> None:
    """CLI --latex-rotate-headers 45 emits rotated headers with that angle."""
    code, out, _ = _run_cli(
        [
            "--output",
            "latex",
            "--latex-rotate-headers",
            "45",
            "relcov",
            str(SAMPLE_DIR),
        ]
    )
    assert code == 0
    lines = out.strip().splitlines()
    assert any(r"\rotcol{" in line for line in lines)
    assert any("R{45}" in line for line in lines)


def test_cli_latex_color_no_cell_colors() -> None:
    """CLI latex output without --latex-enable-color disables \\cellcolor."""
    code, out, _ = _run_cli(
        [
            "--output",
            "latex",
            "relcov",
            str(SAMPLE_DIR),
        ]
    )
    assert code == 0
    lines = out.strip().splitlines()
    assert any(line.startswith(r"\begin{tabular}") for line in lines)
    # Table should not contain any colored cells
    assert not any(r"\cellcolor" in line for line in lines)
