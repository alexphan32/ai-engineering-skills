#!/usr/bin/env bash
# Grep-sweep for the mechanical checks in implement/SKILL.md's VERIFY step.
# These are candidate flags, not verdicts — a hit means "look at this line by hand,"
# not "this is broken." Silence means no obvious hit, not a guarantee.
#
# Usage: scripts/verify-checks.sh <path> [path...]
# <path> is usually the changed file(s) or the source dir for this change.

set -uo pipefail

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 <path> [path...]" >&2
  exit 1
fi

paths=("$@")
hits=0

check() {
  local label="$1"; shift
  local out
  out="$(grep -rnE "$@" "${paths[@]}" 2>/dev/null)"
  if [ -n "$out" ]; then
    echo "== $label =="
    echo "$out"
    echo
    hits=$((hits + 1))
  fi
}

check "Secrets committed"                '(password|secret|api_key|token)\s*='
check "Sensitive data logged"            'log\.(info|debug|warn|error)\(.*\b(password|token|otp|secret)\b'

# Query-in-loop / N+1: show 2 lines of context, then keep only hits near a loop keyword.
qil="$(grep -rnE -B2 '(findById|\.get\(|SELECT )' "${paths[@]}" 2>/dev/null | grep -B2 'for \|while \|forEach\|\.map(')"
if [ -n "$qil" ]; then
  echo "== Query-in-loop / N+1 candidate (confirm each hit by hand) =="
  echo "$qil"
  echo
  hits=$((hits + 1))
fi

check "Unbounded fetch-all"              '(findAll\(\)|fetchall\(\)|SELECT \*)'
check "Fire-and-forget async (Java)"      '@Async'
check "Fire-and-forget async (Go)"        '^\s*go [a-zA-Z]'
check "Direct status/state assignment"    '(\.setStatus\(|status = ")'
check "Money as float/double"             '(float.*amount|double.*amount|amount.*: number)'
check "Unbounded goroutine/thread spawn"  '(go func|new Thread\()'

if [ "$hits" -eq 0 ]; then
  echo "No candidate hits."
fi
