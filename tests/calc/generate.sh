#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD="${BUILD:-$ROOT/build}"
COVERAGE="${COVERAGE:-$ROOT/coverage}"

for llvm_bin in /opt/homebrew/opt/llvm/bin /usr/local/opt/llvm/bin; do
    if [[ -d "$llvm_bin" ]]; then
        PATH="$llvm_bin:$PATH"
        break
    fi
done

for tool in clang llvm-profdata llvm-cov; do
    command -v "$tool" >/dev/null || {
        echo "Missing required tool: $tool" >&2
        exit 1
    }
done

mkdir -p "$BUILD" "$COVERAGE"

clang -g -O0 -fprofile-instr-generate -fcoverage-mapping \
    -o "$BUILD/calc" "$ROOT/calc.c"

while IFS= read -r -d '' corpus; do
    approach="$(basename "$(dirname "$corpus")")"
    trial="$(basename "$corpus" .txt)"
    trial_build="$BUILD/$approach/$trial"
    out_dir="$COVERAGE/$approach"

    mkdir -p "$trial_build" "$out_dir"
    profraws=()
    index=0

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%%#*}"
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" ]] && continue

        profraw="$trial_build/$index.profraw"
        # shellcheck disable=SC2086
        LLVM_PROFILE_FILE="$profraw" "$BUILD/calc" $line
        profraws+=("$profraw")
        index=$((index + 1))
    done <"$corpus"

    if [[ ${#profraws[@]} -eq 0 ]]; then
        echo "Empty corpus: $corpus" >&2
        exit 1
    fi

    profdata="$trial_build/trial.profdata"
    llvm-profdata merge -sparse "${profraws[@]}" -o "$profdata"
    llvm-cov export \
        -instr-profile="$profdata" \
        -object="$BUILD/calc" \
        -format=text \
        >"$out_dir/$trial.json"
done < <(find "$ROOT/corpora" -name '*.txt' -print0 | sort -z)
