"""Unit tests for the differential_coverage CLI using tests/sample_coverage data."""

import io
import sys
from pathlib import Path

import pytest

from differential_coverage.cli import main

SAMPLE_SHOWMAP_DIR = (Path(__file__).parent / "sample_coverage").resolve()


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


def test_cli_jobs_passed_to_read_campaign_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, int | None] = {}

    def fake_read_campaign_dir(
        path: Path,
        *,
        input_format: str = "auto",
        granularity: str = "auto",
        max_workers: int | None = None,
    ) -> dict[str, dict[str, set[str]]]:
        seen["max_workers"] = max_workers
        return {
            "approach_a": {"t1": {"e1"}},
            "approach_b": {"t1": {"e1"}},
        }

    monkeypatch.setattr(
        "differential_coverage.cli.read_campaign_dir", fake_read_campaign_dir
    )
    code, _, _ = _run_cli(["-j", "4", "relscore", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    assert seen["max_workers"] == 4


def test_cli_jobs_rejects_zero() -> None:
    code, _, _ = _run_cli(
        ["-j", "0", "relscore", str(SAMPLE_SHOWMAP_DIR)], capture_stderr=True
    )
    assert code != 0


def test_cli_relscore_rejects_unsupported_granularity() -> None:
    code, _, _ = _run_cli(
        ["--granularity", "branch", "relscore", str(SAMPLE_SHOWMAP_DIR)],
        capture_stderr=True,
    )
    assert code != 0


def test_cli_relscore() -> None:
    """CLI relscore prints all approaches sorted by score descending."""
    code, out, _ = _run_cli(["relscore", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 4  # approach_c, approach_a, approach_b, seeds
    # Scores are descending (relscore over full campaign including seeds)
    assert any(line.startswith("approach_c:") for line in lines)
    assert any(line.startswith("approach_a:") for line in lines)
    assert any(line.startswith("approach_b:") for line in lines)
    assert any(line.startswith("seeds:") for line in lines)
    # First line is highest scorer
    assert lines[0].startswith("approach_c:")


def test_cli_relcov_performance_approach_table() -> None:
    """CLI relcov prints a table."""
    code, out, _ = _run_cli(
        [
            "relcov",
            str(SAMPLE_SHOWMAP_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    # Header: approach + all approaches as columns
    assert "approach" in lines[0].lower()
    assert "approach_a" in lines[0] or "approach_b" in lines[0]
    assert any("approach_a" in line for line in lines)
    assert any("approach_b" in line for line in lines)
    assert any("approach_c" in line for line in lines)
    assert any("seeds" in line for line in lines)


def test_cli_exclude_approach_relscore() -> None:
    """CLI --exclude-approach removes approaches from relscore output."""
    code, out, _ = _run_cli(
        [
            "--exclude-approach",
            "seeds",
            "--exclude-approach",
            "approach_b",
            "relscore",
            str(SAMPLE_SHOWMAP_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 2  # only approach_a and approach_c
    assert any("approach_c" in line for line in lines)
    assert any("approach_a" in line for line in lines)
    assert not any("approach_b" in line for line in lines)
    assert not any("seeds" in line for line in lines)


@pytest.mark.parametrize(
    "pattern", ["approach_[bc]", "approach_b|approach_c", "approach_(b|c)"]
)
def test_cli_exclude_approach_regex(pattern: str) -> None:
    """CLI --exclude-approach accepts regex; one pattern can exclude multiple approaches."""
    code, out, _ = _run_cli(
        [
            "--exclude-approach",
            pattern,  # regex: matches approach_b and approach_c
            "relscore",
            str(SAMPLE_SHOWMAP_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert any("approach_a" in line for line in lines)
    assert any("seeds" in line for line in lines)
    assert not any("approach_b" in line for line in lines)
    assert not any("approach_c" in line for line in lines)


def test_cli_include_approach_regex() -> None:
    """CLI --include-approach whitelists by regex; only matching approaches are used."""
    code, out, _ = _run_cli(
        [
            "--include-approach",
            "approach_.*",  # only approach_a, approach_b, approach_c (not seeds)
            "relscore",
            str(SAMPLE_SHOWMAP_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 3
    assert any("approach_a" in line for line in lines)
    assert any("approach_b" in line for line in lines)
    assert any("approach_c" in line for line in lines)
    assert not any("seeds" in line for line in lines)


def test_cli_include_then_exclude() -> None:
    """Include applies first, then exclude (both regex)."""
    code, out, _ = _run_cli(
        [
            "--include-approach",
            "approach_.*",
            "--exclude-approach",
            "approach_b",
            "relscore",
            str(SAMPLE_SHOWMAP_DIR),
        ]
    )
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 2  # approach_a, approach_c
    assert any("approach_a" in line for line in lines)
    assert any("approach_c" in line for line in lines)
    assert not any("approach_b" in line for line in lines)
    assert not any("seeds" in line for line in lines)


def test_cli_csv_relscore() -> None:
    """CLI --output csv with relscore outputs CSV with header approach,score."""
    code, out, _ = _run_cli(["--output", "csv", "relscore", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert lines[0] == "approach,score"
    assert len(lines) == 5  # header + 4 approaches
    assert any("approach_c," in line for line in lines[1:])
    assert any("approach_a," in line for line in lines[1:])


def test_cli_csv_relcov_performance_approach_table() -> None:
    """CLI --output csv with relcov (table) outputs CSV with header row."""
    code, out, _ = _run_cli(["--output", "csv", "relcov", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert "approach" in lines[0]
    assert "approach_a" in lines[0] or "approach_b" in lines[0]
    assert len(lines) >= 4  # header + data rows


def test_cli_latex_relcov_performance_approach_table() -> None:
    """CLI --output latex with relcov (table) outputs LaTeX tabular."""
    code, out, _ = _run_cli(["--output", "latex", "relcov", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert any(line.startswith(r"\begin{tabular}") for line in lines)
    assert any("approach" in line for line in lines)
    assert lines[-1] == r"\end{tabular}"


def test_cli_latex_color_relcov_performance_approach_table() -> None:
    """CLI --output latex with --latex-enable-color outputs colored LaTeX tabular."""
    code, out, _ = _run_cli(
        [
            "--output",
            "latex",
            "--latex-enable-color",
            "relcov",
            str(SAMPLE_SHOWMAP_DIR),
        ]
    )
    assert code == 0
    lines = out.strip().splitlines()
    assert any(line.startswith(r"\begin{tabular}") for line in lines)
    assert any(r"\cellcolor" in line for line in lines)
    assert lines[-1] == r"\end{tabular}"


def test_cli_latex_default_no_rotate_headers() -> None:
    """CLI LaTeX output without --latex-rotate-headers emits unrotated headers."""
    code, out, _ = _run_cli(["--output", "latex", "relcov", str(SAMPLE_SHOWMAP_DIR)])
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
            str(SAMPLE_SHOWMAP_DIR),
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
            str(SAMPLE_SHOWMAP_DIR),
        ]
    )
    assert code == 0
    lines = out.strip().splitlines()
    assert any(line.startswith(r"\begin{tabular}") for line in lines)
    # Table should not contain any colored cells
    assert not any(r"\cellcolor" in line for line in lines)


def test_cli_digits_relscore() -> None:
    """CLI --digits controls decimal places in relscore output."""
    code, out, _ = _run_cli(["--digits", "4", "relscore", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    # Each score should have exactly 4 digits after the decimal point
    for line in lines:
        score = line.split(":", 1)[1].strip()
        assert "." in score
        assert len(score.split(".", 1)[1]) == 4


def test_cli_count() -> None:
    """CLI count prints absolute coverage counts sorted descending."""
    code, out, _ = _run_cli(["count", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    lines = [s.strip() for s in out.strip().splitlines()]
    assert len(lines) == 4
    # Sample: approach_a=3, approach_c=3, approach_b=2, seeds=1
    counts = {}
    for line in lines:
        name, count = line.split(":", 1)
        counts[name.strip()] = int(count.strip())
    assert counts == {
        "approach_a": 3,
        "approach_b": 2,
        "approach_c": 3,
        "seeds": 1,
    }
    # Sorted by count descending; ties broken by name ascending
    assert lines[0].startswith("approach_a:") or lines[0].startswith("approach_c:")
    assert lines[-1].startswith("seeds:")


def test_cli_csv_count() -> None:
    """CLI --output csv with count outputs CSV with header approach,coverage."""
    code, out, _ = _run_cli(["--output", "csv", "count", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert lines[0] == "approach,coverage"
    assert len(lines) == 5  # header + 4 approaches
    assert any(line.startswith("approach_a,3") for line in lines[1:])
    assert any(line.startswith("seeds,1") for line in lines[1:])


def test_cli_latex_count() -> None:
    """CLI --output latex with count outputs LaTeX tabular."""
    code, out, _ = _run_cli(["--output", "latex", "count", str(SAMPLE_SHOWMAP_DIR)])
    assert code == 0
    lines = out.strip().splitlines()
    assert any(line.startswith(r"\begin{tabular}") for line in lines)
    assert any("coverage" in line for line in lines)
    assert lines[-1] == r"\end{tabular}"
