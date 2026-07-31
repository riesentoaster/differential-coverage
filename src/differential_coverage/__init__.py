from differential_coverage.api import DifferentialCoverage
from differential_coverage.approach_data import ApproachData
from differential_coverage.cli import main
from differential_coverage.types import (
    ApproachId,
    CollectionReducer,
    EdgeId,
    TrialId,
    ValueReducer,
)

__all__ = [
    "ApproachData",
    "ApproachId",
    "CollectionReducer",
    "DifferentialCoverage",
    "EdgeId",
    "TrialId",
    "ValueReducer",
    "main",
]

if __name__ == "__main__":
    raise SystemExit(main())
