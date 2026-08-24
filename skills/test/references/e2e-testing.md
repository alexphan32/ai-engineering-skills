# End-to-End Testing

Load this when a user-facing flow spans multiple screens, multiple services, or a multi-step
saga the user actually experiences from end to end (signup → verification → first login, add to
cart → checkout → payment → confirmation) — not for a single endpoint or component, which belongs
in integration/contract/unit tests instead.

**Core principle:** e2e tests sit at the top of the test pyramid on purpose — they're the slowest,
flakiest, and most expensive to maintain, so they should cover only the golden paths a business
actually depends on, with edge cases pushed down to integration/unit tests that can check the same
logic in milliseconds instead of seconds. A codebase with more e2e tests than integration tests
has usually pushed correctness-checking to the wrong layer, not tested more thoroughly.

## 1. Cover golden paths, not permutations [MUST]

```text
right-sized:  "user signs up, verifies email, logs in" — one e2e test
wrong-sized:  a separate e2e test for every validation error on the signup form
              → those belong in unit/integration tests against the form/endpoint directly
```

If you find yourself writing the third e2e test for the same flow with only the input varied,
that's a sign the variation belongs at a lower, faster test layer.

## 2. Use a real (or realistic) environment, but isolate test data [MUST]

Run against a staging-like environment with the real services wired together — mocking your own
services defeats the purpose of an e2e test. Third-party dependencies you don't control (payment
gateways, SMS providers) are the exception: use their sandbox/test mode, not a mock, so the real
integration contract is still exercised.

Each test run must use its own uniquely-namespaced data (a generated email/account per run) so
parallel runs and repeated runs don't collide or leave state that breaks the next run.

## 3. Wait on conditions, never on fixed sleeps [MUST]

```text
vulnerable: click "submit"; sleep(3); assert confirmation visible
required:   click "submit"; wait_for(confirmation_element, timeout=10s); assert visible
```

A fixed sleep is either too short (flaky under load) or too long (slow suite for no reason); a
condition-based wait is correct at any speed the system actually runs at. See
`systematic-debugging`'s `condition-based-waiting.md` for the underlying pattern — it isn't
e2e-specific, but e2e suites are where a missing wait strategy shows up as the most visible flake.

## 4. Reserve retries for infrastructure flake, not logic bugs [SHOULD]

A test retry mechanism (rerun once on failure) is acceptable for absorbing a genuinely transient
infra hiccup (a CI runner's network blip), but a test that only passes on retry because of a race
in the flow itself is a real bug in either the test's wait strategy or the product — investigate
before assuming "just flaky."

## 5. State what's out of scope [SHOULD]

Because e2e tests are expensive, explicitly state which parts of the flow are covered by this e2e
test versus by lower-layer tests, the same way the WRITE step's coverage-gap procedure asks for it
— an e2e suite that silently assumes edge cases are "probably" covered elsewhere is how a gap goes
unnoticed until production.

## Verify

```bash
# confirm no fixed sleep() calls smuggled into wait logic
grep -rn "sleep(\|time\.sleep\|Thread\.sleep" <new_e2e_test_file>

# confirm each test generates its own unique test data rather than reusing a shared fixture account
grep -n "test@example.com\|shared_user\|SHARED_" <new_e2e_test_file>
```

Run the new e2e test 2-3 times back to back — an e2e test that only passes on a cold environment
and fails on a warm one (leftover state from its own prior run) has an isolation bug, not a
tooling bug.
