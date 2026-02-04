from pathlib import Path
from differential_coverage import calculate_scores_for_campaign


def test_sample_coverage() -> None:
    scores = calculate_scores_for_campaign(
        (Path(__file__).parent / "sample_coverage").resolve()
    )
    assert scores == {
        "fuzzer_c": 1.0,
        "fuzzer_a": 0.5,
        "fuzzer_b": 0.0,
    }
