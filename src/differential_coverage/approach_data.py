from functools import reduce
from typing import Collection, Generic, Mapping
from differential_coverage.types import CollectionReducer, EdgeId, TrialId, ValueReducer


class ApproachData(Generic[TrialId, EdgeId]):
    """Per-approach view of coverage data grouped by trial."""

    def __init__(self, trials: Mapping[TrialId, Collection[EdgeId]]) -> None:
        if len(trials) == 0:
            raise ValueError("Approach with no trials cannot be empty")
        for edges in trials.values():
            if len(edges) == 0:
                raise ValueError("Trial has no edges")

        self._edges_by_trial: dict[TrialId, set[EdgeId]] = {
            t: set(e) for t, e in trials.items()
        }
        self._edges_union: set[EdgeId] = reduce(
            lambda x, y: x.union(y), iter(self._edges_by_trial.values())
        )

        self._edges_intersection: set[EdgeId] = reduce(
            lambda x, y: x.intersection(y), iter(self._edges_by_trial.values())
        )

    @property
    def edges_union(self) -> frozenset[EdgeId]:
        return frozenset(self._edges_union)

    @property
    def edges_intersection(self) -> frozenset[EdgeId]:
        return frozenset(self._edges_intersection)

    @property
    def edges_by_trial(self) -> Mapping[TrialId, frozenset[EdgeId]]:
        return {t: frozenset(e) for t, e in self._edges_by_trial.items()}

    def relcov(
        self,
        other: "ApproachData[TrialId, EdgeId]",
        value_reducer: ValueReducer = ValueReducer.MEDIAN,
        collection_reducer: CollectionReducer = CollectionReducer.UNION,
    ) -> float:
        other_reduced = collection_reducer.reduce(other)
        return value_reducer.reduce(
            len(edges.intersection(other_reduced)) / len(other_reduced)
            for edges in self.edges_by_trial.values()
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ApproachData):
            return False
        return self.edges_by_trial == other.edges_by_trial
