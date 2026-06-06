from pathlib import Path

from differential_coverage.readers.registry import TrialReader, register_reader


def read(path: Path) -> set[str]:
    edges: set[str] = set()
    for i, line in enumerate(path.read_text().strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        parts = line.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid line {path}:{i}: {line}")
        edge_id, count = parts
        if int(count) > 0:
            edges.add(edge_id)
    if not edges:
        raise ValueError(f"No covered edges in {path}")
    return edges


def detect(path: Path) -> bool:
    found = False
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(":")
        if len(parts) != 2:
            return False
        try:
            int(parts[1])
        except ValueError:
            return False
        found = True
    return found


register_reader(TrialReader(name="afl-showmap", read=read, detect=detect))
