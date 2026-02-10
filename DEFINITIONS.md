# Definitions

Different ways of differential coverage were proposed:
- `relcov` was introduced by Leonelli et al. in their paper on TwinFuzz[^TwinFuzz]. It allows comparing the relative performance of one approach against another and provides values $0\leq x\leq 1$.
- `relscore` was proposed in the SBFT’25 Competition Report[^SBFT] by Crump et al. It provides a total ordering of a list of approaches.


## Variables
These definitions were originally used in the context of fuzzing, but generalize to all testing approaches that provide some way of (repeatedly) executing a target. These definitions thus use *approach $a$* instead of *fuzzer $f$*. An approach can be e.g. one of the following:
- A corpus of existing (scraped, generated, …) inputs
- All unit tests from a project
- A fuzzer with a specific configuration, harness, and input corpus
- Another fuzzer with a different configuration, harness, or input corpus.


## `relcov`
`relcov` was defined as the following[^TwinFuzz] :

$$
\begin{align}
\text{upper}(a)&=\bigcup\text{cov}(t)\quad\forall t\in \text{trials}(a) \\
\text{lower}(a)&=\bigcap\text{cov}(t)\quad\forall t\in \text{trials}(a) \\
\text{relcov}(c,a)&=\frac{\left|c\cap\text{upper}(a)\right|}{\left|\text{upper}(a)\right|}
\end{align}
$$

This can be used in various ways:

> To calculate all the following, calcualate the `relcov` table for all approaches $a_n$ and the coverage reached by each seed corpus.

### Reliability of an Approach

The reliability of an approach $a$ is its ability to always reach its full potential across a set of trials of $a$ $T_a$. It is calculated as the median of the `relcov` values between each trial $t$ and the union of all reached coverage. Or, in a formula:

$$
\begin{align}
\text{reliability}(a)=\text{med}({\text{relcov}(\text{cov}(t),a)})\quad\forall t\in T_a
\end{align}
$$

> In the full `relcov` table, the approach reliability is visible in the falling diagonal, so the `relcov` of an approach with itself.

### Reach of an Approach

The performance of a approach $a$ over its input corpus, or its *reach*, is how much extra coverage it can reach past what is already reached in the input corpus. It is calculated as `relcov` of the coverage of the input corpus $c_\text{input-corpus}$ and the approach. As a formula:

$$
\begin{align}
\text{reach}(a)=\text{relcov}(c_\text{input-corpus},a)
\end{align}
$$

> In the full `relcov` table, these values can be seen in the fields of the row representing the seeds and the column representing the fuzzer seeded with the seeds.

### Performance over Other Approaches

The relative performance of an approach $a_1$ relative to another approach $a_2$ is how much extra coverage can be reached by $a_1$ over $a_2$. It is calculated as the median (alternative reductions such as minimum, maximum, or average are also available in the implementation) of the `relcov` values between each trial $t$ from a set of trials $T_{a_1}$ of $a_1$ against the union of all coverage reached by $a_2$ across different trials. Or, in a formula:

$$
\begin{align}
\text{performance}(a_1, a_2)=\text{med}({\text{relcov}(\text{cov}(t),a_2)})\quad\forall t\in T_{a_1}
\end{align}
$$

> In the full `relcov` table, these values are the other values between approaches.

## `relscore`

`relscore` was defined as the following[^SBFT]:

$$
\begin{align}
\begin{split}
relscore(a,b,s,e) = \left|a_0\in A|e\notin \text{cov}(b,t,s)\forall t\in \text{trials}(a_0,b)\right|\\
\times\frac
{\left|\{t\in \text{trials}(a,b)\ |\ e \in \text{cov}(b,t,s)\}\right|}
{\left|\{t\in \text{trials}(a,b)\ |\ \text{cov}(b,t,s)\neq \emptyset\}\right|}
\end{split}
\end{align}
$$

The score of an approach is then

$$
\begin{align}
\text{score}(a,b,s)=\sum_{e\in E}\text{relscore}(a,b,s,e)
\end{align}
$$

This can be approximately simplified to the following:

$$
\begin{align}
\text{missing\_approaches}(e) &= \text{number of approaches that never hit }e \\
\text{hits}(a,e) &= \text{number of trials of }a\text{ that hit }e \\
\text{trials}(a) &= \text{number of trials of }a\text{ with non-empty coverage} \\
\text{relscore}(a,e) &= \text{missing\_approaches}(e)
\times\frac
{\text{hits}(a,e)}
{\text{trials}(a)} \\
\text{score}(a) &= \text{sum of relscore}(a,e)\text{ over all edges e}
\end{align}
$$


[^TwinFuzz]: TwinFuzz: Differential Testing of Video Hardware Acceleration Stacks, https://www.ndss-symposium.org/ndss-paper/twinfuzz-differential-testing-of-video-hardware-acceleration-stacks/

[^SBFT]: SBFT’25 Competition Report — Fuzzing Track, https://ieeexplore.ieee.org/document/11086561