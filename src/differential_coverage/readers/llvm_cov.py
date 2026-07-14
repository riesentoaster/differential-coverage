import json
from pathlib import Path
from typing import Any

from differential_coverage.readers.registry import (
    Granularity,
    TrialReader,
    register_reader,
)

# llvm-cov region Kind field (region[7]); see LLVM CoverageMapping.h RegionKind.
_CODE_REGION = 0
_LLVM_EXPORT_MARKER = b"llvm.coverage.json.export"


def _edge_id(scope: str, file_id: int, record: list[int]) -> str:
    return f"{scope}@fid{file_id}:{record[0]}:{record[1]}-{record[2]}:{record[3]}"


def _branch_edges(scope: str, branches: list[list[int]]) -> set[str]:
    edges: set[str] = set()
    for branch in branches:
        region_id = _edge_id(scope, branch[6], branch)
        if branch[4] > 0:
            edges.add(f"{region_id}:true")
        if branch[5] > 0:
            edges.add(f"{region_id}:false")
    return edges


def _block_edges(scope: str, regions: list[list[int]]) -> set[str]:
    return {
        _edge_id(scope, region[5], region)
        for region in regions
        if region[4] > 0 and region[7] == _CODE_REGION
    }


def _parse_export(export: dict[str, Any], *, granularity: Granularity) -> set[str]:
    edges: set[str] = set()
    # functions[] pairs branches/regions with filenames[] for FileID lookup and
    # includes macro-expanded code; files[]/expansions[] are filtered views.
    for function in export.get("functions", []):
        name = function.get("name", "<unknown>")
        scope = f"fn:{name}"
        if granularity == "branch":
            edges.update(_branch_edges(scope, function.get("branches", [])))
        else:
            edges.update(_block_edges(scope, function.get("regions", [])))
    return edges


def _export_has_branches(data: dict[str, Any]) -> bool:
    return any(
        function.get("branches")
        for export in data.get("data", [])
        for function in export.get("functions", [])
    )


def read(path: Path, *, granularity: Granularity) -> set[str]:
    if granularity == "edge":
        raise ValueError("llvm-cov does not support --granularity edge")
    data = json.loads(path.read_text())
    if granularity == "branch" and not _export_has_branches(data):
        raise ValueError(
            f"No branch data in {path}; use --granularity block or export "
            "with LLVM 12+ and -fcoverage-mapping"
        )
    edges: set[str] = set()
    for export in data.get("data", []):
        edges.update(_parse_export(export, granularity=granularity))
    if not edges:
        raise ValueError(f"No covered edges in {path}")
    return edges


def detect(path: Path) -> bool:
    content = path.read_bytes()
    return _LLVM_EXPORT_MARKER in content and b'"data"' in content


register_reader(TrialReader(name="llvm-cov", read=read, detect=detect))
