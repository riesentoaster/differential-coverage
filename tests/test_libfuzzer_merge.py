"""Unit tests for libFuzzer merge control file input."""

import io
import re
import sys
from pathlib import Path

import pytest

from differential_coverage.api import DifferentialCoverage
from differential_coverage.cli import main
from differential_coverage.fs import read_approach_dir, read_campaign_dir
from differential_coverage.readers import libfuzzer_merge
from differential_coverage.readers.registry import detect_reader, resolve_granularity

_DONE_COV_RE = re.compile(r"^\#\d+\s+DONE\s+cov:\s+(\d+)", re.MULTILINE)


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


def _calc_merge(calc_merge_dir: Path, *parts: str) -> Path:
    return calc_merge_dir.joinpath(*parts)


def _parse_libfuzzer_done_cov(log_text: str) -> int:
    matches = _DONE_COV_RE.findall(log_text)
    if not matches:
        raise ValueError("no DONE cov line in libFuzzer merge output")
    return int(matches[-1])


def test_read_cov_matches_libfuzzer_merge_output(
    calc_build_dir: Path, calc_merge_dir: Path
) -> None:
    merge_logs = calc_build_dir / "build" / "merge_logs"
    for merge_file in sorted(calc_merge_dir.rglob("*.merge")):
        rel = merge_file.relative_to(calc_merge_dir)
        log_file = merge_logs / rel.parent / f"{merge_file.stem}.log"
        assert log_file.is_file(), f"missing libFuzzer log for {merge_file}"
        expected_cov = _parse_libfuzzer_done_cov(log_file.read_text())
        edges = libfuzzer_merge.read(merge_file, granularity="edge")
        assert len(edges) == expected_cov, (
            f"{rel}: reader found {len(edges)} edges, "
            f"libFuzzer reported cov: {expected_cov}"
        )


def test_read_detect_and_read(calc_merge_dir: Path) -> None:
    merge_file = _calc_merge(calc_merge_dir, "approach_a", "t1.merge")
    assert libfuzzer_merge.detect(merge_file)
    edges = libfuzzer_merge.read(merge_file, granularity="edge")
    assert edges
    assert all(edge.isdigit() for edge in edges)


def test_detect_reader(calc_merge_dir: Path) -> None:
    merge_file = _calc_merge(calc_merge_dir, "approach_a", "t1.merge")
    assert detect_reader(merge_file) == "libfuzzer-merge"


def test_granularity_rejects_non_edge(calc_merge_dir: Path) -> None:
    merge_file = _calc_merge(calc_merge_dir, "approach_a", "t1.merge")
    with pytest.raises(ValueError, match="does not support --granularity branch"):
        resolve_granularity("libfuzzer-merge", "branch")
    with pytest.raises(ValueError, match="only supports --granularity edge"):
        libfuzzer_merge.read(merge_file, granularity="block")


def test_read_raises_without_cov_lines(tmp_path: Path) -> None:
    merge_file = tmp_path / "empty.merge"
    merge_file.write_text("1\n1\n/input\n")
    with pytest.raises(ValueError, match="No covered edges"):
        libfuzzer_merge.read(merge_file, granularity="edge")


def test_read_approach_dir(calc_merge_dir: Path) -> None:
    trials = read_approach_dir(
        calc_merge_dir / "approach_a",
        input_format="libfuzzer-merge",
    )
    assert trials
    assert all(edges for edges in trials.values())


def test_read_campaign_dir(calc_merge_dir: Path) -> None:
    campaign = read_campaign_dir(
        calc_merge_dir,
        input_format="libfuzzer-merge",
    )
    assert {"seeds", "approach_a", "approach_b", "approach_c"} <= set(campaign.keys())


def test_relcov_from_merge_campaign(calc_merge_dir: Path) -> None:
    dc = DifferentialCoverage.from_campaign_dir(
        calc_merge_dir,
        input_format="libfuzzer-merge",
    )
    approach_c = dc.approaches["approach_c"]
    for approach in ("approach_a", "approach_b", "seeds"):
        assert approach_c.relcov(dc.approaches[approach]) == 1.0


def test_cli_relscore(calc_merge_dir: Path) -> None:
    code, out = _run_cli(
        ["--input-format", "libfuzzer-merge", "relscore", str(calc_merge_dir)]
    )
    assert code == 0
    lines = [line.strip() for line in out.strip().splitlines()]
    assert any(line.startswith("approach_c:") for line in lines)
    assert any(line.startswith("approach_a:") for line in lines)
