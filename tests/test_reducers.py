from differential_coverage.approach_data import ApproachData
from differential_coverage.types import CollectionReducer, ValueReducer
import pytest


@pytest.mark.parametrize(
    "reducer, expected",
    [
        (ValueReducer.MEDIAN, 2.0),
        (ValueReducer.MIN, 1.0),
        (ValueReducer.MAX, 6.0),
        (ValueReducer.AVERAGE, 3.0),
    ],
)
def test_value_reducer(reducer: ValueReducer, expected: float) -> None:
    assert reducer.reduce([1.0, 2.0, 6.0]) == expected


def test_collection_reducer() -> None:
    class TestApproachData(ApproachData[str, int]):
        def __init__(self, trials: dict[str, frozenset[int]]):
            self.calls: list[str] = []

        @property
        def edges_union(self) -> frozenset[int]:
            self.calls.append("edges_union")
            return frozenset()

        @property
        def edges_intersection(self) -> frozenset[int]:
            self.calls.append("edges_intersection")
            return frozenset()

    reducer = CollectionReducer.UNION
    approach_data = TestApproachData({})
    reducer.reduce(approach_data)
    assert approach_data.calls == ["edges_union"]

    reducer = CollectionReducer.INTERSECTION
    approach_data = TestApproachData({})
    reducer.reduce(approach_data)
    assert approach_data.calls == ["edges_intersection"]
