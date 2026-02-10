from pathlib import Path
from typing import Any


def test_docs() -> None:
    from differential_coverage import (
        DifferentialCoverage,
        ApproachData,
        CollectionReducer,
        ValueReducer,
    )

    # last part (EdgeId) can be any comparable type, e.g. str, int
    dc: DifferentialCoverage[str, str, Any]

    # read from campaign directory, see above for structure
    dc = DifferentialCoverage.from_campaign_dir(
        Path(__file__).parent / "sample_coverage"
    )
    # or from a memory structure
    dc = DifferentialCoverage(
        {
            "approach_1": {"trial_1": {1, 2}, "trial_2": {1, 3}},
            "approach_2": {"trial_1": {1, 3}, "trial_2": {1, 3}},
            "approach_3": {"trial_1": {1, 2, 3}, "trial_2": {1, 2, 3}},
            "seeds": {"seeds": {1}},
        }
    )

    a1_name: str
    a1_data: ApproachData[str, Any]
    a2_name: str
    a2_data: ApproachData[str, Any]

    for a1_name, a1_data in dc.approaches.items():
        for a2_name, a2_data in dc.approaches.items():
            relcov: float = a1_data.relcov(
                a2_data,
                value_reducer=ValueReducer.MEDIAN,  # how to reduce relcov values from multiple trials from a1
                collection_reducer=CollectionReducer.UNION,  # how to reduce the edges from multiple trials from a2
            )
            print(f"relcov {a1_name} vs {a2_name}: {relcov}")

    relscores: dict[str, float] = dc.relscores()
    for fuzzer_name, relscore in relscores.items():
        print(f"relscore {fuzzer_name}: {relscore}")
