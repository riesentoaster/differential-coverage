from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ReaderName = Literal["afl-showmap", "llvm-cov"]
InputFormat = Literal["auto", "afl-showmap", "llvm-cov"]


@dataclass(frozen=True)
class TrialReader:
    name: ReaderName
    read: Callable[[Path], set[str]]
    detect: Callable[[Path], bool]


_READERS: dict[str, TrialReader] = {}


def register_reader(reader: TrialReader) -> None:
    _READERS[reader.name] = reader


def get_reader(name: ReaderName) -> TrialReader:
    return _READERS[name]


def detect_reader(path: Path) -> ReaderName:
    for reader in _READERS.values():
        if reader.detect(path):
            return reader.name
    raise ValueError(f"Unrecognized trial file format: {path}")


def resolve_reader(files: list[Path], input_format: InputFormat) -> TrialReader:
    if not files:
        raise ValueError("Approach directory has no files")
    if input_format != "auto":
        return get_reader(input_format)

    detected = detect_reader(files[0])
    for file in files[1:]:
        if detect_reader(file) != detected:
            raise ValueError(
                f"Mixed trial formats in approach directory ({detected} vs {file})"
            )
    return get_reader(detected)


def read_trial(path: Path, reader: TrialReader) -> set[str]:
    return reader.read(path)
