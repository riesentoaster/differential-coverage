"""Unit tests for llvm-cov export input."""

import io
import json
import sys
from pathlib import Path

import pytest

from differential_coverage.api import DifferentialCoverage
from differential_coverage.cli import main
from differential_coverage.fs import read_approach_dir, read_campaign_dir
from differential_coverage.readers import llvm_cov


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


def _calc_export(calc_coverage_dir: Path, *parts: str) -> Path:
    return calc_coverage_dir.joinpath(*parts)


def test_read_llvm_cov_file_uses_export_path(calc_coverage_dir: Path) -> None:
    export = _calc_export(calc_coverage_dir, "approach_a", "t1.json")
    source_path = json.loads(export.read_text())["data"][0]["files"][0]["filename"]
    edges = llvm_cov.read(export, granularity="branch")
    assert edges
    assert all(edge.startswith(f"{source_path}:") for edge in edges)


def test_read_llvm_cov_branch_requires_branch_data(
    llvm_exports: dict[str, Path],
) -> None:
    with pytest.raises(ValueError, match="No branch data"):
        llvm_cov.read(llvm_exports["summary_only"], granularity="branch")


def test_read_llvm_cov_block_reads_calc_export(calc_coverage_dir: Path) -> None:
    export = _calc_export(calc_coverage_dir, "approach_a", "t1.json")
    with pytest.warns(UserWarning, match="Kind "):
        edges = llvm_cov.read(export, granularity="block")
    assert edges
    assert not any(edge.endswith(":true") or edge.endswith(":false") for edge in edges)


def test_read_llvm_cov_expansion_branches(llvm_exports: dict[str, Path]) -> None:
    export = llvm_exports["macro"]
    data = json.loads(export.read_text())
    assert data["data"][0]["files"][0]["expansions"]
    edges = llvm_cov.read(export, granularity="branch")
    assert edges
    assert any(":true" in edge or ":false" in edge for edge in edges)


def test_read_llvm_cov_expansion_blocks(llvm_exports: dict[str, Path]) -> None:
    with pytest.warns(UserWarning, match="Kind [13]"):
        edges = llvm_cov.read(llvm_exports["macro"], granularity="block")
    assert edges


def test_block_edges_warns_on_invalid_file_id() -> None:
    with pytest.warns(UserWarning, match="FileID 0 out of range"):
        edges = llvm_cov._block_edges([], [[1, 1, 1, 5, 1, 0, 0, 0]], label="test")
    assert not edges


def test_block_edges_warns_on_empty_filename() -> None:
    with pytest.warns(UserWarning, match="empty filename"):
        edges = llvm_cov._block_edges([""], [[1, 1, 1, 5, 1, 0, 0, 0]], label="test")
    assert not edges


def test_read_approach_dir_auto_detect(calc_coverage_dir: Path) -> None:
    trials = read_approach_dir(calc_coverage_dir / "approach_a")
    assert trials
    assert all(edges for edges in trials.values())


def test_read_campaign_dir(calc_coverage_dir: Path) -> None:
    campaign = read_campaign_dir(calc_coverage_dir)
    assert {"seeds", "approach_a", "approach_b", "approach_c"} <= set(campaign.keys())


def test_read_campaign_dir_skips_empty_approach(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    approach = tmp_path / "has_data"
    approach.mkdir()
    (approach / "t1.txt").write_text("1:1\n")
    with pytest.warns(UserWarning, match="skipping approach"):
        campaign = read_campaign_dir(tmp_path)
    assert set(campaign.keys()) == {"has_data"}


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
