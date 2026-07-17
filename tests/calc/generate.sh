#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD="${BUILD:-$ROOT/build}"
COVERAGE="${COVERAGE:-$ROOT/coverage}"
MERGE_COVERAGE="${MERGE_COVERAGE:-$ROOT/merge_coverage}"
EXPORTS="${EXPORTS:-$ROOT/exports}"

calc="${BUILD}/calc"
calc_fuzz="${BUILD}/calc-fuzz"
macro="${BUILD}/macro"

if [[ "${1:-}" == "clean" ]]; then
    rm -rf "$BUILD" "$COVERAGE" "$MERGE_COVERAGE" "$EXPORTS"
    exit 0
fi

for llvm_bin in /opt/homebrew/opt/llvm/bin /usr/local/opt/llvm/bin; do
    if [[ -d "$llvm_bin" ]]; then
        PATH="$llvm_bin:$PATH"
        break
    fi
done
export PATH

for tool in clang llvm-profdata llvm-cov; do
    command -v "$tool" >/dev/null || {
        echo "Missing required tool: $tool" >&2
        exit 1
    }
done

mkdir -p "$BUILD" "$COVERAGE" "$MERGE_COVERAGE" "$EXPORTS"

clang -g -O0 -fprofile-instr-generate -fcoverage-mapping \
    -o "$calc" "$ROOT/calc.c"
clang -g -O0 -fsanitize=fuzzer -DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION \
    -o "$calc_fuzz" "$ROOT/calc.c"
clang -g -O0 -fprofile-instr-generate -fcoverage-mapping \
    -o "$macro" "$ROOT/macro.c"

make_corpus_dir() {
    local corpus_file=$1
    local out_dir=$2
    local index=0

    rm -rf "$out_dir"
    mkdir -p "$out_dir"

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%%#*}"
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" ]] && continue
        printf '%s' "$line" >"$out_dir/$index"
        index=$((index + 1))
    done <"$corpus_file"

    if [[ "$index" -eq 0 ]]; then
        echo "Empty corpus: $corpus_file" >&2
        exit 1
    fi
}

run_trial() {
    local trial=$1
    local corpus="${ROOT}/corpora/${trial}.txt"
    local trial_build="${BUILD}/${trial}"
    local trial_merge_dir="${BUILD}/merge/${trial}"
    local name
    name="$(basename "$trial")"

    mkdir -p "$trial_build" \
        "${COVERAGE}/$(dirname "$trial")" \
        "${MERGE_COVERAGE}/$(dirname "$trial")" \
        "${BUILD}/llvm_summaries/$(dirname "$trial")" \
        "${BUILD}/merge_logs/$(dirname "$trial")"

    make_corpus_dir "$corpus" "$trial_merge_dir"

    local profraws=()
    local index=0
    local input_file
    for input_file in "$trial_merge_dir"/*; do
        local profraw="$trial_build/$index.profraw"
        LLVM_PROFILE_FILE="$profraw" "$calc" <"$input_file"
        profraws+=("$profraw")
        index=$((index + 1))
    done

    local profdata="$trial_build/trial.profdata"
    llvm-profdata merge -sparse "${profraws[@]}" -o "$profdata"
    llvm-cov export \
        -instr-profile="$profdata" \
        -object="$calc" \
        -format=text \
        >"${COVERAGE}/${trial}.json"
    llvm-cov export \
        --summary-only \
        -instr-profile="$profdata" \
        -object="$calc" \
        -format=text \
        >"${BUILD}/llvm_summaries/${trial}.json"
    "$calc_fuzz" -merge=1 \
        -merge_control_file="${MERGE_COVERAGE}/${trial}.merge" \
        "$empty" "$trial_merge_dir" \
        >"${BUILD}/merge_logs/${trial}.log" 2>&1
}

empty=$(mktemp -d)
trap 'rm -rf "$empty"' EXIT

while IFS= read -r -d '' corpus; do
    trial="$(basename "$(dirname "$corpus")")/$(basename "$corpus" .txt)"
    run_trial "$trial"
done < <(find "$ROOT/corpora" -name '*.txt' -print0 | sort -z)

macro_build="$BUILD/macro_run"
mkdir -p "$macro_build"
LLVM_PROFILE_FILE="$macro_build/run.profraw" "$macro"
llvm-profdata merge -sparse "$macro_build/run.profraw" -o "$macro_build/trial.profdata"
llvm-cov export \
    -instr-profile="$macro_build/trial.profdata" \
    -object="$macro" \
    -format=text \
    >"$EXPORTS/macro.json"

cp "$BUILD/seeds/t1/trial.profdata" "$BUILD/summary_only.profdata"
llvm-cov export \
    --summary-only \
    -instr-profile="$BUILD/summary_only.profdata" \
    -object="$calc" \
    -format=text \
    >"$EXPORTS/summary_only.json"
