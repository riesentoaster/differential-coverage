from differential_coverage.readers import afl_showmap, llvm_cov
from differential_coverage.readers.registry import (
    Granularity,
    GranularityArg,
    InputFormat,
    read_trial,
    resolve_reader,
)

__all__ = [
    "Granularity",
    "GranularityArg",
    "InputFormat",
    "read_trial",
    "resolve_reader",
]

_ = (afl_showmap, llvm_cov)
