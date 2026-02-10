#!/usr/bin/env python3
from differential_coverage.cli import main
from differential_coverage.api import DifferentialCoverage
from differential_coverage.approach_data import ApproachData
from differential_coverage.types import (
    EdgeId,
    ApproachId,
    TrialId,
    ValueReducer,
    CollectionReducer,
)

__all__ = [
    "main",
    "DifferentialCoverage",
    "ApproachData",
    "EdgeId",
    "ApproachId",
    "TrialId",
    "ValueReducer",
    "CollectionReducer",
]

if __name__ == "__main__":
    raise SystemExit(main())
