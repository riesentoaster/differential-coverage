# Differential Coverage

> A better way of comparing testing tools.

## Why?

Looking only at absolute (code) coverage when comparing testing tools loses a lot of information: Do all approaches cover the same blocks? Or just the same total count? How different is their coverage?

Here, *differential coverage* can help: By comparing *what parts* of the target is covered by each approach, we get much better insight into what is actually happening.

## What?

In principle, differential coverage measures how much of approach $a_2$'s coverage can also be covered by approach $a_1$. This can be done in multiple ways:

- `relcov` does exactly this. It is an *asymetrical* measure between coverage of two approaches. If the approach relies on randomness (such as most fuzzers), it can aggregate over multiple trials of these.
- `relscore` aggregates all this data to an order of all approaches. This measure, compared to simple coverage numbers, takes into account and values higher approaches that can cover code that no other approach covers. However, compared to `relcov`, this hides a lot of information in this aggregation.
- `count` just reports absolute coverage counts (union of covered edges/blocks/branches across trials) per approach — useful as a baseline, but without the differential comparison.

For more precise definitions, including formulas, look at [DEFINITIONS.md](./DEFINITIONS.md).

## How?

Campaign data lives in one directory per approach, with one file per trial. Three input formats are supported.

**All approaches in one campaign must use the same input format and the same edge ID scheme.** afl-showmap edge IDs (numeric bitmap indices), libFuzzer merge COV indices (PC-table indices), and llvm-cov edge IDs (source locations) are not comparable — do not mix them in one campaign. Format is detected from file content (`auto`, default). Override with `--input-format` if needed.

For **afl-showmap** and **libfuzzer-merge**, edge IDs are opaque indices into the instrumented binary, so every trial must use the **same binary** (same build/instrumentation). **llvm-cov** uses source locations instead, so the binary may differ as long as source paths are consistent across exports (I think™).

### afl-showmap

Files contain `<edge_id>: <count>` rows; only whether count ≥ 1 matters. Edge IDs are opaque strings from the fuzzer bitmap (e.g. `12345`).

```
coverage_data
|-- approach_1
|   |-- trial_1.out
|   |-- trial_2.out
|   `-- trial_3.out
|-- approach_2
|   |-- trial_1.out
|   `-- trial_2.out
|   `-- trial_3.out
`-- seeds
    `-- seeds.out
```

### llvm-cov export JSON

Same layout, with JSON trial files from `llvm-cov export` (LLVM's `-format=text` produces JSON):

```
coverage_data
|-- approach_1
|   |-- trial_1.json
|   `-- trial_2.json
`-- seeds
    `-- seeds.json
```

Generate each trial file with:

```bash
llvm-cov export \
  -instr-profile=default.profdata \
  -object=./my_binary \
  -format=text \
  > trial_1.json
```

Run once per trial (merge profdata first if a trial replays multiple inputs). Use `--granularity branch` or `block` for llvm-cov exports; afl-showmap uses `edge` (selected automatically with `--granularity auto`).

On macOS, use Homebrew LLVM rather than Apple Clang: `brew install llvm`, then either add `$(brew --prefix llvm)/bin` to your `PATH` or call tools by full path (e.g. `$(brew --prefix llvm)/bin/clang`). Built-in `clang` _may_ work, but is untested.

**All trials in a campaign must use the same input format, granularity, and consistent source paths (llvm-cov).** If paths differ between machines, re-export with `llvm-cov export -path-equivalence=<build-path>,<local-path>`.

#### cov-analysis

For fuzzer campaigns, [cov-analysis](https://github.com/aflplusplus/cov-analysis) can generate trial JSON for you: it replays AFL++, libFuzzer, libafl, or honggfuzz output through an instrumented binary and writes an `llvm-cov` export to `<fuzzer-out>/cov/coverage.json`.

```bash
cov-analysis build make -j$(nproc)
cov-analysis -d /path/to/fuzzer-out/ -e "./cov @@"
```

Copy one `coverage.json` per trial into your campaign directory (same layout as above). The format matches `llvm-cov export -format=text`.

### libFuzzer merge control files

Same layout, with merge control files from libFuzzer's `-merge=1` mode:

```
coverage_data
|-- approach_1
|   |-- trial_1.merge
|   `-- trial_2.merge
`-- seeds
    `-- seeds.merge
```

Generate each trial file by merging a seeds corpus with trial inputs and keeping the control file:

```bash
empty=$(mktemp -d)
./my_fuzzer -merge=1 -merge_control_file=trial_1.merge "$empty" CORPUS_DIR
rmdir "$empty"
```

Use an empty first corpus so every input is recorded. The reader unions all `COV` lines (PC-table indices; `--granularity edge`). Same binary across trials; LLVM 10+.

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
differential-coverage {relcov,relscore,count} [--input-format {auto,afl-showmap,llvm-cov,libfuzzer-merge}] [--granularity {auto,branch,block,edge}] <campaign-dir>
```

Examples:

```bash
differential-coverage relscore ./coverage_data
differential-coverage count ./coverage_data
differential-coverage --input-format llvm-cov relcov ./coverage_data
differential-coverage --output csv relscore ./coverage_data
```

To avoid re-parsing a large campaign, `pickle` saves the parsed data to a file that any subcommand can read back via `--input-format pickle`:

```bash
differential-coverage pickle ./coverage_data campaign.pkl
differential-coverage --input-format pickle relscore campaign.pkl
```

There are more options available, e.g. for output as csv or (colored) LaTeX table:

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
# or save/load the parsed data as a versioned pickle file
dc.to_pickle(Path("campaign.pkl"))
dc = DifferentialCoverage.from_pickle(Path("campaign.pkl"))
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

counts: dict[str, int] = dc.coverage_counts()
for approach_name, count in counts.items():
    print(f"coverage {approach_name}: {count}")

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
