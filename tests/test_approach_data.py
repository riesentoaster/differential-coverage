from copy import deepcopy
from typing import Any
from differential_coverage.approach_data import ApproachData
from differential_coverage.types import CollectionReducer, ValueReducer
from test_api import SAMPLE_CAMPAIGN_CONTENT
import pytest


def test_constructor() -> None:
    fuzzer_data = ApproachData(SAMPLE_CAMPAIGN_CONTENT)
    assert isinstance(fuzzer_data, ApproachData)
    with pytest.raises(ValueError):
        fuzzer_data = ApproachData({})


def test_edges_union() -> None:
    # single trial
    fuzzer_data = ApproachData({"t1": {1, 2}})
    assert fuzzer_data.edges_union == {1, 2}

    # multiple trials, no overlap
    fuzzer_data = ApproachData({"t1": {1, 2}, "t2": {3, 4}})
    assert fuzzer_data.edges_union == {1, 2, 3, 4}

    # multiple trials, some overlap
    fuzzer_data = ApproachData({"t1": {1, 2}, "t2": {2, 3}})
    assert fuzzer_data.edges_union == {1, 2, 3}


def test_edges_intersection() -> None:
    # single trial
    fuzzer_data = ApproachData({"t1": {1, 2}})
    assert fuzzer_data.edges_intersection == {1, 2}

    # multiple trials, no overlap
    fuzzer_data = ApproachData({"t1": {1, 2}, "t2": {3, 4}})
    assert fuzzer_data.edges_intersection == set()

    # multiple trials, some overlap
    fuzzer_data = ApproachData({"t1": {1, 2}, "t2": {2, 3}})
    assert fuzzer_data.edges_intersection == {2}


@pytest.mark.parametrize(
    "trials",
    [{"t1": {1, 2}}, {"t1": {1, 2}, "t2": {3, 4}}, {"t1": {1, 2}, "t2": {2, 3}}],
)
def test_edges_by_trial(trials: dict[str, set[int]]) -> None:
    fuzzer_data = ApproachData(deepcopy(trials))
    assert fuzzer_data.edges_by_trial == trials


def test_eq() -> None:
    fuzzer_data = ApproachData({"t1": {1, 2}})
    assert fuzzer_data == fuzzer_data  # eq to self
    assert fuzzer_data == deepcopy(fuzzer_data)  # eq to deepcopy
    assert fuzzer_data == ApproachData({"t1": {1, 2}})  # eq to same data
    assert fuzzer_data != ApproachData({"t1": {1, 2, 3}})  # different data
    assert fuzzer_data != ApproachData(
        {"t1": {1, 2}, "t2": {3, 4}}
    )  # different trials with different edges
    assert fuzzer_data != ApproachData(
        {"t1": {1, 2}, "t2": {1, 2}}
    )  # different trials with same edges
    assert fuzzer_data != ApproachData({"t2": {1, 2}})  # different trial name


def test_relcov_default_params_single_trials() -> None:
    a = {1, 2, 3}
    b = {4, 5, 6}
    c = {7, 8, 9}
    small_a = ApproachData({"t1": deepcopy(a)})
    small_b = ApproachData({"t1": deepcopy(b)})
    large_a = ApproachData({"t1": deepcopy(a) | deepcopy(b)})
    large_b = ApproachData({"t1": deepcopy(a) | deepcopy(c)})

    assert small_a.relcov(deepcopy(small_a)) == 1.0  # equal edges
    assert small_a.relcov(large_a) == 0.5  # subset
    assert large_a.relcov(small_a) == 1.0  # superset
    assert small_a.relcov(small_b) == 0.0  # no overlap
    assert small_b.relcov(small_a) == 0.0  # no overlap
    assert large_a.relcov(large_b) == 0.5  # some overlap
    assert large_b.relcov(large_a) == 0.5  # some overlap


def test_relcov_default_params_single_against_multiple_trials() -> None:
    a = {1, 2, 3}
    b = {4, 5, 6}
    c = {7, 8, 9}

    left = ApproachData({"t1": deepcopy(a)})

    # subset, full overlap of rhs
    right = ApproachData(
        {"t1": deepcopy(a) | deepcopy(b), "t2": deepcopy(a) | deepcopy(b)}
    )
    assert left.relcov(right) == 0.5

    # subset, full distinct of rhs
    right = ApproachData({"t1": deepcopy(a), "t2": deepcopy(b)})
    assert left.relcov(right) == 0.5

    # subset, some overlap of rhs
    right = ApproachData(
        {"t1": deepcopy(a) | deepcopy(b), "t2": deepcopy(a) | deepcopy(c)}
    )
    assert left.relcov(right) == 1.0 / 3

    left = ApproachData({"t1": deepcopy(a) | deepcopy(b)})
    # partial subset, some overlap of rhs
    right = ApproachData(
        {"t1": deepcopy(a) | deepcopy(b), "t2": deepcopy(a) | deepcopy(c)}
    )
    assert left.relcov(right) == 1.0 * 2 / 3


def test_relcov_default_params_multiple_against_single_trials() -> None:
    rhs = ApproachData({"t1": {1, 2, 3, 4, 5, 6}})

    # full overlap of lhs, subset of rhs
    lhs = ApproachData({"t1": {1, 2, 3}, "t2": {1, 2, 3}})
    assert lhs.relcov(rhs) == 0.5  # half coverage reached

    # full distinct of lhs, subset of rhs
    lhs = ApproachData({"t1": {1, 2, 3}, "t2": {4, 5, 6}})
    assert lhs.relcov(rhs) == 0.5  # both cover half

    # partial subset of rhs
    lhs = ApproachData({"t1": {1, 2}, "t2": {1, 2, 3, 4}, "t3": {1, 2, 3, 4, 5, 6}})
    assert lhs.relcov(rhs) == 1.0 * 2 / 3  # median, so 4/6

    # ignore cov from lhs not present in rhs
    lhs = ApproachData(
        {
            "t1": {i for i in range(10, 100)},
            "t2": {1, 2, 3} | {i for i in range(10, 100)},
            "t3": {1, 2, 3, 4, 5, 6} | {i for i in range(10, 100)},
        }
    )
    assert lhs.relcov(rhs) == 0.5  # half coverage reached on median


def test_relcov_value_reducer() -> None:
    # produce three values: 0, 0.5, 1.0
    lhs = ApproachData({"t1": {1, 2}, "t2": {1, 2, 3}, "t3": {1, 2, 3, 4, 5, 6}})
    rhs = ApproachData({"t1": {1, 2, 3, 4, 5, 6}})

    accesses = []
    original_getattr = ValueReducer.__getattribute__

    def spy_getattr(self: object, name: str) -> Any:
        if name == "reduce":

            def wrapped_reduce(*args: Any, **kwargs: Any) -> Any:
                assert len(kwargs) == 0
                assert len(args) == 1
                args = tuple(list(e) for e in args)
                accesses.append(args[0])
                return original_getattr(self, name)(*args, **kwargs)

            return wrapped_reduce
        else:
            return original_getattr(self, name)

    setattr(ValueReducer, "__getattribute__", spy_getattr)

    res = lhs.relcov(rhs, value_reducer=ValueReducer.MEDIAN)
    assert res == 0.5  # default median from superclass
    assert accesses == [[1.0 / 3.0, 0.5, 1.0]]


def test_relcov_collection_reducer() -> None:
    lhs = ApproachData({"lhs1": {1}})
    rhs = ApproachData({"rhs1": {1}, "rhs2": {2}})

    accesses = []
    original_getattr = CollectionReducer.__getattribute__

    def spy_getattr(self: object, name: str) -> Any:
        if name == "reduce":

            def wrapped_reduce(*args: Any, **kwargs: Any) -> Any:
                assert len(kwargs) == 0
                assert len(args) == 1
                accesses.append(args[0])
                return original_getattr(self, name)(*args, **kwargs)

            return wrapped_reduce
        else:
            return original_getattr(self, name)

    setattr(CollectionReducer, "__getattribute__", spy_getattr)

    res = lhs.relcov(rhs, collection_reducer=CollectionReducer.UNION)
    assert res == 0.5  # default: union of rhs, so half is reached
    assert accesses == [ApproachData({"rhs1": {1}, "rhs2": {2}})]
