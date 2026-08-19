import pickle
import warnings
from collections.abc import Collection, Mapping
from functools import reduce
from pathlib import Path
from typing import Generic

from differential_coverage.approach_data import ApproachData
from differential_coverage.fs import read_campaign_dir
from differential_coverage.readers import GranularityArg, InputFormat
from differential_coverage.types import (
    ApproachId,
    EdgeId,
    TrialId,
)


def _calculate_relscore(
    approach_data: ApproachData[TrialId, EdgeId],
    all_edges: frozenset[EdgeId],
    approaches_that_never_hit_edge: dict[EdgeId, set[ApproachId]],
) -> float:
    score = 0.0
    trials_with_non_empty_cov = len(
        [1 for trial in approach_data.edges_by_trial.values() if len(trial) > 0]
    )
    if trials_with_non_empty_cov == 0:
        warnings.warn("Approach has no trials with non-empty coverage")
        return 0.0

    for e in all_edges:
        approaches_that_never_hit_e = len(approaches_that_never_hit_edge[e])
        trials_that_hit_e = len(
            [1 for trial in approach_data.edges_by_trial.values() if e in trial]
        )
        score += (
            approaches_that_never_hit_e * trials_that_hit_e / trials_with_non_empty_cov
        )
    return score


class DifferentialCoverage(Generic[ApproachId, TrialId, EdgeId]):
    """High-level view of a full campaign across approaches and trials."""

    def __init__(
        self,
        campaign: Mapping[ApproachId, Mapping[TrialId, Collection[EdgeId]]],
    ) -> None:
        if len(campaign) == 0:
            raise ValueError("Did not provide any approaches")
        for f, t in campaign.items():
            if len(t) == 0:
                raise ValueError(f"Approach {f} has no trials")

        self._approaches: dict[ApproachId, ApproachData[TrialId, EdgeId]] = {
            f: ApproachData(t) for f, t in campaign.items()
        }

    @classmethod
    def from_campaign_dir(
        cls: type["DifferentialCoverage[ApproachId, TrialId, EdgeId]"],
        path: Path,
        *,
        input_format: InputFormat = "auto",
        granularity: GranularityArg = "auto",
        max_workers: int | None = None,
    ) -> "DifferentialCoverage[str, str, str]":
        return DifferentialCoverage[str, str, str](
            read_campaign_dir(
                path,
                input_format=input_format,
                granularity=granularity,
                max_workers=max_workers,
            )
        )

    # Pickle files hold a versioned envelope of builtins (not this class itself),
    # so old files survive refactorings of the class internals.
    PICKLE_FORMAT_VERSION = 1

    @classmethod
    def from_pickle(
        cls: type["DifferentialCoverage[ApproachId, TrialId, EdgeId]"],
        path: Path,
    ) -> "DifferentialCoverage[ApproachId, TrialId, EdgeId]":
        with path.open("rb") as f:
            envelope = pickle.load(f)
        if not isinstance(envelope, dict) or "format_version" not in envelope:
            raise ValueError(f"{path} is not a differential-coverage pickle file")
        version = envelope["format_version"]
        if version != cls.PICKLE_FORMAT_VERSION:
            raise ValueError(
                f"Unsupported pickle format version {version} in {path}; "
                f"this version of differential-coverage supports "
                f"version {cls.PICKLE_FORMAT_VERSION}"
            )
        campaign = envelope.get("campaign")
        if not isinstance(campaign, Mapping) or not all(
            isinstance(trials, Mapping)
            and all(isinstance(edges, Collection) for edges in trials.values())
            for trials in campaign.values()
        ):
            raise ValueError(
                f"Corrupt pickle file {path}: malformed campaign structure"
            )
        return cls(campaign)

    def to_pickle(self, path: Path) -> None:
        envelope = {
            "format_version": self.PICKLE_FORMAT_VERSION,
            "campaign": {
                name: {t: set(e) for t, e in data.edges_by_trial.items()}
                for name, data in self._approaches.items()
            },
        }
        with path.open("wb") as f:
            pickle.dump(envelope, f)

    @property
    def approaches(self) -> Mapping[ApproachId, ApproachData[TrialId, EdgeId]]:
        return self._approaches

    def coverage_counts(self) -> dict[ApproachId, int]:
        """Absolute coverage count per approach: size of the union of all trial edges."""
        return {
            approach_name: len(approach_data.edges_union)
            for approach_name, approach_data in self._approaches.items()
        }

    def relscores(self) -> dict[ApproachId, float]:
        all_edges = reduce(
            lambda x, y: x.union(y),
            (approach_data.edges_union for approach_data in self._approaches.values()),
        )
        approaches_that_never_hit_edge = {
            edge: {
                approach_name
                for approach_name, approach_data in self._approaches.items()
                if edge not in approach_data.edges_union
            }
            for edge in all_edges
        }

        scores = {
            approach_name: _calculate_relscore(
                approach_data, all_edges, approaches_that_never_hit_edge
            )
            for approach_name, approach_data in self._approaches.items()
        }
        return scores
