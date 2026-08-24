# Distributed Systems & Async Processing Implementation Checklist

Load this whenever the code being implemented publishes/consumes a message, calls another
service or an external system (Core Banking, payment gateway), runs work asynchronously, or
manages an entity with a status/lifecycle field. Design-time rationale for every item here lives
in `.claude/skills/design/references/distributed-systems-checklist.md` — this file verifies the
code actually implements what was designed, with concrete per-stack patterns.

## Priority levels

Same convention as the other implementation checklists: **[MUST]** blocks completion,
**[SHOULD]** needs an explicit reason if skipped, **[MAY]** is workload-dependent. Several items
here are MUST even where the analogous performance item would only be SHOULD, because getting
these wrong corrupts data rather than just degrading latency.

## 1. Data Ownership Boundary [MUST]

Grep for any code in this service writing to a table/collection this service doesn't own — a
repository/DAO reaching into another service's schema, or a raw connection string pointed at
another service's database, is the shared-database anti-pattern regardless of how it's phrased
in code. Cross-service access must go through that service's API/event stream.

## 2. Durable Async — Not Fire-and-Forget [MUST]

```java
// vulnerable — lost if the process crashes before this completes
@Async
public void processTransfer(...) { ... }
```
```go
// vulnerable — same problem
go processTransfer(...)
```

Verify any business-critical async path is backed by a durable mechanism (Kafka, RabbitMQ, SQS,
or a persisted job table a worker polls) — not a bare `@Async`/`go func()` with no persistence.

## 3. Transactional Outbox [MUST when a DB write and an event publish must be atomic]

```java
// vulnerable — two systems, two separate commits, a gap between them
@Transactional
public void createOrder(Order order) {
    orderRepository.save(order);
}
// then, outside the transaction:
kafkaTemplate.send("orders", orderCreatedEvent);   // can fail after the DB already committed

// required — outbox row written in the SAME transaction as the business write
@Transactional
public void createOrder(Order order) {
    orderRepository.save(order);
    outboxRepository.save(new OutboxEvent(order.getId(), "ORDER_CREATED", toJson(order)));
}
// a separate poller/publisher reads unsent outbox rows and publishes them, marking sent on success
```

Verify the outbox table actually exists, the business write and the outbox insert share one
transaction, and a publisher process (polling or CDC-based) is what actually sends to Kafka — not
an inline publish call sitting outside the transaction.

## 4. Idempotent Consumers [MUST for any consumer of an at-least-once source]

```java
// required shape
@KafkaListener(topics = "transfers")
public void onTransfer(TransferEvent event) {
    if (processedEventRepository.existsById(event.getEventId())) {
        return; // already handled
    }
    // business update + markProcessed in the SAME transaction:
    transferService.applyTransfer(event);
    processedEventRepository.save(new ProcessedEvent(event.getEventId()));
}
```

Verify: (a) a dedup check exists keyed on the event/message ID, (b) the "mark processed" write is
in the same transaction as the business update — not a separate, best-effort write that can
diverge from whether the business update actually committed.

## 5. Message Ordering / Partition Key [MUST when the design specified an ordering scope]

Verify the producer actually sets the partition key the design specified (e.g. `accountId`) —
grep the producer call for a key argument; a `send(topic, value)` call with no key means Kafka
partitions round-robin/randomly, silently breaking any assumed per-account ordering.

## 6. Optimistic Locking [SHOULD, verify before reaching for a distributed lock]

```sql
UPDATE account SET balance = ?, version = version + 1 WHERE id = ? AND version = ?
```

Verify the calling code checks the affected-row count and treats 0 as a concurrent-modification
error (retry or fail explicitly) — silently ignoring a 0-row update result means the caller
believes an update succeeded when it didn't.

## 7. Distributed Lock Hygiene [MUST if a distributed lock is used at all]

```go
// vulnerable — no lease timeout, a crashed holder locks this forever
lock.Acquire(key)
// required
lock.AcquireWithLease(key, leaseTimeout)
defer lock.Release(key)
// plus a renewal path if the critical section can outlast one lease
```

Verify every acquired lock has a lease timeout and a release path that runs even on failure
(`defer`/`finally`), and that the code doesn't reach for a distributed lock where optimistic
locking, a DB uniqueness constraint, or idempotency would have solved the same problem more
cheaply.

## 8. State Machine Transitions [MUST for any status/lifecycle field]

```java
// vulnerable — consumer sets status directly, bypassing transition rules
transfer.setStatus(Status.COMPLETED);
// required — transition validated against the current state
transfer.transitionTo(Status.COMPLETED); // throws IllegalStateTransitionException if not allowed from current state
```

Grep for direct status-field assignment outside the state machine's transition method — that's
the single most common way an "impossible" state gets into production data.

## 9. Saga Steps & Compensation [MUST for a multi-service business transaction]

Verify each Saga step implemented has a corresponding compensation implemented and wired into the
failure path — not just a forward action with a TODO for the rollback. If using an orchestrator,
verify it persists its own progress (which step it's on) so a crash mid-saga can resume rather
than losing track of an in-flight transaction.

## 10. Retry & Backoff [MUST]

```java
// vulnerable — unbounded, no backoff, retries validation errors too
while (true) { try { call(); break; } catch (Exception e) {} }

// required
@Retryable(retryFor = {TimeoutException.class, ConnectException.class},
           maxAttempts = 5, backoff = @Backoff(delay = 1000, multiplier = 2, random = true))
```

Verify retry logic excludes non-retryable errors (4xx, validation, business rejection) — a retry
loop that doesn't discriminate error types will hammer a dependency returning 400s just as hard
as one returning 503s.

## 11. Dead Letter Queue Wiring [MUST for a consumer with retry]

Verify a DLQ actually exists and is reachable — a consumer that logs-and-drops after retry
exhaustion has no DLQ regardless of what the design said. Verify the DLQ payload carries
`eventId, eventType, payload/reference, source, partition, offset, retryCount, error, failedAt,
correlationId` — a DLQ entry missing these can't be triaged without re-deriving context from
other logs.

## 12. Reconciliation Job [MUST for a financial/critical distributed workflow]

Verify a reconciliation job/endpoint exists that compares this service's authoritative fields
against the external system of record, and that a detected mismatch actually triggers
alert/repair/manual-review — not just a log line no one is watching.

## 13. Unknown Result Handling [MUST for any external call whose timeout doesn't guarantee non-execution]

```java
// vulnerable — treats a timeout as a failure and may double-execute on retry
try {
    coreBankingClient.debit(request);
} catch (TimeoutException e) {
    markFailed(transactionId);   // WRONG — Core Banking may have already succeeded
}

// required
try {
    coreBankingClient.debit(request);
    markCompleted(transactionId);
} catch (TimeoutException e) {
    markUnknown(transactionId);   // then: status-inquiry call or reconciliation, never a blind retry
}
```

Grep for a `catch`/`except` on a timeout that transitions state to a terminal failure — that's
the exact bug this checklist exists to catch.

## 14. Idempotency Key Propagation [MUST for a multi-hop flow]

Verify the same `idempotencyKey`/`correlationId`/`transactionId` is threaded through every hop
(don't grep-generate a new ID at each layer) — check the producer code actually forwards the
incoming key onto the outgoing event/request rather than calling a new-ID generator again.

## 15. Correlation ID Propagation [SHOULD]

Verify HTTP calls and message headers actually carry `traceId`/`correlationId` — check the
outgoing client/producer code sets the header/property, not just that a logging config mentions
one.

## 16. Backpressure & Consumer Scaling [SHOULD]

Verify consumer concurrency configuration is actually bounded and consistent with the topic's
partition count (adding consumer instances beyond partition count adds no throughput for that
topic) — a mismatch here is a common "why isn't scaling out helping" bug.

## 17. Event Schema Versioning [SHOULD]

Verify a new/changed event schema includes a version field or is otherwise backward compatible
with in-flight consumers that haven't deployed the new schema yet — a breaking schema change
deployed without versioning can crash consumers mid-rollout.

## 18. Checkpointed Batch/Migration [MUST for a migration or backfill over a large table]

```python
# vulnerable — one giant transaction, no recovery if it crashes at row 9,000,000
db.execute("UPDATE big_table SET ... ")

# required — chunked with a checkpoint
last_id = load_checkpoint()
while True:
    batch = fetch_batch(after_id=last_id, size=100_000)
    if not batch: break
    process_and_commit(batch)
    last_id = batch[-1].id
    save_checkpoint(last_id)
```

Verify a checkpoint is persisted after each chunk and the job resumes from it rather than
restarting from zero on a crash.

## 19. Anti-Pattern Grep Sweep [MUST — run before claiming distributed/async-reviewed]

```bash
# fire-and-forget async on a business-critical path (flags candidates — verify each hit)
grep -rn "@Async" <source_dir> --include="*.java"
grep -rn "^\s*go [a-zA-Z]" <source_dir> --include="*.go"

# consumer with no visible idempotency check near it
grep -n -A5 "@KafkaListener\|consumer.on(\|@EventPattern" <changed_files> | grep -L "alreadyProcessed\|existsById\|processed"

# status set directly instead of through a transition method
grep -rn "\.setStatus(\|status = \"" <changed_files>

# unbounded retry
grep -rn "while (true)\|for {}" <changed_files>
```

Cross-check any hit against the full Red Flag list in
`.claude/skills/design/references/distributed-systems-checklist.md` §33.

## 20. Failure-Scenario Test Coverage [MUST for a distributed/async feature]

Verify tests exist (not just planned) for: duplicate message delivery, out-of-order message,
consumer crash mid-processing, DB commit failure after a message was consumed, message-broker
publish failure, external API timeout, **external API succeeds but the response is lost**
(the highest-value case — see §13), retry exhaustion reaching the DLQ, and replay of an already-
processed event producing no duplicate effect. A distributed feature whose tests only cover the
happy path hasn't actually been tested for the failure modes that make this class of system hard.
