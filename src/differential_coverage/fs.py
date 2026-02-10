from pathlib import Path


def read_afl_showmap_file(file: Path) -> dict[str, int]:
    """Parse one afl-showmap file; return dict of edge ids to counts."""
    edges: dict[str, int] = {}
    for i, line in enumerate(file.read_text().strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        split = line.split(":")
        if len(split) != 2:
            raise ValueError(f"Invalid line {file}:{i}: {line}")
        id, count = split
        edges[id] = int(count)
    return edges


def read_approach_dir(path: Path) -> dict[str, set[str]]:
    """Read all afl-showmap files in a directory; return dict of trial id to dict of edge ids to counts."""
    trials: dict[str, set[str]] = {}
    for file in path.iterdir():
        if file.is_file():
            map = read_afl_showmap_file(file)
            trials[file.stem] = {e for e in map if map.get(e, 0) > 0}
        else:
            raise ValueError(f"Invalid file: {file}")
    return trials


def read_campaign_dir(
    path: Path,
) -> dict[str, dict[str, set[str]]]:
    """Read all approach directories in a campaign directory; return dict of approach name to dict of trial id to dict of edge ids to counts."""
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    campaigns: dict[str, dict[str, set[str]]] = {}
    for approach_dir in path.iterdir():
        if approach_dir.is_dir():
            campaigns[approach_dir.name] = read_approach_dir(approach_dir)
        else:
            raise ValueError(f"Invalid file: {approach_dir}")
    return campaigns
