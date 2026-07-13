import warnings
from pathlib import Path

from differential_coverage.readers import (
    GranularityArg,
    InputFormat,
    read_trial,
    resolve_reader,
)


def read_approach_dir(
    path: Path,
    *,
    input_format: InputFormat = "auto",
    granularity: GranularityArg = "auto",
) -> dict[str, set[str]]:
    """Read all trial files in a directory; return dict of trial id to edge sets."""
    files = [file for file in path.iterdir() if file.is_file()]
    for file in path.iterdir():
        if not file.is_file():
            raise ValueError(f"Invalid file: {file}")

    reader = resolve_reader(files, input_format)
    return {
        file.stem: read_trial(file, reader, granularity=granularity) for file in files
    }


def read_campaign_dir(
    path: Path,
    *,
    input_format: InputFormat = "auto",
    granularity: GranularityArg = "auto",
) -> dict[str, dict[str, set[str]]]:
    """Read all approach directories in a campaign directory."""
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    campaigns: dict[str, dict[str, set[str]]] = {}
    campaign_reader: str | None = None
    for approach_dir in path.iterdir():
        if approach_dir.is_dir():
            files = [file for file in approach_dir.iterdir() if file.is_file()]
            if not files:
                warnings.warn(f"No coverage data in {approach_dir}; skipping approach")
                continue
            reader = resolve_reader(files, input_format)
            if campaign_reader is None:
                campaign_reader = reader.name
            elif reader.name != campaign_reader:
                raise ValueError(
                    "Mixed input formats across campaign; use one format for all approaches"
                )
            campaigns[approach_dir.name] = {
                file.stem: read_trial(file, reader, granularity=granularity)
                for file in files
            }
        else:
            raise ValueError(f"Invalid file: {approach_dir}")
    return campaigns
