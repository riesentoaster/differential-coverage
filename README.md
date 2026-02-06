# Differential Coverage

Absolute coverage numbers aren't painting the whole picture: Different fuzzers may reach the same total coverage, but cover different parts of the program. Or, fuzzer (A) may reach more coverage than fuzzer (B), but (B) may reach coverage that (A) doesn't reach — so it's still valuable.

## Definition

There are different ways of measuring differential coverage:
- Leonelli et al. introduced `relcov` in their paper on TwinFuzz[^1]. It allows comparing the relative performance of one fuzzer against another and provides values $0\leq x\leq 1$.
- Alternatively, `relscore` was proposed in the SBFT’25 Competition Report[^2] by Crump et al. It provides a total ordering of a list of fuzzers.

### `relcov`
`relcov` was defined as the following[^1]:

$$
\text{upper}(f)=\bigcup\text{cov}(t)\quad\forall t\in \text{trials}(f)\\
$$

$$
\text{lower}(f)=\bigcap\text{cov}(t)\quad\forall t\in \text{trials}(f)\\
$$

$$
\text{relcov}(c,f)=\frac{\left|c\cap\text{upper}(f)\right|}{\left|\text{upper}(f)\right|}
$$

This can be used in various ways, such as:

#### Reliability of a Fuzzer

The reliability of a fuzzer $f$ is its ability to always reach its full potential across a set of trials of $f$ $T_f$. It is calculated as the median of the `relcov` values between each trial $t$ and the union of all reached coverage. Or, in a formula:

$$
\text{reliability}(f)=\text{med}({\text{relcov}(\text{cov}(t),f)})\quad\forall t\in T_f
$$

#### Performance over Input Corpus

The performance of a fuzzer $f$ over its input corpus is how much extra coverage it can reach past what is already reached in the input corpus. It is calculated as `relcov` of the coverage of the input corpus $c_\text{input-corpus}$ and the fuzzer. As a formula:

$$
\text{performance-over-input-corpus}(f)=\text{relcov}(c_\text{input-corpus},f)
$$

#### Performance over other fuzzers

The relative performance of a fuzzer $f_1$ relative to another fuzzer $f_2$ (or another configuration of the same fuzzer, or the same fuzzer with the same configuration but a different input corpus, or whatever else you want to test against) is how much extra coverage can be reached by $f_1$ over $f_2$. It is calculated as the median of the `relcov` values between each trial $t$ from a set of trials $T_{f_1}$ of $f_1$ against the union of all coverage reached by $f_2$ across different trials. Or, in a formula:

$$
\text{performance-over-fuzzer}(f_1, f_2)=\text{med}({\text{relcov}(\text{cov}(t),f_2)})\quad\forall t\in T_{f_1}
$$

### `relscore`

`relscore` was defined as the following[^2]:

$$
relscore(f,b,s,e) = \left|f_0\in F|e\notin \text{cov}(b,t,s)\forall t\in \text{trials}(f_0,b)\right|
\times\frac
{\left|\{t\in \text{trials}(f,b)\ |\ e \in \text{cov}(b,t,s)\}\right|}
{\left|\{t\in \text{trials}(f,b)\ |\ \text{cov}(b,t,s)\neq \emptyset\}\right|}
$$

The score of a fuzzer is then

$$
\text{score}(f,b,s)=\sum_{e\in E}\text{relscore}(f,b,s,e)
$$

This can be simplified to the following:

$$
\text{differential coverage}(f,e) = \text{number of fuzzers that never hit }e
\times\frac
{\text{number of trials of }f\text{ that hit }e}
{\text{number of trials of }f\text{ with non-empty cov}}
$$

$$
\text{score}(f) = \text{sum of differential coverage}(f,e)\text{ over all edges e}
$$

## Usage

> Disclaimer: This is subject to change.

Assume `<campaign_dir>` is a directory of subdirectories for each fuzzer, where each fuzzer subdirectory contains coverage files for each trial. Currently, the output format of `afl-showmap` is supported (lines with `edge_id:count`, where we only care if `count > 0`).

PRs for other data formats welcome :)

### Command Line Interface

All commands take the same campaign directory layout: one subdirectory per fuzzer, each with afl-showmap coverage files. Use `-o csv` for machine-readable output.

```bash
differential-coverage --help
```

```
usage: differential-coverage [-h] [-i PATTERN] [-x PATTERN] [--output FORMAT]
                             [--latex-rotate-headers DEGREES] [--latex-enable-color]
                             [--latex-colormap NAME]
                             command ...

Compute differential coverage relscore and relcov-based measures from afl-showmap
coverage. All commands take one campaign directory: one subdir per fuzzer, each with
coverage files.

options:
  -h, --help            show this help message and exit
  -i, --include-fuzzer PATTERN
                        Include only fuzzers whose name matches this regex (whitelist).
                        Can be specified multiple times; a fuzzer is kept if it matches
                        any pattern.
  -x, --exclude-fuzzer PATTERN
                        Exclude fuzzers whose name matches this regex. Can be specified
                        multiple times; apply after --include-fuzzer.
  --output, -o FORMAT   Output format: csv for CSV, latex for LaTeX tabular (requires
                        "latex" optional dependencies)
  --latex-rotate-headers DEGREES
                        Rotate LaTeX table column headers by this angle in degrees (e.g.
                        45). Requires \usepackage[table]{xcolor} and
                        \usepackage{adjustbox}.
  --latex-enable-color  Enable background colors for LaTeX tables and score outputs when
                        using --output latex. Requires \usepackage[table]{xcolor}.
  --latex-colormap NAME
                        Matplotlib colormap name to use for colored LaTeX output (e.g.
                        viridis, plasma, magma, inferno). Default: viridis.

subcommands:
  command
    relscore            Compute relscore (SBFT'25) from a campaign directory containing
                        one subdirectory per fuzzer with afl-showmap files.
    relcov              Compute relcov-based performance of each fuzzer relative to
                        reference fuzzers. By default prints a table (all fuzzers × all
                        fuzzers as reference). Use --single to get scores for one
                        reference only.
```

### API

Load a campaign from disk and run the same computations programmatically. The API lives in `differential_coverage.api`:

```python
from pathlib import Path
from differential_coverage.api import (
    read_campaign,
    run_relscore,
    run_relcov_performance_fuzzer,
    run_relcov_performance_fuzzer_all,
)

path = Path("path/to/campaign_dir")
campaign = read_campaign(path)  # dict[fuzzer_name, dict[trial_id, dict[edge_id, count]]]

# Relscore (SBFT'25): fuzzer -> score
scores = run_relscore(campaign)

# Relcov performance vs a reference fuzzer (reference excluded from result)
perf = run_relcov_performance_fuzzer(campaign, against="fuzzer_c")

# Relcov performance vs every fuzzer as reference: (ref_fuzzers, table[row][col])
ref_fuzzers, table = run_relcov_performance_fuzzer_all(campaign)
```

All `run_*` functions take a **campaign** (in-memory map: fuzzer name → trial id → edge id → count). Use `read_campaign(path)` to build it from a directory. The single-reference function returns `dict[str, float]` (fuzzer name → value). The `*_all` function returns `(list_of_refs, table)` where `table[row_fuzzer][ref_fuzzer]` is the score (1.0 on the diagonal). `run_relcov_performance_fuzzer` raises `ValueError` if the reference fuzzer is missing.

## Installation
```bash
pip install .
pip install ".[latex]" # if you need latex output support
```

## Development
Install dev dependencies and set up the pre-commit hook (runs a couple of checks before committing):
```bash
pip install -e ".[dev]"
pre-commit install
```

[^1]: TWINFUZZ: Differential Testing of Video Hardware Acceleration Stacks, https://www.ndss-symposium.org/ndss-paper/twinfuzz-differential-testing-of-video-hardware-acceleration-stacks/

[^2]: SBFT’25 Competition Report — Fuzzing Track, https://ieeexplore.ieee.org/document/11086561