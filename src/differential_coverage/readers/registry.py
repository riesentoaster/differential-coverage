from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

ReaderName = Literal["afl-showmap", "llvm-cov"]
InputFormat = Literal["auto", "afl-showmap", "llvm-cov"]
Granularity = Literal["branch", "block", "edge"]
GranularityArg = Literal["auto", "branch", "block", "edge"]

_SUPPORTED: dict[ReaderName, frozenset[Granularity]] = {
    "afl-showmap": frozenset({"edge"}),
    "llvm-cov": frozenset({"branch", "block"}),
}
_DEFAULT: dict[ReaderName, Granularity] = {
    "afl-showmap": "edge",
    "llvm-cov": "branch",
}


class ReadTrial(Protocol):
    def __call__(self, path: Path, *, granularity: Granularity) -> set[str]: ...


@dataclass(frozen=True)
class TrialReader:
    name: ReaderName
    read: ReadTrial
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


def resolve_granularity(reader: ReaderName, granularity: GranularityArg) -> Granularity:
    if granularity == "auto":
        return _DEFAULT[reader]
    if granularity not in _SUPPORTED[reader]:
        supported = ", ".join(sorted(_SUPPORTED[reader]))
        raise ValueError(
            f"{reader} does not support --granularity {granularity}; use: {supported}"
        )
    return granularity


def read_trial(
    path: Path,
    reader: TrialReader,
    *,
    granularity: GranularityArg = "auto",
) -> set[str]:
    resolved = resolve_granularity(reader.name, granularity)
    return reader.read(path, granularity=resolved)
