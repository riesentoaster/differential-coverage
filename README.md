# Differential Coverage

Absolute coverage numbers aren't painting the whole picture: Different fuzzers may reach the same total coverage, but cover different parts of the program. Fuzzer (A) may reach more coverage than fuzzer (B), but (B) may reach coverage that (A) doesn't reach — so it's still valuable.

## Definition

Differential coverage is a measure for this. It was proposed by Leonelli et al. in their paper on TwinFuzz[^1]. This implementation relies on the formulas from the SBFT’25 Competition Report[^2]. There, Crump et al. define a fuzzers overall score compared to others as

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

## Explanation
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
```
differential_coverage <input_dir>
# or: python -m differential_coverage <input_dir>
```

Where `<input_dir>` is a directory of directories for each fuzzer, where each fuzzer subdirectory contains coverage files for each trial. Currently, the output format of `afl-showmap` is supported (lines with `edge_id:count`, where we only care if `count > 0`).

PRs for other data formats welcome :)

## Example
[`tests/sample_coverage`](./tests/sample_coverage/) provides sample coverage data to explain differential coverage. It contains 3 fuzzers and 3 edges:
- Edge 1 is always hit by all fuzzers
- Edge 2 is always hit by `fuzzer_c`, sometimes hit by `fuzzer_a`, and never hit by `fuzzer_b`
- Edge 3 is always hit by `fuzzer_b` and `fuzzer_c`, but only sometimes by `fuzzer_a`

```
differential_coverage tests/sample_coverage
```
produces
```
fuzzer_c: 1.00
fuzzer_a: 0.50
fuzzer_b: 0.00
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