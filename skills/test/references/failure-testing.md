# Failure Testing

Load this when the change involves a queue, an external call, a multi-step flow that can crash
partway through, or any consumer of an at-least-once delivery source. This is distinct from
`concurrency-testing.md`: failure testing is about **a single flow breaking partway through**
(timeout, crash, lost message, duplicate redelivery) — it doesn't require two things happening at
the same time, just one thing happening incompletely. A feature can need either, both, or neither.

**Core principle:** the happy path proves the feature works when nothing goes wrong; failure tests
prove it stays correct when something does. For a distributed/async feature, an untested failure
mode isn't a minor gap — it's the part of the feature most likely to actually break in production,
since infrastructure failures (network blips, broker hiccups, process restarts) are routine at
scale even when the business logic is flawless.

## 1. Cover the canonical failure scenarios, not just "the API returns an error" [MUST]

At minimum, for any distributed/async flow, write a test for each of these that applies:

- **Duplicate message delivery** — the same message arrives twice; assert the effect happens once
- **Out-of-order message** — messages arrive in a different order than sent; assert the final
  state is still correct (or the design's stated ordering guarantee actually holds)
- **Consumer crash mid-processing** — the process dies after partial work; assert recovery
  reprocesses correctly rather than either losing the message or double-applying the partial work
- **DB commit failure after a message was consumed** — assert the message isn't acked as
  processed when the business write didn't actually commit
- **Message-broker publish failure** — assert the business transaction doesn't silently succeed
  while the event that was supposed to notify other systems was never sent (see the transactional
  outbox pattern in `.claude/skills/design/references/distributed-systems-checklist.md`)
- **External API timeout with unknown result** — the highest-value case (see item 2 below)
- **Retry exhaustion reaching the DLQ** — assert a message that fails every retry actually lands
  in the dead letter queue with enough context to triage, not silently dropped
- **Replay of an already-processed event** — assert replaying a message the system already
  processed produces no duplicate effect (this overlaps with idempotency, but from the failure-
  recovery angle: replay happens after an operator manually intervenes, not just under a race)

This list mirrors item 20 of
`.claude/skills/implement/references/distributed-systems-implementation-checklist.md` — that file
verifies the implementation *has* these paths; this one is about proving they're actually *tested*.

## 2. Timeout ≠ failure — test the unknown-result path explicitly [MUST]

```text
vulnerable test only covers: external call throws → code marks the operation failed
missing test:                external call times out (caller can't tell if the callee actually
                              executed) → code must NOT assume failure and retry blindly, since the
                              callee may have already succeeded (e.g. already charged the card)
```

```java
// what the failure test must assert
when(coreBankingClient.debit(any())).thenThrow(new TimeoutException());
transferService.process(transfer);
assertThat(transfer.getStatus()).isEqualTo(Status.UNKNOWN);   // not COMPLETED, not FAILED
verify(reconciliationQueue).enqueue(transfer.getId());        // triggers status-inquiry, not a blind retry
```

A test that only exercises the "external call throws a clean error" path misses the case that
actually causes double-charges and double-shipments in production: the call that timed out but
still executed on the other side.

## 3. Inject the failure at the boundary, not by deleting the dependency [SHOULD]

Simulate the failure by making the mocked/stubbed client throw, delay, or return a malformed
response at the exact call site — rather than, say, shutting down a real test container, which
tests infrastructure resilience (a different, valid but separate concern) rather than the
business logic's failure handling. For network-level fault injection against a real dependency
(partition, latency injection), a proxy like Toxiproxy is the right tool if the project needs that
level of realism; a mocked client throwing the right exception type is usually enough to prove the
business logic path is correct.

## 4. Assert the recovery path fired, not just that nothing crashed [MUST]

```text
weak:      assert no exception was thrown
stronger:  assert the message landed in the DLQ / the transaction rolled back / the reconciliation
           job was enqueued / the status transitioned to UNKNOWN — the actual recovery behavior the
           design specified for this failure
```

"Didn't crash" is a necessary but not sufficient bar — the design usually specifies exactly what
should happen on each failure (retry, DLQ, mark-unknown-and-reconcile); the test should assert
that specific behavior, not just survival.

## Verify

```bash
# confirm the test file actually injects a failure rather than only covering the happy path
grep -n "thenThrow\|reject(new\|side_effect=\|mockRejectedValue" <new_failure_test_file>

# cross-check coverage against the canonical list above
grep -ncE "duplicate|out.of.order|crash.mid|timeout|dead.letter|DLQ|replay" <new_failure_test_file>
```

If that second grep returns 0 or 1 for a feature with a Distributed & Async Design section, the
failure coverage is likely incomplete relative to what the design flagged as a risk.
