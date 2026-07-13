"""Unit tests for trial readers and format detection."""

from pathlib import Path

import pytest

from differential_coverage.readers import afl_showmap, llvm_cov
from differential_coverage.readers.registry import detect_reader, resolve_reader

AFL_FIXTURE = Path(__file__).parent / "fixtures" / "afl_showmap" / "t1.txt"


def _llvm_export(calc_coverage_dir: Path) -> Path:
    return next((calc_coverage_dir / "approach_a").glob("*.json"))


def test_afl_showmap_detect_and_read() -> None:
    assert afl_showmap.detect(AFL_FIXTURE)
    assert not llvm_cov.detect(AFL_FIXTURE)
    assert afl_showmap.read(AFL_FIXTURE, granularity="edge") == {"1", "2"}


def test_llvm_cov_detect_and_read(calc_coverage_dir: Path) -> None:
    export = _llvm_export(calc_coverage_dir)
    assert llvm_cov.detect(export)
    assert not afl_showmap.detect(export)
    assert llvm_cov.read(export, granularity="branch")


def test_detect_reader(calc_coverage_dir: Path) -> None:
    export = _llvm_export(calc_coverage_dir)
    assert detect_reader(AFL_FIXTURE) == "afl-showmap"
    assert detect_reader(export) == "llvm-cov"


def test_resolve_reader_auto(calc_coverage_dir: Path) -> None:
    export = _llvm_export(calc_coverage_dir)
    reader = resolve_reader([AFL_FIXTURE], "auto")
    assert reader.name == "afl-showmap"
    reader = resolve_reader([export], "auto")
    assert reader.name == "llvm-cov"


def test_resolve_reader_forced(calc_coverage_dir: Path) -> None:
    export = _llvm_export(calc_coverage_dir)
    assert resolve_reader([export], "llvm-cov").name == "llvm-cov"
    assert resolve_reader([AFL_FIXTURE], "afl-showmap").name == "afl-showmap"


def test_afl_showmap_rejects_block_granularity() -> None:
    from differential_coverage.readers.registry import resolve_granularity

    with pytest.raises(ValueError, match="does not support --granularity block"):
        resolve_granularity("afl-showmap", "block")


def test_resolve_granularity_auto(calc_coverage_dir: Path) -> None:
    from differential_coverage.readers.registry import resolve_granularity

    assert resolve_granularity("llvm-cov", "auto") == "branch"
    assert resolve_granularity("afl-showmap", "auto") == "edge"
    assert resolve_granularity("llvm-cov", "block") == "block"
    with pytest.raises(ValueError, match="does not support --granularity edge"):
        resolve_granularity("llvm-cov", "edge")


def test_mixed_formats_in_approach_dir(tmp_path: Path, calc_coverage_dir: Path) -> None:
    export = _llvm_export(calc_coverage_dir)
    approach = tmp_path / "approach"
    approach.mkdir()
    (approach / "a.txt").write_text("1:1\n")
    (approach / "b.json").write_text(export.read_text())
    with pytest.raises(ValueError, match="Mixed trial formats"):
        resolve_reader(list(approach.iterdir()), "auto")
