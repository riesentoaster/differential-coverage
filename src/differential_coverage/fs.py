import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from differential_coverage.readers import (
    GranularityArg,
    InputFormat,
    read_trial,
    resolve_reader,
)
from differential_coverage.readers.registry import TrialReader


def _read_all(
    trials: list[tuple[Path, TrialReader]],
    *,
    granularity: GranularityArg,
    max_workers: int | None = None,
) -> list[set[str]]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(
            executor.map(
                lambda trial: read_trial(trial[0], trial[1], granularity=granularity),
                trials,
            )
        )


def read_approach_dir(
    path: Path,
    *,
    input_format: InputFormat = "auto",
    granularity: GranularityArg = "auto",
    max_workers: int | None = None,
) -> dict[str, set[str]]:
    """Read all trial files in a directory; return dict of trial id to edge sets."""
    files = [file for file in path.iterdir() if file.is_file()]
    for file in path.iterdir():
        if not file.is_file():
            raise ValueError(f"Invalid file: {file}")

    reader = resolve_reader(files, input_format)
    trials = [(file, reader) for file in files]
    return {
        file.stem: edges
        for file, edges in zip(
            files,
            _read_all(trials, granularity=granularity, max_workers=max_workers),
            strict=True,
        )
    }


def read_campaign_dir(
    path: Path,
    *,
    input_format: InputFormat = "auto",
    granularity: GranularityArg = "auto",
    max_workers: int | None = None,
) -> dict[str, dict[str, set[str]]]:
    """Read all approach directories in a campaign directory."""
    if not path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    trials: list[tuple[Path, TrialReader]] = []
    meta: list[tuple[str, Path]] = []
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
            for file in files:
                meta.append((approach_dir.name, file))
                trials.append((file, reader))
        else:
            raise ValueError(f"Invalid file: {approach_dir}")

    campaigns: dict[str, dict[str, set[str]]] = {}
    for (approach, file), edges in zip(
        meta,
        _read_all(trials, granularity=granularity, max_workers=max_workers),
        strict=True,
    ):
        campaigns.setdefault(approach, {})[file.stem] = edges
    return campaigns
