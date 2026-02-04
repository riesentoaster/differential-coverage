from pathlib import Path

from differential_coverage.types import CampaignMap, CoverageMap, FuzzerMap


def read_afl_showmap_file(file: Path) -> CoverageMap:
    """Parse one afl-showmap file; return dict of edge ids to counts."""
    edges: CoverageMap = {}
    for i, line in enumerate(file.read_text().strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        split = line.split(":")
        if len(split) != 2:
            raise ValueError(f"Invalid line {file}:{i}: {line}")
        id, count = split
        edges[int(id)] = int(count)
    return edges


def read_fuzzer_dir(path: Path) -> FuzzerMap:
    """Read all afl-showmap files in a directory; return dict of trial id to dict of edge ids to counts."""
    trials: FuzzerMap = {}
    for file in path.iterdir():
        if file.is_file():
            trials[file.name] = read_afl_showmap_file(file)
        else:
            raise ValueError(f"Invalid file: {file}")
    return trials


def read_campaign_dir(path: Path) -> CampaignMap:
    """Read all fuzzer directories in a campaign directory; return dict of fuzzer name to dict of trial id to dict of edge ids to counts."""
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    campaigns: CampaignMap = {}
    for fuzzer_dir in path.iterdir():
        if fuzzer_dir.is_dir():
            campaigns[fuzzer_dir.name] = read_fuzzer_dir(fuzzer_dir)
        else:
            raise ValueError(f"Invalid file: {fuzzer_dir}")
    return campaigns
