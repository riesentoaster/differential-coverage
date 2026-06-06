"""Unit tests for llvm-cov export input."""

import io
import sys
from pathlib import Path

from differential_coverage.api import DifferentialCoverage
from differential_coverage.cli import main
from differential_coverage.fs import read_approach_dir, read_campaign_dir
from differential_coverage.readers import llvm_cov

LLVM_FIXTURE = Path(__file__).parent / "fixtures" / "llvm_cov" / "t1.json"


def _run_cli(argv: list[str]) -> tuple[int | str, str]:
    out = io.StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = out
        code = main(argv)
    except SystemExit as exc:
        code = int(exc.code) if exc.code is not None else 1
    finally:
        sys.stdout = old_stdout
    return code, out.getvalue()


def test_read_llvm_cov_file_uses_basename() -> None:
    edges = llvm_cov.read(LLVM_FIXTURE)
    assert edges == {"foo.c:1:1-1:5:true"}
    assert all(not edge.startswith("/") for edge in edges)


def test_read_llvm_cov_file(calc_coverage_dir: Path) -> None:
    export = next((calc_coverage_dir / "approach_a").glob("*.json"))
    edges = llvm_cov.read(export)
    assert edges
    assert all(":" in edge for edge in edges)
    assert all(Path(edge.split(":")[0]).name == edge.split(":")[0] for edge in edges)


def test_read_approach_dir_auto_detect(calc_coverage_dir: Path) -> None:
    trials = read_approach_dir(calc_coverage_dir / "approach_a")
    assert trials
    assert all(edges for edges in trials.values())


def test_read_campaign_dir(calc_coverage_dir: Path) -> None:
    campaign = read_campaign_dir(calc_coverage_dir)
    assert {"seeds", "approach_a", "approach_b", "approach_c"} <= set(campaign.keys())


def test_relcov_from_llvm_cov_campaign(calc_coverage_dir: Path) -> None:
    dc = DifferentialCoverage.from_campaign_dir(calc_coverage_dir)
    approach_c = dc.approaches["approach_c"]
    for approach in ("approach_a", "approach_b", "seeds"):
        assert approach_c.relcov(dc.approaches[approach]) == 1.0


def test_cli_relscore(calc_coverage_dir: Path) -> None:
    code, out = _run_cli(["relscore", str(calc_coverage_dir)])
    assert code == 0
    lines = [line.strip() for line in out.strip().splitlines()]
    assert any(line.startswith("approach_c:") for line in lines)
    assert any(line.startswith("approach_a:") for line in lines)
