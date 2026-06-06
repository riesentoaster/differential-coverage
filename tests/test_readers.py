"""Unit tests for trial readers and format detection."""

from pathlib import Path

import pytest

from differential_coverage.readers import afl_showmap, llvm_cov
from differential_coverage.readers.registry import detect_reader, resolve_reader

AFL_FIXTURE = Path(__file__).parent / "fixtures" / "afl_showmap" / "t1.txt"
LLVM_FIXTURE = Path(__file__).parent / "fixtures" / "llvm_cov" / "t1.json"


def test_afl_showmap_detect_and_read() -> None:
    assert afl_showmap.detect(AFL_FIXTURE)
    assert not llvm_cov.detect(AFL_FIXTURE)
    assert afl_showmap.read(AFL_FIXTURE) == {"1", "2"}


def test_llvm_cov_detect_and_read() -> None:
    assert llvm_cov.detect(LLVM_FIXTURE)
    assert not afl_showmap.detect(LLVM_FIXTURE)
    assert llvm_cov.read(LLVM_FIXTURE) == {"foo.c:1:1-1:5:true"}


def test_detect_reader() -> None:
    assert detect_reader(AFL_FIXTURE) == "afl-showmap"
    assert detect_reader(LLVM_FIXTURE) == "llvm-cov"


def test_resolve_reader_auto() -> None:
    reader = resolve_reader([AFL_FIXTURE], "auto")
    assert reader.name == "afl-showmap"
    reader = resolve_reader([LLVM_FIXTURE], "auto")
    assert reader.name == "llvm-cov"


def test_resolve_reader_forced() -> None:
    assert resolve_reader([LLVM_FIXTURE], "llvm-cov").name == "llvm-cov"
    assert resolve_reader([AFL_FIXTURE], "afl-showmap").name == "afl-showmap"


def test_mixed_formats_in_approach_dir(tmp_path: Path) -> None:
    approach = tmp_path / "approach"
    approach.mkdir()
    (approach / "a.txt").write_text("1:1\n")
    (approach / "b.json").write_text(LLVM_FIXTURE.read_text())
    with pytest.raises(ValueError, match="Mixed trial formats"):
        resolve_reader(list(approach.iterdir()), "auto")
