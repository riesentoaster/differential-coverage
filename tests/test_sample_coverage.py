from pathlib import Path
from differential_coverage import read_campaign_and_calculate_score


def test_sample_coverage() -> None:
    scores = read_campaign_and_calculate_score(
        (Path(__file__).parent / "sample_coverage").resolve()
    )
    assert scores == {
        "fuzzer_c": 1.0,
        "fuzzer_a": 0.5,
        "fuzzer_b": 0.0,
    }
