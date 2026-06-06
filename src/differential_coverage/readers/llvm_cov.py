import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from differential_coverage.readers.registry import TrialReader, register_reader

_CODE_REGION = 0
_GAP_REGION = 3
_LLVM_EXPORT_MARKER = b"llvm.coverage.json.export"


def normalize_source_path(path: str) -> str:
    """Use basename so edge IDs are portable across build machines."""
    return Path(path).name


def _region_id(filename: str, region: list[int]) -> str:
    source = normalize_source_path(filename)
    return f"{source}:{region[0]}:{region[1]}-{region[2]}:{region[3]}"


def _parse_branch_export(export: dict[str, Any]) -> set[str]:
    edges: set[str] = set()
    for file in export.get("files", []):
        filename = file["filename"]
        for branch in file.get("branches", []):
            region_id = _region_id(filename, branch)
            if branch[4] > 0:
                edges.add(f"{region_id}:true")
            if branch[5] > 0:
                edges.add(f"{region_id}:false")
    return edges


def _parse_region_export(
    export: dict[str, Any], *, code_regions_only: bool
) -> set[str]:
    edges: set[str] = set()
    for function in export.get("functions", []):
        filenames = function.get("filenames", [])
        for region in function.get("regions", []):
            if region[4] <= 0:
                continue
            kind = region[7]
            if code_regions_only:
                if kind != _CODE_REGION:
                    continue
            elif kind == _GAP_REGION:
                continue
            file_id = region[5]
            if file_id >= len(filenames):
                continue
            edges.add(_region_id(filenames[file_id], region))
    return edges


def _detect_granularity(data: dict[str, Any]) -> Literal["branch", "block", "region"]:
    for export in data.get("data", []):
        if any(file.get("branches") for file in export.get("files", [])):
            return "branch"
    for export in data.get("data", []):
        for function in export.get("functions", []):
            if any(
                region[4] > 0 and region[7] == _CODE_REGION
                for region in function.get("regions", [])
            ):
                return "block"
    return "region"


_PARSERS: dict[
    Literal["branch", "block", "region"],
    Callable[[dict[str, Any]], set[str]],
] = {
    "branch": _parse_branch_export,
    "block": lambda export: _parse_region_export(export, code_regions_only=True),
    "region": lambda export: _parse_region_export(export, code_regions_only=False),
}


def read(path: Path) -> set[str]:
    data = json.loads(path.read_text())
    parser = _PARSERS[_detect_granularity(data)]
    edges: set[str] = set()
    for export in data.get("data", []):
        edges.update(parser(export))
    if not edges:
        raise ValueError(f"No covered edges in {path}")
    return edges


def detect(path: Path) -> bool:
    prefix = path.read_bytes()[:8192]
    return _LLVM_EXPORT_MARKER in prefix and b'"data"' in prefix


register_reader(TrialReader(name="llvm-cov", read=read, detect=detect))
