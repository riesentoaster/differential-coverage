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


def _covered_code_region_keys(export: Path) -> list[str]:
    """Covered CodeRegion location keys (may include duplicates)."""
    data = json.loads(export.read_text())
    keys: list[str] = []
    for item in data.get("data", []):
        for function in item.get("functions", []):
            filenames = function["filenames"]
            for region in function.get("regions", []):
                # CountedRegion: exec=4, file_id=5, kind=7; CodeRegion kind=0
                if region[4] <= 0 or region[7] != 0:
                    continue
                file_id = region[5]
                keys.append(
                    f"fn:{function['name']}@{filenames[file_id]}:"
                    f"{region[0]}:{region[1]}-{region[2]}:{region[3]}"
                )
    return keys


def test_read_cov_matches_llvm_cov_summary(
    calc_build_dir: Path, calc_coverage_dir: Path
) -> None:
    summaries = calc_build_dir / "build" / "llvm_summaries"
    for export in sorted(calc_coverage_dir.rglob("*.json")):
        rel = export.relative_to(calc_coverage_dir)
        summary_file = summaries / rel.parent / f"{export.stem}.json"
        assert summary_file.is_file(), f"missing llvm-cov summary for {export}"
        totals = json.loads(summary_file.read_text())["data"][0]["totals"]
        branch_edges = llvm_cov.read(export, granularity="branch")
        block_edges = llvm_cov.read(export, granularity="block")
        assert len(branch_edges) == totals["branches"]["covered"], (
            f"{rel} branch: reader found {len(branch_edges)}, "
            f"llvm-cov reported {totals['branches']['covered']}"
        )
        # Summary counts CodeRegion hits with multiplicity; the reader dedupes
        # by source location (same as differential-coverage edge identity).
        region_keys = _covered_code_region_keys(export)
        assert len(region_keys) == totals["regions"]["covered"], (
            f"{rel} regions: export has {len(region_keys)} covered CodeRegions, "
            f"llvm-cov reported {totals['regions']['covered']}"
        )
        assert block_edges == set(region_keys), (
            f"{rel} block: reader set does not match unique covered CodeRegions"
        )


def test_read_llvm_cov_branch_uses_function_scope(calc_coverage_dir: Path) -> None:
    export = _calc_export(calc_coverage_dir, "approach_a", "t1.json")
    edges = llvm_cov.read(export, granularity="branch")
    assert edges
    assert all(edge.startswith("fn:") and "@" in edge for edge in edges)
    assert not any("@fid" in edge for edge in edges)


def test_read_llvm_cov_branch_requires_branch_data(
    llvm_exports: dict[str, Path],
) -> None:
    with pytest.raises(ValueError, match="No covered edges"):
        llvm_cov.read(llvm_exports["summary_only"], granularity="branch")


def test_read_llvm_cov_block_reads_calc_export(calc_coverage_dir: Path) -> None:
    export = _calc_export(calc_coverage_dir, "approach_a", "t1.json")
    edges = llvm_cov.read(export, granularity="block")
    assert edges
    assert not any(edge.endswith(":true") or edge.endswith(":false") for edge in edges)


def test_read_llvm_cov_expansion_branches(llvm_exports: dict[str, Path]) -> None:
    export = llvm_exports["macro"]
    data = json.loads(export.read_text())
    functions = data["data"][0].get("functions", [])
    if not any(function.get("branches") for function in functions):
        pytest.skip("macro-expansion branch data not present in llvm-cov export")
    edges = llvm_cov.read(export, granularity="branch")
    assert edges
    assert all(edge.startswith("fn:main@") for edge in edges)
    assert any(":true" in edge or ":false" in edge for edge in edges)


def test_read_llvm_cov_expansion_blocks(llvm_exports: dict[str, Path]) -> None:
    edges = llvm_cov.read(llvm_exports["macro"], granularity="block")
    assert len(edges) == 6
    assert all(edge.startswith("fn:main@") for edge in edges)


def _write_export(path: Path, functions: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "type": "llvm.coverage.json.export",
                "data": [{"functions": functions}],
            }
        )
    )


def test_block_edges_uses_source_path(tmp_path: Path) -> None:
    export = tmp_path / "t.json"
    _write_export(
        export,
        [
            {
                "name": "main",
                "filenames": [f"/src/file{i}.c" for i in range(25)],
                "regions": [[1, 1, 1, 5, 1, 24, 0, 0]],
            }
        ],
    )
    edges = llvm_cov.read(export, granularity="block")
    assert edges == {"fn:main@/src/file24.c:1:1-1:5"}


def test_branch_edges_uses_source_path(tmp_path: Path) -> None:
    export = tmp_path / "t.json"
    _write_export(
        export,
        [
            {
                "name": "main",
                "filenames": ["/src/main.c", "/src/other.c"],
                "branches": [[5, 13, 5, 17, 0, 1, 1, 0, 4]],
            }
        ],
    )
    edges = llvm_cov.read(export, granularity="branch")
    assert edges == {"fn:main@/src/other.c:5:13-5:17:false"}


def test_read_raises_on_missing_filenames(tmp_path: Path) -> None:
    export = tmp_path / "t.json"
    _write_export(export, [{"name": "main", "regions": [[1, 1, 1, 5, 1, 0, 0, 0]]}])
    with pytest.raises(KeyError):
        llvm_cov.read(export, granularity="block")


def test_read_raises_on_invalid_file_id(tmp_path: Path) -> None:
    export = tmp_path / "t.json"
    _write_export(
        export,
        [
            {
                "name": "main",
                "filenames": ["/a.c", "/b.c"],
                "regions": [[1, 1, 1, 5, 1, 3, 0, 0]],
            }
        ],
    )
    with pytest.raises(IndexError):
        llvm_cov.read(export, granularity="block")


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
