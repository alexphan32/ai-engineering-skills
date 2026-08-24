---
name: test
description: >
  Use when the ask is about test coverage or strategy rather than feature code — "viết test cho
  module X", "test coverage đã đủ chưa", "cần test tải/performance cho endpoint Y", "contract test
  giữa 2 service", or after `/review` flags missing coverage. Do NOT use for the inline
  RED→GREEN loop while writing a single function (`/implement` covers that) or to judge whether
  existing code has bugs (`/review`).
---

## OVERVIEW

Design and write the tests a feature needs beyond the single inline unit test `/implement`
already writes per function — which test *types* the change needs, what the coverage gap is,
and how to actually write an integration/contract/performance/concurrency test in this stack.

**Relationship to `/implement`:** `/implement`'s Step 2 (TEST) writes the RED→GREEN unit test
for the function being changed, in the same pass as the code. `/test` covers everything that
doesn't fit that inline loop — a coverage audit, a new integration suite, a contract test
between two services, a load test, or a concurrency/failure-injection test for a distributed
flow. Mid-`/implement` and just need "does this function work"? Stay in `/implement`.

**Core principle:** a test that can't fail is not a test. Before writing any test, know what
production bug it would have caught — if you can't state one, the test is checking that the
mock behaves like the mock, not that the system behaves correctly.

---

<HARD-GATE>
Do NOT write a test until:
1. You know exactly which test type(s) this change needs (see SELECT below) — not "write some tests"
2. For a bug-driven test: you can reproduce the bug's failure first (see Prove-It pattern below)
3. You know the project's test runner/conventions — check CLAUDE.md, don't guess a framework

Do NOT claim "tested" or "covered" until:
4. The new test fails without the fix/feature and passes with it (you actually ran both states)
5. The full relevant suite passes, not just the new test in isolation
6. No test asserts on a mock's own behavior instead of the system's observable behavior
</HARD-GATE>

**Violating any gate = violating the spirit of the skill.** Common rationalizations:

| Rationalization | Reality |
|----------------|---------|
| "I wrote the test after the fix, but I'm confident it would've failed before" | Confidence isn't evidence. Stash the fix, run the test, confirm RED, then restore GREEN. |
| "Unit tests cover this, no need for an integration test" | A unit test with everything mocked doesn't prove the pieces actually connect. If the SDS crosses a boundary, test the boundary. |
| "This is just a happy-path feature, edge cases can come later" | "Later" is how untested edge cases ship. Cover null/empty/boundary/concurrent inputs now. |
| "The mock returns what the real service returns, so this is basically an integration test" | It's testing your assumption about the real service, not the real service. Label it a unit test and add a real (or contract) test separately. |
| "Performance testing is overkill for this endpoint" | Only true if the SDS/design didn't flag a scale signal. If it did (loop-over-query, list/export endpoint, high-traffic path), skip it deliberately and say why, don't skip it silently. |
| "Flaky test, I'll just add a retry/sleep" | A flaky test is signaling a real race or ordering bug, or a bad wait strategy. Fix the wait condition (see `condition-based-waiting`), don't paper over it. |
| "Still flaky after my fix, I'll just skip it for now" | Quarantine it with an owner and tracking ticket, not a bare skip — an untracked skip is a silent coverage gap that never gets revisited. |

**Red Flags — STOP and fix before continuing:**
- Writing an assertion before confirming what failure it would catch
- A new test that passes on the very first run with no prior RED state
- Mocking the exact thing the test is supposed to verify
- Adding `sleep()`/arbitrary waits instead of polling a real condition
- Marking a feature "tested" when only the happy path has a test

---

## WORKFLOW

### 1. SCOPE — What is actually being tested

Identify the artifact under test and what kind of correctness matters for it:
- A single function/class in isolation → **unit**
- The seam between two components/modules in the same service → **integration**
- The seam between two independently deployed services → **contract**
- A full user-facing flow end to end → **e2e**
- Latency/throughput/resource usage under load → **performance**
- Multiple threads/requests touching the same shared state at once (race, lost update, double-spend) → **concurrency**
- A single flow breaking partway through (timeout, crash, lost/duplicate/out-of-order message) → **failure**

Concurrency and failure are easy to conflate but differ — concurrency is about *simultaneity*,
failure is about *incompleteness* — a feature can need either, both, or neither. See
`references/concurrency-testing.md` and `references/failure-testing.md`.

### 2. SELECT — Which type(s) this change needs

Don't default to unit-only. Pull signals from the SDS/spec — each row maps to a reference file
with concrete methodology, tooling, and a verify checklist:

| Signal in the SDS/spec | Test type to add | Reference |
|---|---|---|
| Data Integrity section (uniqueness, invariants, multi-table writes) | Integration test hitting the real constraint, not a mock | `references/integration-testing.md` |
| Cross-service API call (calls, or is called by, an independently deployed service) | Contract test | `references/contract-testing.md` |
| Full user-facing flow spans multiple screens/services (signup→login, checkout→payment) | E2e test | `references/e2e-testing.md` |
| Performance/scale tier ≥2 (see `.claude/skills/architecture/references/system-scale-checklist.md`) | Performance/load test | `references/performance-testing.md` |
| Concurrent access to shared state (parallel workers, same-resource writes, idempotency under simultaneous requests) | Concurrency test | `references/concurrency-testing.md` |
| Distributed & Async Design section present (queue, external call, retry, crash-mid-flow risk) | Failure/resilience test | `references/failure-testing.md` |
| Security Design section present (auth, payments, state transitions) | Security-critical test cases | `.claude/skills/design/references/security-checklist.md` |
| No SDS, just a bug fix | Unit test reproducing the bug | Prove-It pattern below |

If nothing above applies, unit tests covering the changed logic and its edge cases are enough —
don't manufacture integration/performance tests the change doesn't need.

### 3. WRITE

**For a new feature, at whichever non-unit test type SELECT pointed at (TDD):** the same
write-fails-first-then-implement shape as `/implement`'s inline unit test, applied at the
integration/contract/e2e/performance/concurrency level SELECT identified:
1. Write the test against the intended interface before the implementation exists
2. Run it — confirm it fails for the right reason (missing implementation, not a typo)
3. Implement the minimum to pass
4. Run again — confirm GREEN

**For a bug fix (Prove-It pattern):**
1. Write a test that reproduces the reported bug using its exact triggering input/state
2. Run it against the unfixed code — confirm RED (this proves the test actually catches the bug)
3. Apply the fix
4. Run again — confirm GREEN
5. Never skip step 2 — a test that was never seen failing might be passing for an unrelated reason

**For a coverage gap (post-review or audit):**
1. List what's covered vs. not, per the SELECT table above — don't just eyeball line coverage
2. Prioritize by likely cost of a regression there (data corruption > wrong response > cosmetic)
3. Write the highest-priority gap first; state which gaps remain and why, if deferring

**Non-unit test mechanics:** each type below has its own reference with methodology, tooling,
code patterns, and a verify checklist — load the one(s) SELECT pointed at, don't guess:
- `references/integration-testing.md` — real dependency over mock, constraint tests, isolation
- `references/contract-testing.md` — consumer-driven contracts vs. schema diffing, CI wiring
- `references/e2e-testing.md` — golden-path scoping, environment/data isolation, flake control
- `references/performance-testing.md` — load/stress/spike/soak, stated budgets, percentiles
- `references/concurrency-testing.md` — forcing real overlap, asserting invariants, race detectors
- `references/failure-testing.md` — canonical failure scenarios, timeout ≠ failure, fault injection

All non-unit test types share one rule worth stating up front: use condition-based waiting/polling
for async state, never a fixed `sleep()` — see `systematic-debugging`'s `condition-based-waiting.md`
for the pattern.

### 4. VERIFY

```bash
<project_test_runner> <new_test_file>       # new test(s) pass in isolation
<project_test_runner>                       # full relevant suite — no regressions introduced
```

- Re-run the new test 2-3 times if it touches concurrency/timing — an order-dependent test that
  passes once will flake in CI
- State test-coverage Implementation Readiness the same way `/spec`/`/design` state theirs: which
  test types exist now, which are deliberately deferred, and why

**A test that stays flaky after a genuine wait-condition fix attempt** doesn't get silently
skipped or deleted — quarantine it: mark it skipped/flaky-tagged with a comment naming the
tracking ticket/owner and the date, so it stays visible as a known gap instead of quietly
disappearing from coverage. A quarantined test with no owner or no re-check date is the same as
deleting it, just slower.

---

## RELATIONSHIP TO OTHER SKILLS

| Skill | How it connects |
|---|---|
| `/implement` | Writes the inline unit test per function; hand off here for anything broader |
| `/review` | Flags missing/weak coverage as a review finding; this skill is where you go fix it |
| `/design` | Its Distributed & Async / Security / Performance sections are the primary signal source for SELECT |
| `/operate` | Production incidents often reveal a missing test class — feed findings back here |
