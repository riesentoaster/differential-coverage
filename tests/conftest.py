"""Shared pytest fixtures."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CALC_DIR = Path(__file__).parent / "calc"
LLVM = ("clang", "llvm-profdata", "llvm-cov")
LLVM_BIN_DIRS = (
    Path("/opt/homebrew/opt/llvm/bin"),
    Path("/usr/local/opt/llvm/bin"),
)


def _env_with_llvm() -> dict[str, str]:
    env = {**os.environ}
    for llvm_bin in LLVM_BIN_DIRS:
        if llvm_bin.is_dir():
            env["PATH"] = f"{llvm_bin}{os.pathsep}{env.get('PATH', '')}"
            break
    return env


def _llvm_available() -> bool:
    path = _env_with_llvm()["PATH"]
    return all(shutil.which(tool, path=path) is not None for tool in LLVM)


@pytest.fixture(scope="session")
def calc_coverage_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if sys.platform == "win32" or not _llvm_available():
        pytest.skip("requires clang/llvm on a Unix-like OS")

    root = tmp_path_factory.mktemp("calc")
    coverage = root / "coverage"
    subprocess.run(
        ["bash", str(CALC_DIR / "generate.sh")],
        check=True,
        env={
            **_env_with_llvm(),
            "BUILD": str(root / "build"),
            "COVERAGE": str(coverage),
            "EXPORTS": str(root / "exports"),
        },
    )
    return coverage


@pytest.fixture(scope="session")
def llvm_exports(calc_coverage_dir: Path) -> dict[str, Path]:
    root = calc_coverage_dir.parent
    exports = root / "exports"
    return {
        "macro": exports / "macro.json",
        "summary_only": exports / "summary_only.json",
    }
