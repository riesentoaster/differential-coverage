# Differential Coverage

> A better way of comparing testing tools.

## Why?

Looking only at absolute (code) coverage when comparing testing tools loses a lot of information: Do all approaches cover the same blocks? Or just the same total count? How different is their coverage?

Here, *differential coverage* can help: By comparing *what parts* of the target is covered by each approach, we get much better insight into what is actually happening.

## What?

In principle, differential coverage measures how much of approach $a_2$'s coverage can also be covered by approach $a_1$. This can be done in multiple ways:

- `relcov` does exactly this. It is an *asymetrical* measure between coverage of two approaches. If the approach relies on randomness (such as most fuzzers), it can aggregate over multiple trials of these.
- `relscore` aggregates all this data to an order of all approaches. This measure, compared to simple coverage numbers, takes into account and values higher approaches that can cover code that no other approach covers. However, compared to `relcov`, this hides a lot of information in this aggregation.

For more precise definitions, including formulas, look at [DEFINITIONS.md](./DEFINITIONS.md).

## How?

`differential-coverage` currently reads `afl-showmap`-style data: files with `<edge_id>: <count>` rows, where `<count>` is only checked to contain a number $\geq 1$. These files are expected to be in the following structure:

```
coverage_data
|-- approach_1
|   |-- showmap_trial_1.out
|   |-- showmap_trial_2.out
|   `-- showmap_trial_3.out
|-- approach_2
|   |-- showmap_trial_1.out
|   |-- showmap_trial_2.out
|   `-- showmap_trial_3.out
`-- seeds
    `-- showmap.out
```

> If you would like support for other input formats, please raise an issue in the GitHub repository!

### Installation

Install `differential-coverage` directly from pypi:

```bash
pip install differential-coverage

# if you need latex output support
pip install differential-coverage[latex]
```

### Command Line Interface

Generally, the command line interface follows the following structure:

```bash
differential-coverage {relcov,relscore} <your-input-dir>
```

There are some options available, e.g. for output as csv or (colored) LaTeX table:

```
differential-coverage --help
```

### API

```python
from differential_coverage import (
    DifferentialCoverage,
    ApproachData,
    CollectionReducer,
    ValueReducer,
)

# last part (EdgeId) can be any comparable type, e.g. str, int
dc: DifferentialCoverage[str, str, Any]

# read from campaign directory, see above for structure
dc = DifferentialCoverage.from_campaign_dir("<your-input-dir>")
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
for approach_name, relscore in relscores.items():
    print(f"relscore {approach_name}: {relscore}")

```

### Hints

When using differential coverage to compare different testing approaches, you may want to do the following:
- Use this approach early on in your development process already, it has helped me uncover problems with my evaluation setup. And you want to discover those before having to redo your entire evaluation.
- For approaches that rely on radomness, such as most fuzzers, run multiple trials! This is generally necessary, not just for differential coverage[^sok].
- For approaches that rely on some sort of input corpus, such as some fuzzers, record coverage of the target when passed just the input corpus, and add that to your data. This allows analyzing how much extra coverage a fuzzer reaches, and how the corpus itself compares to other fuzzers.
- Related: If you compare an approach with different seed corpora, add coverage maps from all input corpora to your table, to compare them within each other, and against the approaches' results based on them.


## Development
Install dev dependencies and set up the pre-commit hook (runs a couple of checks before committing):
```bash
pip install -e ".[dev]"
pre-commit install
```

[^sok] SoK: Prudent Evaluation Practices for Fuzzing, https://ieeexplore.ieee.org/document/10646824
