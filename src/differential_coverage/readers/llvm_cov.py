import json
import warnings
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


def _region_id(filename: str, region: list[int]) -> str:
    return f"{filename}:{region[0]}:{region[1]}-{region[2]}:{region[3]}"


def _resolve_filename(
    filenames: list[str], file_id: int, fallback: str, *, label: str
) -> str:
    if file_id < len(filenames):
        filename = filenames[file_id]
        if not filename:
            warnings.warn(
                f"llvm-cov export {label}: FileID {file_id} maps to empty filename",
                stacklevel=4,
            )
        return filename
    warnings.warn(
        f"llvm-cov export {label}: FileID {file_id} out of range "
        f"(filenames has {len(filenames)} entries); using fallback {fallback!r}",
        stacklevel=4,
    )
    return fallback


def _file_branch_filenames(file: dict[str, Any]) -> list[str]:
    """Filename table for files[].branches FileID indices.

    Without macro expansions, branches only reference the file itself (FileID 0).
    With expansions, LLVM indexes into expansions[0].filenames (same table used
    for expansion branches).
    """
    filename = file["filename"]
    expansions = file.get("expansions", [])
    if not expansions:
        return [filename]
    return list(expansions[0].get("filenames", [filename]))


def _branch_edges(
    filenames: list[str], fallback: str, branches: list[list[int]], *, label: str
) -> set[str]:
    edges: set[str] = set()
    for branch in branches:
        filename = _resolve_filename(filenames, branch[6], fallback, label=label)
        if not filename:
            continue
        region_id = _region_id(filename, branch)
        if branch[4] > 0:
            edges.add(f"{region_id}:true")
        if branch[5] > 0:
            edges.add(f"{region_id}:false")
    return edges


def _block_edges(
    filenames: list[str], regions: list[list[int]], *, label: str
) -> set[str]:
    """Collect executed CodeRegions as block-granularity edge IDs.

    Region tuples are
    [LineStart, ColStart, LineEnd, ColEnd, ExecutionCount, FileID, ExpandedFileID, Kind].

    ExecutionCount (index 4): only regions run at least once become edges. Uncovered
    regions stay in the export with count 0; we skip them because differential
    coverage is hit/miss, not how often something ran (same rule as branch counts).

    Kind (index 7): block mode uses CodeRegion only. Other kinds are LLVM metadata
    (gaps for rendering, skipped/dead code, expansion/branch records) or belong in
    branch mode via files[].branches / expansions[].branches.
    """
    edges: set[str] = set()
    skipped_by_kind: dict[int, int] = {}
    for region in regions:
        if region[4] <= 0:
            continue
        if region[7] != _CODE_REGION:
            skipped_by_kind[region[7]] = skipped_by_kind.get(region[7], 0) + 1
            continue
        filename = _resolve_filename(filenames, region[5], "", label=label)
        if not filename:
            continue
        edges.add(_region_id(filename, region))
    for kind, count in sorted(skipped_by_kind.items()):
        warnings.warn(
            f"llvm-cov export {label}: skipped {count} executed region(s) with "
            f"Kind {kind} (block mode uses CodeRegion only, Kind {_CODE_REGION})",
            stacklevel=4,
        )
    return edges


def _parse_branch_export(export: dict[str, Any]) -> set[str]:
    edges: set[str] = set()
    for file in export.get("files", []):
        filename = file["filename"]
        file_filenames = _file_branch_filenames(file)
        edges.update(
            _branch_edges(
                file_filenames,
                filename,
                file.get("branches", []),
                label="file branches",
            )
        )
        for expansion in file.get("expansions", []):
            filenames = expansion.get("filenames", [])
            fallback = filenames[0] if filenames else filename
            edges.update(
                _branch_edges(
                    filenames,
                    fallback,
                    expansion.get("branches", []),
                    label="expansion branches",
                )
            )
    return edges


def _parse_block_export(export: dict[str, Any]) -> set[str]:
    edges: set[str] = set()
    for function in export.get("functions", []):
        name = function.get("name", "<unknown>")
        edges.update(
            _block_edges(
                function.get("filenames", []),
                function.get("regions", []),
                label=f"function {name!r}",
            )
        )
    for file in export.get("files", []):
        for expansion in file.get("expansions", []):
            edges.update(
                _block_edges(
                    expansion.get("filenames", []),
                    expansion.get("target_regions", []),
                    label="expansion target_regions",
                )
            )
    return edges


def _export_has_branches(data: dict[str, Any]) -> bool:
    return any(
        "branches" in file
        for export in data.get("data", [])
        for file in export.get("files", [])
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
    parser = _parse_branch_export if granularity == "branch" else _parse_block_export
    edges: set[str] = set()
    for export in data.get("data", []):
        edges.update(parser(export))
    if not edges:
        raise ValueError(f"No covered edges in {path}")
    return edges


def detect(path: Path) -> bool:
    content = path.read_bytes()
    return _LLVM_EXPORT_MARKER in content and b'"data"' in content


register_reader(TrialReader(name="llvm-cov", read=read, detect=detect))
