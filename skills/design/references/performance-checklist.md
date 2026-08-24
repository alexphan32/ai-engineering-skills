# Performance Design Checklist

Load this when drafting **Section 9 (Performance Design)** of any SDS (MODE B/C/D/E), and skim it
during MODE A design for complexity/memory concerns. It is the stack-agnostic master list — mode
templates hold only the stack-specific slice (which pagination API, which cache annotation). This
file holds the items that are easy to forget because no template section prompts for them, and
the principle behind all of them: **performance-by-design — don't wait for a load test to find
the bottleneck a design review would have caught for free.**

## Priority levels

Same convention as the security checklist: **[MUST]** blocks the SDS from being done, **[SHOULD]**
needs an explicit reason if skipped, **[MAY]** is a recommendation tied to actual workload.

Not every section applies to every feature — a low-traffic admin CRUD screen doesn't need a
circuit breaker design. State "N/A — read-only, low volume, no external dependency" rather than
silently omitting the section, so a reviewer can tell "considered and excluded" from "forgotten."

## 0. Performance Baseline [MUST — answer before designing anything else]

Every new API/feature states, even approximately:

```text
Expected RPS/QPS, concurrent users, peak traffic multiplier
Payload size (typical + max)
Latency target: P95, P99 (not just average)
Error-rate target
External dependency latency budget
```

A design with zero workload assumption can't be judged for the tradeoffs below — pagination size,
cache TTL, connection pool size, and concurrency bounds are all sized *relative to* this baseline,
not from a generic default. If the SRS doesn't state a target, mark
`[PERF TARGET NEEDED — SRS §X.Y or user input]` the same way a missing formula gets flagged in
Section 3 — don't invent a number.

## 1. Algorithm & Complexity [MUST]

Before writing pseudo-code for a processing step, state its time/space complexity. The most common
production incident in this category is the same in every stack:

```text
for (item in items) {
    repository.findById(item.relatedId)   // O(N) DB calls
}
```

Design instead as: fetch all related IDs → one batch query → build an in-memory map → look up from
the map. State explicitly wherever a step could become O(N²)/O(N³) as the dataset grows, and
whether that's acceptable given the Performance Baseline (§0) — "it's fine because N is bounded to
50 by business rule" is a legitimate design statement; "it's fine, I didn't check" is not.

## 2. API Performance [MUST]

- **Request limits**: max request body size, max header size, max query-parameter length, max
  array elements in a batch endpoint — state the numbers, don't leave them at framework defaults
  unexamined.
- **Response limits**: never design an endpoint that can return "all rows" — pagination, filtering,
  sorting, and (if the entity is wide) field selection are part of the endpoint's contract, not an
  optimization to add later.

## 3. Pagination [MUST for any list endpoint over a growing dataset]

Offset pagination (`LIMIT 100 OFFSET 500000`) gets slower as the offset grows because the DB still
scans/skips the offset rows. For a dataset that can grow large or is queried deep, design
cursor/keyset pagination instead (`WHERE id > :after ORDER BY id LIMIT :n`) — state which of the
two this endpoint uses and why. Either way, state: default page size, **max page size** (never
unbounded), and max export size if the endpoint supports bulk export.

## 4. Database Performance [MUST]

- Never design a step that queries inside a loop — see §1's fetch-batch-map pattern.
- Never design `SELECT *`-equivalent (fetch all columns) when the consumer needs a subset — state
  the actual columns/fields needed.
- Every query needs a stated access pattern (which columns filter/sort) so the index in §5 can be
  designed against it, not guessed at implementation time.
- Batch operations (bulk insert/update) where the workload does more than a handful of rows at once.
- **Transaction scope** — the single highest-value rule for a banking-style backend: design the
  transaction boundary to be **short, deterministic, and database-only**. Never design a flow where
  a DB transaction stays open across an external HTTP call, a blocking Kafka publish, a large
  computation, or a sleep/retry:

  ```text
  BEGIN TRANSACTION
  UPDATE account
  HTTP call → Core Banking   ← BAD: holds the DB connection/lock for the call's full latency
  UPDATE transaction
  COMMIT
  ```

  Design instead as: validate → prepare → short DB transaction → commit → async/external step
  outside the transaction (queue, saga step, or a follow-up call after commit). If the feature
  genuinely needs cross-system atomicity, that's a Saga/state-machine design decision to make
  explicitly, not something to leave implicit and hope the transaction stays short.

## 5. Database Index [MUST for any new/changed query pattern]

State the composite index a new query pattern needs, matching filter/sort order — e.g. a query
filtering `tenant_id` + `status` and sorting by `created_at DESC` needs
`(tenant_id, status, created_at)`, not three separate single-column indexes. Don't design indexes
mechanically — note the tradeoff considered: read benefit vs. write overhead, storage, and
cardinality. For a production-critical query, state that `EXPLAIN`/`EXPLAIN ANALYZE` (or the
stack's equivalent) will be checked against the actual query plan before implementation is
considered done — this is a implementation-time verification the SDS should call for, not something
the SDS can satisfy itself.

## 6. Connection Pools [MUST]

State the bound for every pool this feature touches (DB, HTTP client, Redis, Kafka
producer/consumer, thread pool) — never leave a pool at "whatever the default is" for a
performance-critical path. Size it against the deployment topology, not a single instance:

```text
application instances × per-instance pool size ≤ downstream capacity
```

20 pods × 100 DB connections each = 2000 connections the database must be able to accept, even if
each pod only uses a handful concurrently under normal load — state the assumed instance count and
the resulting total when sizing a pool.

## 7. Concurrency / Thread Pool [MUST]

State whether the workload is CPU-bound or I/O-bound, because the right concurrency model differs:
CPU-bound work needs a worker limit near the core count; I/O-bound work can use bounded concurrency
well above that. Never design an unbounded pool (`Executors.newCachedThreadPool()`-equivalent, or a
thread/goroutine spawned per request with no cap) — state queue size, max concurrency, and
rejection policy (reject, block, or shed). Stack-specific traps to call out if relevant: Node.js
blocking the event loop with synchronous CPU work; Go goroutines leaking because a channel is never
drained or a context is never cancelled.

## 8. Timeout [MUST for every external call]

Every call to another service, the database, or an external API needs a stated connect timeout,
read timeout, and overall timeout — "no timeout" means a single slow dependency can exhaust the
caller's threads/connections and take the whole service down with it. Typical shape:
`connect: 500ms, read: 2s, overall: 3s` — the actual numbers come from the Performance Baseline
(§0)'s latency budget, not a copy-pasted default.

## 9. Retry [MUST if any external call retries]

Bounded retries with exponential backoff **and jitter**, retrying only transient failures (network
errors, 502/503/504, timeouts) — never retry on 400/401/403/validation/business-rejection, since
those will fail identically every time and just add load. An unbounded or synchronized retry
(every caller retries at the same interval after a shared dependency blips) can turn a brief outage
into a self-inflicted overload — state the backoff/jitter parameters, not just "retry on failure."

## 10. Circuit Breaker [SHOULD, for a dependency that can degrade]

For a call to a service that can become slow or unavailable, design a circuit breaker
(failure-threshold, slow-call threshold, open duration, half-open probe count) so a struggling
downstream doesn't accumulate blocked callers upstream. State which dependencies get one — not
every call needs it, but every call to a dependency outside this team's control should be
considered.

## 11. Bulkhead [SHOULD, for multiple dependencies sharing resources]

If this feature shares a thread/connection pool with another feature that calls a different,
independently-unreliable dependency, design isolation (separate pools/queues per dependency) so a
slow report/export path can't starve a latency-sensitive payment path of threads or connections.

## 12. Cache [MAY — only with a stated access pattern]

Design a cache only when the access pattern justifies it (read-heavy, tolerant of some staleness).
State: key shape, TTL, eviction trigger, max size, invalidation path, and the consistency
requirement this cache must not violate (e.g. never cache an account balance if the SRS requires
strong consistency there). A cache without a stated invalidation path is a design gap, not a
convenience.

## 13. Cache Stampede [SHOULD, whenever §12 applies to a hot key]

When a cache key expires under concurrent load, every one of those concurrent requests can miss the
cache and hit the DB simultaneously (1000 requests → 1000 DB queries). Design one of:
single-flight/request-coalescing (only one request populates the cache, others wait on it),
a distributed lock around the refill, early/background refresh before expiry, or a jittered TTL so
keys don't all expire at once.

## 14. Serialization [SHOULD]

State the response shape as a DTO/projection, not "serialize the entity" — a wide entity graph
serialized to JSON when the caller needs three fields wastes CPU and payload size on both ends.
Flag any step that repeatedly converts the same data between representations (entity → DTO → entity
→ DTO) as a design smell.

## 15. Memory & Large Data Processing [MUST]

Never design a step that loads an entire large table/collection into memory
(`findAll()`/`SELECT *` with no bound). For anything that can grow large: pagination, streaming, a
DB cursor, or batch processing. For an export or bulk-read operation, design it as an async job
(request → create job → background worker reads by cursor/batch → writes to object storage →
client downloads) rather than holding an HTTP request open for minutes.

## 16. Async Processing [SHOULD, for work that doesn't need a synchronous response]

Design a queue/async handoff (`validate → persist → return 202 → publish → async processing`) for
work the caller doesn't need to wait for — but don't make everything async by default. Whenever
this pattern is chosen, the design must also state: consistency model, message ordering
requirement, retry behavior, duplicate-delivery handling, idempotency, and failure/recovery path.
An async design that doesn't address these is deferring a correctness problem, not solving a
performance one.

## 17. Messaging (Kafka/etc.) Performance [SHOULD, if this feature produces/consumes messages]

State: partition count, consumer concurrency, batch size, linger/batching config, compression, and
which field is the partition key. The partition key choice is a design decision, not an
implementation detail — e.g. `accountId` as the key preserves per-account ordering at the cost of
load distribution across partitions; state which property (ordering vs. even distribution) this
feature actually needs.

## 18. Network [MAY, for cross-service or high-volume calls]

For calls this feature makes to other services: connection reuse/keep-alive (don't design a
new-connection-per-call pattern when the client library supports pooling), compression for large
payloads, and — for internal service-to-service calls — whether REST/JSON or a binary protocol fits
the volume.

## 19. Distributed System Latency [SHOULD, if this feature's request path spans multiple services]

Latency compounds across a synchronous call chain — five hops at 50-100ms each is 300ms+ before any
single hop looks slow in isolation. When designing a multi-hop path, state the per-hop budget and
consider: parallelizing independent calls, caching stable data instead of re-fetching it per-hop,
moving a hop to async where the caller doesn't need it synchronously, or an aggregating API that
collapses several hops into one.

## 20. Concurrency & Race Conditions [MUST for shared mutable state]

This overlaps with the security checklist's Business Security section (§10 there) — a race
condition is simultaneously a correctness bug and a performance/reliability one. Design must name
the mechanism (optimistic lock, pessimistic lock, distributed lock, or a state machine that makes
the race safe by construction) for any resource multiple requests can contend on: account balance,
approval state, inventory count, quota, rate-limit counter. Also consider "hot key"/"hot row" —
if the design concentrates load on a single row or cache key (e.g. a global counter), state whether
that's an acceptable bottleneck or needs sharding.

## 21. Observability [SHOULD]

State which metrics this feature exposes: request latency (**P50/P90/P95/P99 — never just the
average**, since a system with a 50ms average and a 5s P99 still has a real problem for the users
hitting that P99), RPS, error rate, and for anything touching them: DB/cache/queue latency and pool
utilization.

## 22. Distributed Tracing [SHOULD, for a request path spanning multiple services]

State that requests carry a `traceId`/`spanId`/correlation ID through the call chain, so a slow
request can be attributed to the actual bottleneck hop (e.g. "Service A 20ms → Service B 100ms →
DB 800ms" tells you exactly where to look) rather than requiring guesswork.

## 23. Performance Testing [SHOULD, MUST for a feature with a stated RPS/latency target]

The test plan should call for the test types that match this feature's risk: load test (expected
traffic), stress test (find the breaking point), spike test (sudden 10x+ traffic), and soak test
(sustained run — 8h/24h — to catch memory/connection/goroutine leaks and queue accumulation that
only show up over time). Not every feature needs all four; state which apply given §0's baseline.

## 24. Performance Acceptance Criteria [SHOULD, MUST for a feature with a stated RPS/latency target]

Restate §0's baseline as acceptance criteria the implementation must meet before shipping:

```text
P95 < 200ms, P99 < 500ms, RPS >= 500, Error rate < 0.1%
CPU < 70%, Memory stable (no growth under soak), DB CPU < 70%, no connection leak
```

## 25. Anti-Patterns — Red Flags

If any of these appear in the design (even implicitly), stop and redesign: N+1 query, `SELECT *`
without justification, `findAll()`-equivalent on an unbounded table, large `OFFSET` pagination on a
big/deep dataset, nested/looped DB queries, an HTTP call inside a DB transaction, an external call
with no timeout, unbounded retry, unbounded thread/goroutine pool, a new DB/HTTP connection created
per request instead of pooled, an API that can return unbounded payload size, a synchronous
long-running job held on the request thread, a global lock, a hot Redis key or Kafka partition with
no mitigation, a cache design with no stampede protection, and a busy-wait/sleep-retry loop.
