# Distributed Systems & Async Processing Design Checklist

Load this whenever a feature crosses a service boundary, publishes/consumes a message
(Kafka/RabbitMQ/SQS/etc.), runs work asynchronously, or calls an external system (Core Banking,
a payment gateway, another microservice) — for MODE B/D/E this is common; for MODE C it applies
only when the feature does one of those things (most CRUD-on-one-Postgres-DB features don't);
MODE A applies only to the checkpoint/resume angle (§18) for a very large batch job.

This is a different failure mode than the security/performance checklists: those are about a
single request going wrong. This one is about **state going wrong across two systems that don't
share a transaction** — the failure shows up later, intermittently, and usually only under retry,
timeout, duplicate delivery, or a crash mid-flow. That's exactly why it has to be designed up
front rather than patched in after an incident.

## Priority levels

Same convention as the other checklists: **[MUST]** blocks the SDS from being done for a feature
this checklist applies to, **[SHOULD]** needs an explicit reason if skipped, **[MAY]** is a
recommendation. Several items here are elevated to MUST relative to their security/performance
counterparts, because a distributed-data bug (double-spend, lost transaction, stuck state)
doesn't self-correct the way a slow query does — it corrupts data.

## Table of Contents

`0` Answer these before picking any technology · `1` Data Ownership · `2` No Shared-Database
Transactions · `3` Source of Truth · `4` Consistency Classification · `5` Durable Async Processing
· `6` Transactional Outbox · `7` Idempotency · `8` Exactly-Once Business Effect · `9` Message
Ordering · `10` Aggregate Serialization · `11` Distributed Locking · `12` Optimistic Locking ·
`13` State Machine · `14` Saga Pattern · `15` Choreography vs. Orchestration · `16` Retry &
Backoff · `17` Dead Letter Queue · `18` Message Replay · `19` Reconciliation · `20` Unknown
Result & Timeout ≠ Failure · `21` Idempotency Key Propagation · `22` Correlation/Causation
Tracing · `23` Backpressure · `24` Consumer Scaling · `25` Distributed Rate Limiting · `26`
Distributed Cache · `27` Data Partitioning/Sharding · `28` Hot Key/Hot Partition · `29`
Distributed Data Migration · `30` Eventual Consistency & Explicit UX · `31` Read Model/CQRS ·
`32` Invariants · `33` Anti-Patterns · `34` Mandatory Failure-Scenario Tests · `35` Event Schema
& Envelope · `36` Backward Compatibility & Schema Evolution

Jump straight to the referenced `§N` rather than reading serially — most callers arrive here from
another file pointing at a specific section.

## 0. Answer these before picking any technology [MUST]

Don't start a distributed design by asking "Kafka or Redis?" — start by answering, per operation:

```text
1. Which data is the source of truth?
2. Which service owns this data?
3. Does this data need strong consistency, or is eventual consistency acceptable?
4. Does this operation need to be synchronous, or can it be async?
5. What happens if the message is processed twice (duplicate)?
6. What happens if the message is lost?
7. What happens if the service crashes mid-transaction?
8. What happens if the downstream dependency is unavailable?
```

The sequencing matters: **data ownership → transaction boundary → consistency requirement →
async boundary → message boundary → failure boundary → recovery strategy**. Picking a message
broker before answering these just moves the hard questions to implementation time, where they're
more expensive to get right.

## 1. Data Ownership [MUST]

Every business entity has exactly one owning service — that service is the only one allowed to
write its database. Other services reach it through an API, event, or command, never through a
shared table:

```text
correct:                          wrong:
Account Service → Account         Service A ↘
Transaction Service → Transaction              shared DB
Customer Service → Customer       Service B ↗
```

State the owner explicitly for every entity this feature touches, including ones it only reads —
a read-only dependency on another service's data still needs to go through that service's API/
event stream, not a direct query against its database.

## 2. No Shared-Database Distributed Transactions [MUST]

Never design a flow that wraps writes to two different services' databases in one ACID
transaction (`@Transactional` spanning DB A and DB B, or two services sharing a database to fake
atomicity). If the two writes are in different bounded contexts, design the handoff as an event
and use Saga/Outbox/Idempotency/Compensation (§8, §14) instead of trying to force cross-database
atomicity that the infrastructure doesn't actually provide.

## 3. Source of Truth [MUST]

Every important piece of data has exactly one authoritative source — state it explicitly:

```text
Core Banking       → Account Balance = authoritative
Transaction Service → Transaction State = authoritative
```

Never let a cache, read model, or replica be treated as authoritative just because it's more
convenient to query. If a read model/cache exists, the direction is always
`Source of Truth → Event → Read Model → Cache`, never the reverse.

## 4. Consistency Classification [MUST]

Classify every operation as one of:

```text
STRONG    — debit account, approve payment, change account limit
EVENTUAL  — notification, search index, dashboard, reporting, analytics, cache
```

State this explicitly per operation in the SDS. **Never default to eventual consistency because
it's easier to implement** — if the classification is unclear, that's an open question for the
business owner, not a default to pick silently.

## 5. Durable Async Processing [MUST]

A business-critical operation that can be lost if the process crashes must not run on an
in-memory/fire-and-forget mechanism:

```text
avoid for critical work:          use instead:
@Async (Spring)                   a durable queue (Kafka, RabbitMQ, SQS)
go process() (unsupervised)       or a persisted DB job table with a worker that polls it
```

"Fire-and-forget business operation" is a Red Flag (§20) precisely because the operation's
completion becomes unobservable and unrecoverable if the goroutine/thread dies.

## 6. Transactional Outbox [MUST when a DB write and an event publish must be atomic]

`DB commit` and `publish event` are two separate systems — doing them as two sequential steps
creates a window where one succeeds and the other doesn't:

```text
DB commits → Kafka publish fails  → data changed, but no one downstream ever finds out
Kafka publish succeeds → DB commit fails → an event exists for a transaction that never happened
```

Design the Transactional Outbox pattern instead: within the same DB transaction, write the
business update AND an outbox-event row; a separate publisher process reads unpublished outbox
rows and sends them to Kafka, marking them sent only after a successful publish.

```text
BEGIN → business update → insert outbox event → COMMIT → outbox publisher → Kafka
```

## 7. Idempotency [MUST for any consumer of an at-least-once message source]

Assume every message can be delivered more than once. The consumer must be idempotent:

```text
if alreadyProcessed(eventId):
    return
process()
markProcessed(eventId)
```

The important refinement: **the business update and the "mark processed" write should be in the
same transaction** whenever possible — recording "processed" as a separate, non-atomic step
re-opens the exact duplicate-effect window idempotency was supposed to close.

## 8. Exactly-Once Business Effect, Not Exactly-Once Delivery [MUST]

Don't design for exactly-once *delivery* — no real message broker guarantees it end-to-end.
Design for:

```text
at-least-once delivery + idempotent processing + atomic state transition = exactly-once business effect
```

This is the correct target for a Kafka-based flow, and it's achievable; "exactly-once delivery"
as a requirement usually means the design is about to lean on a guarantee the infrastructure
doesn't provide.

## 9. Message Ordering [MUST — state the ordering scope explicitly]

Never assume global ordering. Kafka only guarantees ordering within a partition. State the scope
this feature actually needs:

```text
Ordering scope: Global | Tenant | Account | Transaction | Aggregate
```

If business logic requires `TX1 → TX2 → TX3` for one account to be processed in order, the
partition key must be `accountId` (or equivalent) so all of that account's events land on the
same partition — state the partition key choice and which ordering scope it satisfies.

## 10. Aggregate Serialization [SHOULD]

Serialize processing within the same aggregate (e.g. all events for Account A, processed in
order), but allow different aggregates to process in parallel (Account A, B, C concurrently).
This gets you correctness without a global lock — state which aggregate boundary this feature
serializes on.

## 11. Distributed Locking — Last Resort, Not Default [MUST evaluate alternatives first]

Before reaching for a Redis/Hazelcast/DB/ZooKeeper lock, evaluate in this order:

```text
Can optimistic locking solve this?      (see §12)
Can partition ordering solve this?      (see §9)
Can a database uniqueness constraint solve this?
Can idempotency solve this?             (see §7)
```

If a distributed lock is genuinely needed, the design must state lease timeout, lock owner
identity, renewal strategy, release path, and failure recovery (what happens if the lock holder
crashes without releasing) — "lock forever" with no timeout is a Red Flag (§20).

## 12. Optimistic Locking [SHOULD, prefer over distributed locks for concurrent updates]

For data with concurrent updates, use a version column:

```sql
UPDATE account SET balance = ?, version = version + 1
WHERE id = ? AND version = ?
```

`updated rows = 0` means a concurrent modification happened — the caller must retry or fail
explicitly, not silently proceed as if the update succeeded.

## 13. State Machine [MUST for any entity with a status/lifecycle field]

Every state transition must be validated against an explicit, allowed-transitions definition:

```text
Current State + Command/Event → (validated against allowed transitions) → Result State
```

Never let a consumer set `status = COMPLETED` directly — the transition must go through logic
that checks the current state permits it. Design the full state graph (e.g.
`PENDING → QUEUED → PROCESSING → COMPLETED`, with `PROCESSING → RETRYING → PROCESSING` and a
terminal `RETRYING → FAILED`) as part of the SDS, not something the implementer infers.

## 14. Saga Pattern [MUST for a business transaction spanning multiple services]

A multi-step flow across services (e.g. Reserve → Debit → Notify) should not attempt a
distributed ACID transaction. Design it as a Saga: each step has a defined forward action AND
compensation, so a failure partway through can be unwound:

```text
Step 1 → Step 2 → Step 3 (fails)
                     ↓
              Compensate Step 2
                     ↓
              Compensate Step 1
```

Every Saga must define: forward action, compensation, retry policy, timeout, final state, and
recovery (what happens if the orchestrator/service crashes mid-saga).

## 15. Choreography vs. Orchestration [MUST — choose deliberately, state why]

```text
Choreography: Service A --event--> Service B --event--> Service C
  + loose coupling
  - hard to see/debug the overall workflow

Orchestration: a Saga Orchestrator directs A, B, C
  + fits complex, multi-step, compensating workflows well
```

For a banking transaction, multi-step approval, or anything needing compensation, prefer
orchestration — the "who's in charge of this workflow" question needs one clear answer, not an
emergent one reconstructed from event logs during an incident.

## 16. Retry & Backoff [MUST]

Classify errors before retrying:

```text
retryable:      timeout, connection failure, temporary 5xx, rate limit, temporary DB failure
non-retryable:  invalid request, business rejection, authorization failure, invalid account, schema error
```

Retries must be bounded, use exponential backoff with jitter, and never retry a non-retryable
error — retrying a 400/401/403/validation/business-rejection wastes calls and can mask the real
problem.

## 17. Dead Letter Queue [MUST for any consumer with retry]

```text
Message → Consumer → Failure → Retry → Retry exhausted → DLQ
```

A DLQ entry must carry enough to act on: `eventId, eventType, payload/reference, source,
partition, offset, retryCount, error, failedAt, correlationId`. A DLQ is not a place to discard
messages — design for monitoring, inspection, replay, and both manual and automated resolution
paths. A consumer with no DLQ (message just disappears after retries exhaust) is a Red Flag (§20).

## 18. Message Replay [SHOULD]

State explicitly whether an event can be safely replayed. Replaying an event must not create a
duplicate business effect — this falls out of idempotency (§7) plus deterministic processing
(the same input always produces the same output, no reliance on wall-clock time or external
state that's since changed). If a message type can't be replayed safely, say so and why.

## 19. Reconciliation [MUST for financial/critical distributed workflows]

Don't trust that Kafka + logs + your own DB mean the distributed system is definitely correct —
design a reconciliation mechanism that periodically compares this service's view of a
transaction against the authoritative external system's view:

```text
System A ↔ System B → Compare → Mismatch → Investigate → Repair
```

E.g. compare Transaction Service's `status`/`amount`/`reference`/`account`/`processing timestamp`
against Core Banking's record. If `internal = COMPLETED` but `Core Banking = UNKNOWN`, that's
exactly the case reconciliation exists to catch — design what happens next (alert, auto-repair,
manual queue), don't leave it undefined.

## 20. Unknown Result & Timeout ≠ Failure [MUST — this is the single most-violated invariant in payment/banking flows]

A call to an external system can succeed on their side while the response is lost on yours:

```text
Backend → Core Banking → Debit
Core Banking: SUCCESS
Backend: TIMEOUT
```

The backend must **not** conclude `FAILED`. The correct intermediate state is `UNKNOWN`, followed
by a status inquiry and/or reconciliation — never a timeout-triggered retry that could double the
effect, and never a timeout-triggered "mark as failed" that could leave a completed real-world
transaction unrecorded. State explicitly, for every external call this feature makes: what state
the caller enters on timeout, and how that state gets resolved (query-status endpoint,
reconciliation job, manual review).

## 21. Distributed Idempotency Key Propagation [MUST for a multi-hop flow]

One idempotency/correlation identity should flow through the whole chain, not get regenerated at
each layer:

```text
Client → API → Transaction → Kafka Event → Consumer → External System
```

State the identifiers this feature carries end-to-end: `idempotencyKey`, `correlationId`,
`transactionId` — and confirm each hop forwards them rather than minting a new, disconnected one.

## 22. Correlation / Causation Tracing [SHOULD]

For any multi-hop flow, state that `traceId`/`correlationId`/`causationId`/`transactionId`
propagate through every hop (HTTP → Service A → Outbox → Kafka → Service B → Core Banking →
Kafka → Service C), so an incident can be traced end-to-end rather than reconstructed from
disconnected logs.

## 23. Backpressure [SHOULD, for a high-throughput consumer]

If producer throughput can exceed consumer throughput, lag grows unboundedly unless designed
against. State the strategy: scale consumers, throttle the producer, batch, pause, or shed load —
and state what's monitored to detect the problem (consumer lag, queue depth, oldest message age).

## 24. Consumer Scaling [SHOULD, for a Kafka-backed consumer]

Consumer parallelism is capped by partition count — adding pods beyond the partition count for a
topic adds no more throughput for that topic. State partition count, consumer concurrency,
per-message processing time, and downstream (DB/API) capacity when sizing consumer scale-out —
"more pods" alone doesn't scale a partitioned topic linearly.

## 25. Distributed Rate Limiting [SHOULD, for a multi-instance deployment]

A per-pod in-memory rate limiter doesn't produce the limit it looks like:

```text
10 pods × 100 req/s/pod (local limiter) = 1000 req/s actual, not 100 req/s
```

If a global limit is actually required, it needs a shared store (Redis, gateway-level limiting,
or a distributed quota service) — state which.

## 26. Distributed Cache [MUST — overlaps with performance checklist §12-13]

Never let a cache become the de facto source of truth for business-critical state without an
architecture that explicitly guarantees it stays correct. State source of truth, TTL,
invalidation, consistency requirement, stampede protection, and hot-key handling for any
distributed cache this feature relies on.

## 27. Data Partitioning / Sharding [SHOULD, for a large dataset]

A shard/partition key choice needs more justification than "it's a convenient ID." State the
query pattern this key needs to serve well, and evaluate hot-partition risk, data distribution,
rebalancing cost, and any cross-shard query or cross-shard transaction this feature would need
(cross-shard transactions are expensive/complex — flag if the design implies one).

## 28. Hot Key / Hot Partition [SHOULD]

A single key/row/partition receiving disproportionate traffic (e.g. one very active account) can
bottleneck even a well-partitioned system. If this feature's access pattern could concentrate
load this way, state the mitigation: a different partition strategy, aggregation, queue
serialization for that key, or a local cache in front of it.

## 29. Distributed Data Migration [SHOULD, for a migration touching a large table]

Never design a migration as a single `ALTER`/`UPDATE` over millions of rows in one transaction.
Design batch/chunk processing with a checkpoint, so a crash mid-migration resumes from the last
checkpoint rather than restarting or leaving the table in an undefined partial state:

```text
0 ── 100k ── 200k ── 300k ── ...   (checkpoint after each chunk; resume from last checkpoint on crash)
```

## 30. Eventual Consistency Needs Explicit UX [MUST when an endpoint returns 202]

If an endpoint accepts a request and processes it asynchronously, the response must say so:

```text
POST /transaction → 202 ACCEPTED, and the client can then observe: QUEUED → PROCESSING → COMPLETED → FAILED
```

Never return `200 SUCCESS` when the actual business operation hasn't completed yet — that's a
lie the client (and any system building on this API) will build incorrect assumptions on top of.

## 31. Read Model / CQRS [MAY, for read-heavy workloads]

If read load justifies a separate read model (`Write Model → Event → Read Model`, e.g.
`Transaction DB → Kafka → Elasticsearch/MongoDB → Query API`), state explicitly that the read
model is eventually consistent, and design its rebuild/replay/reconciliation path — a read model
with no rebuild path can't recover from corruption or a schema change without data loss.

## 32. Invariants — treat as MUST for a banking/financial distributed system

These are elevated above "recommendation" for this class of system, because violating them
corrupts data rather than just degrading performance:

```text
1. Every business-critical entity has a single authoritative owner.
2. Services never directly modify another service's owned database.
3. Every asynchronous business operation has durable state.
4. Consumers are idempotent.
5. Duplicate messages never create duplicate business effects.
6. ACK never occurs before durable successful processing.
7. Every retry policy is bounded.
8. Every distributed workflow defines failure recovery.
9. Every cross-service transaction defines consistency semantics (strong vs. eventual).
10. Strong consistency is never silently replaced by eventual consistency — only with explicit business approval.
11. Every state transition is validated by a state machine or equivalent invariant.
12. Timeout is never automatically treated as business failure.
13. Operations with unknown outcomes support status inquiry or reconciliation.
14. Every critical distributed workflow has a reconciliation mechanism.
15. Every event is traceable through correlationId/transactionId.
16. Event schemas support versioning/evolution.
17. Message ordering requirements are explicitly defined.
18. Distributed locks are never used when idempotency, optimistic locking, or partition ordering would solve the problem.
19. Queues, retries, concurrency, and memory are never unbounded.
20. Long-running distributed operations support recovery after process/node failure.
```

## 33. Anti-Patterns — Red Flags (block, don't just flag)

If any of these appear in a design, stop and redesign — these aren't style preferences, they're
the specific shapes that cause data corruption or silent failure in production:

shared database writes across services; a distributed transaction attempted without an explicit
Saga/Outbox design; a fire-and-forget business operation; an in-memory queue for critical work; an
ACK issued before business commit; infinite retry; retry with no backoff; a consumer with no
idempotency; a consumer with no DLQ; a workflow with no recovery strategy; a design assuming
exactly-once delivery; a design assuming global Kafka ordering; treating timeout as a failed
transaction; an external call inside a long DB transaction; unbounded goroutines/threads; a
distributed lock with no timeout; a cache used as source of truth with no justification; a state
changed with no transition validation; no reconciliation for a financial transaction; no event
versioning; no correlation ID; no handling for duplicate events; no handling for out-of-order
events.

## 34. Mandatory Failure-Scenario Test Cases [MUST include in the test plan]

For a distributed/async feature, the test plan must cover the scenarios that only surface under
failure, not just the happy path: duplicate message, out-of-order message, message lost, consumer
crash, producer crash, DB commit failure, message-broker publish failure, broker unavailable,
consumer unavailable, external API timeout, **external API succeeds but the response is lost**
(this is the single most important case for distributed banking — see §20), external API fails
outright, network partition, concurrent processing of the same aggregate, lock timeout, retry
exhaustion, DLQ delivery, replay, service restart, pod termination, and database failover.

## 35. Event Schema & Envelope [MUST for any published event]

A payload with just the business fields (`{"transactionId": "123"}`) forces every consumer to
guess what kind of event this is, when it happened, and how to trace it back to the request that
caused it. Define the envelope, not just the payload:

```json
{
  "eventId": "uuid — unique per event instance, used for consumer-side dedup",
  "eventType": "TransactionSubmitted",
  "eventVersion": 1,
  "occurredAt": "when the business fact happened, not when it was published",
  "correlationId": "ties this event to the request/flow that caused it",
  "causationId": "the eventId or requestId that directly caused this event (chains for replay/debugging)",
  "producer": "transaction-service",
  "payload": { "...business fields..." }
}
```

State this envelope shape once per feature (or point to a shared/platform-wide envelope schema if
one already exists in the project — don't invent a second envelope shape alongside an existing
one). Every event this feature publishes uses it.

## 36. Backward Compatibility & Schema Evolution [MUST when changing an existing event, API, or DB schema that has active consumers]

Changing a schema is not just "add a field" once something else already depends on it — every
consumer of an event/API/table, or every existing row, is affected in a different way depending
on whether the change is additive or breaking. State, for this change:

- **Compatibility mode**: additive (new optional field, new enum value nobody's switch-cases
  reject) vs. breaking (renamed/removed field, changed type, removed enum value, a new mandatory
  field with no default).
- **Consumer inventory**: who currently reads this event/API/table? A schema change with zero
  named consumers checked is a schema change shipped blind.
- **Version strategy**: if breaking, how do old and new consumers coexist during rollout —
  `eventVersion` bump + dual-publish, API versioning (`/v2/...`), or a DB migration with a
  backfill and a deprecation window for the old column? Don't ship a breaking change with only
  one deploy step and no coexistence period unless every consumer deploys atomically with it
  (rare in a real distributed system).
- **Migration/backfill**: for a DB schema change, state whether existing rows need a backfill
  and whether that backfill runs online (no downtime, no long lock) or requires a maintenance
  window.

A "no consumers yet" answer is valid and shortens this section to one line — the point is stating
it, not assuming it.
