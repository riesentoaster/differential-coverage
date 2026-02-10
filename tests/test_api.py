from pathlib import Path
import pytest

from differential_coverage.api import DifferentialCoverage
from differential_coverage.approach_data import ApproachData

SAMPLE_DIR = (Path(__file__).parent / "sample_coverage").resolve()

SAMPLE_CAMPAIGN_CONTENT = {
    "approach_a": {
        "t1": {"1", "2"},
        "t2": {"1", "3"},
    },
    "approach_b": {
        "t1": {"1", "3"},
        "t2": {"1", "3"},
        "t3": {"1"},
    },
    "approach_c": {
        "t1": {"1", "2", "3"},
        "t2": {"1", "2", "3"},
    },
    "seeds": {
        "t1": {"1"},
    },
}

SAMPLE_CAMPAIGN_CONTENT_APPROACH_DATA = {
    f: ApproachData(t) for f, t in SAMPLE_CAMPAIGN_CONTENT.items()
}


def test_constructor() -> None:
    dc = DifferentialCoverage(SAMPLE_CAMPAIGN_CONTENT)
    assert dc.approaches == SAMPLE_CAMPAIGN_CONTENT_APPROACH_DATA

    with pytest.raises(ValueError):
        DifferentialCoverage({})
    with pytest.raises(ValueError):
        DifferentialCoverage({"approach_a": {}})


def test_read_campaign_dir() -> None:
    dc = DifferentialCoverage.from_campaign_dir(SAMPLE_DIR)
    approaches = {f: t.edges_by_trial for f, t in dc.approaches.items()}
    assert approaches == SAMPLE_CAMPAIGN_CONTENT


def test_relscores_single_approach() -> None:
    dc = DifferentialCoverage({"approach_a": {"t1": {1, 2}, "t2": {1, 3}}})
    assert dc.relscores() == {"approach_a": 0.0}


def test_relscores_multiple_approaches() -> None:
    dc = DifferentialCoverage(
        {
            "approach_a": {"t1": {1, 2}},
            "approach_b": {"t1": {1, 2, 3}},
            "approach_c": {"t1": {1, 3}, "t2": {1}},
        }
    )

    assert (
        dc.relscores()
        == {
            "approach_a": 1.0,  # 2 is not hit by approach_c
            "approach_b": 2.0,  # 2 is not hit by approach_c, 3 is not hit by approach_a
            "approach_c": 0.5,  # 3 is not hit by approach_a, but only hit in half of the trials
        }
    )
