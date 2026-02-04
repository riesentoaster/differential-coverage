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


#### Performance over other fuzzers

The relative performance of a fuzzer $f_1$ relative to another fuzzer $f_2$ (or another configuration of the same fuzzer, or the same fuzzer with the same configuration but a different input corpus, or whatever else you want to test against) is how much extra coverage can be reached by $f_1$ over $f_2$. It is calculated as the median of the `relcov` values between each trial $t$ from a set of trials $T_{f_1}$ of $f_1$ against the union of all coverage reached by $f_2$ across different trials. Or, in a formula:

$$
\text{performance-over-fuzzer}(f_1, f_2)=\text{med}({\text{relcov}(\text{cov}(t),f_2)})\quad\forall t\in T_{f_1}
$$

#### Performance over Input Corpus

The performance of a fuzzer $f$ over its input corpus is how much extra coverage it can reach past what is already reached in the input corpus. It is calculated as median of the `relcov` values between each trial $t$ from a set of trials $T_f$ of $f$ against the coverage of the input corpus on the target $c_{\text{input-corpus}}$. This is essentially a special case of $\text{performance-over-fuzzer}(f,f_\text{input})$ where $f_\text{input}$ is a fuzzer that will just pass all elements from the input corpus to the target and then exit. In a formula:

$$
\text{performance-over-input-corpus}(f)=\text{med}({\text{relcov}(\text{cov}(t),f_\text{input})})\quad\forall t\in T_f
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

TODO: is it number of trials of other fuzzers or other fuzzers?
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
Assume `<input_dir>` is a directory of directories for each fuzzer, where each fuzzer subdirectory contains coverage files for each trial. Currently, the output format of `afl-showmap` is supported (lines with `edge_id:count`, where we only care if `count > 0`).

PRs for other data formats welcome :)

### Command Line Interface
```
differential_coverage <input_dir>
```

#### Example
[`tests/sample_coverage`](./tests/sample_coverage/) provides sample coverage data to explain differential coverage. It contains 3 fuzzers and 3 edges:
- Edge 1 is always hit by all fuzzers
- Edge 2 is always hit by `fuzzer_c`, sometimes hit by `fuzzer_a`, and never hit by `fuzzer_b`
- Edge 3 is always hit by `fuzzer_b` and `fuzzer_c`, but only sometimes by `fuzzer_a`

```
differential_coverage tests/sample_coverage
```
then produces
```
fuzzer_c: 1.00
fuzzer_a: 0.50
fuzzer_b: 0.00
```
### API

```python
from pathlib import Path
from differential_coverage import (
    calculate_scores_for_campaign,
    calculate_differential_coverage_scores,
)

# From a campaign directory (one subdir per fuzzer, each with coverage files):
scores = read_campaign_and_calculate_score(Path("path/to/campaign_dir"))
# -> dict[str, float]: fuzzer name -> score

# From in-memory campaign data (fuzzer -> trial_id -> edge_id -> count):
campaign = {...}  # dict[str, dict[str, dict[int, int]]]
scores = calculate_differential_coverage_scores(campaign)
# -> dict[str, float]: fuzzer name -> score
```

## Installation
```bash
pip install .
```

## Development
Install dev dependencies and set up the pre-commit hook (runs a couple of checks before committing):
```bash
pip install -e ".[dev]"
pre-commit install
```

[^1]: TWINFUZZ: Differential Testing of Video Hardware Acceleration Stacks, https://www.ndss-symposium.org/ndss-paper/twinfuzz-differential-testing-of-video-hardware-acceleration-stacks/

[^2]: SBFT’25 Competition Report — Fuzzing Track, https://ieeexplore.ieee.org/document/11086561