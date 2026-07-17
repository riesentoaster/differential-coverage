from pathlib import Path

from differential_coverage.readers.registry import (
    Granularity,
    TrialReader,
    register_reader,
)


def read(path: Path, *, granularity: Granularity) -> set[str]:
    if granularity != "edge":
        raise ValueError("libfuzzer-merge only supports --granularity edge")
    edges: set[str] = set()
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[0] != "COV":
            continue
        edges.update(parts[2:])
    if not edges:
        raise ValueError(f"No covered edges in {path}")
    return edges


def detect(path: Path) -> bool:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    try:
        num_files = int(lines[0])
        num_first = int(lines[1])
    except ValueError:
        return False
    if num_files <= 0 or num_first > num_files:
        return False
    has_marker = any(
        line.startswith("STARTED ") or line.startswith("COV ") for line in lines
    )
    return has_marker


register_reader(TrialReader(name="libfuzzer-merge", read=read, detect=detect))
