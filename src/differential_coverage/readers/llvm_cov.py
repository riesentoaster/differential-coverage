import json
from pathlib import Path

from differential_coverage.readers.registry import (
    Granularity,
    TrialReader,
    register_reader,
)

# llvm-cov CountedRegion JSON arrays; see renderRegion/renderBranch in
# llvm/tools/llvm-cov/CoverageExporterJson.cpp.
_LINE_START = 0
_COLUMN_START = 1
_LINE_END = 2
_COLUMN_END = 3
_EXEC_COUNT = 4
_REGION_FILE_ID = 5
_REGION_KIND = 7
_BRANCH_FALSE_COUNT = 5
_BRANCH_FILE_ID = 6

# RegionKind::CodeRegion in include/llvm/ProfileData/CoverageMapping.h
_CODE_REGION = 0
_LLVM_EXPORT_MARKER = b"llvm.coverage.json.export"


def _edge_id(scope: str, filenames: list[str], file_id: int, record: list[int]) -> str:
    return (
        f"{scope}@{filenames[file_id]}:"
        f"{record[_LINE_START]}:{record[_COLUMN_START]}-"
        f"{record[_LINE_END]}:{record[_COLUMN_END]}"
    )


def read(path: Path, *, granularity: Granularity) -> set[str]:
    if granularity == "edge":
        raise ValueError("llvm-cov does not support --granularity edge")
    data = json.loads(path.read_text())
    edges: set[str] = set()
    for export in data.get("data", []):
        for function in export.get("functions", []):
            scope = f"fn:{function['name']}"
            filenames = function["filenames"]

            if granularity == "branch":
                for branch in function.get("branches", []):
                    base = _edge_id(scope, filenames, branch[_BRANCH_FILE_ID], branch)
                    if branch[_EXEC_COUNT] > 0:
                        edges.add(f"{base}:true")
                    if branch[_BRANCH_FALSE_COUNT] > 0:
                        edges.add(f"{base}:false")
            else:
                for region in function.get("regions", []):
                    if region[_EXEC_COUNT] > 0 and region[_REGION_KIND] == _CODE_REGION:
                        edges.add(
                            _edge_id(scope, filenames, region[_REGION_FILE_ID], region)
                        )
    if not edges:
        raise ValueError(f"No covered edges in {path}")
    return edges


def detect(path: Path) -> bool:
    content = path.read_bytes()
    return _LLVM_EXPORT_MARKER in content and b'"data"' in content


register_reader(TrialReader(name="llvm-cov", read=read, detect=detect))
