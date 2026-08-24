# Performance Implementation Checklist

Load this during Step 1 (IMPLEMENT) whenever the code has a loop over a query, a list/export
endpoint, a DB transaction, an external call, a cache, or a queue consumer — and always during
Step 3 (VERIFY)'s performance check. It's the stack-agnostic master list; the per-stack checklists
hold the framework-specific slice. Go/Fiber has no dedicated checklist file — use this file
directly for MODE B code. Design-time rationale for each item lives in
`.claude/skills/design/references/performance-checklist.md` — this file is about verifying the
code actually does what was designed, not re-deriving why.

## Priority levels

Same convention as the security checklist: **[MUST]** blocks completion, **[SHOULD]** needs an
explicit reason if skipped, **[MAY]** is workload-dependent.

## 1. Algorithm & N+1 [MUST]

```java
// vulnerable — O(N) DB calls
for (Order o : orders) {
    Customer c = customerRepository.findById(o.getCustomerId());
}
// required — one batch query
Set<Long> ids = orders.stream().map(Order::getCustomerId).collect(toSet());
Map<Long, Customer> byId = customerRepository.findAllById(ids).stream()
    .collect(toMap(Customer::getId, c -> c));
```

Grep for a repository/query call sitting inside a `for`/`while`/`.map`/`.forEach` — it's the single
most common performance regression across every stack.

## 2. API Limits [MUST]

Verify the framework's actual body-size/header-size limit is configured (not left at a huge or
unbounded default) for endpoints accepting arbitrary payloads, and that any array-typed request
field has a max-length check — a batch endpoint accepting an unbounded array is a memory/DoS risk
regardless of auth.

## 3. Pagination [MUST for any list endpoint]

```sql
-- gets slower as the offset grows
SELECT * FROM transactions ORDER BY created_at LIMIT 100 OFFSET 500000
-- required for large/deep datasets
SELECT * FROM transactions WHERE created_at < :cursor ORDER BY created_at DESC LIMIT 100
```

Verify the endpoint actually enforces a **max** page size — a `size` query param that's validated
for type but not clamped to a maximum still lets a client request unbounded rows.

## 4. Database Query Patterns [MUST]

- No query inside a loop (see §1). No `SELECT *`/fetch-all-columns when the DTO only needs a
  subset — verify the actual `select`/`include`/projection matches what's returned.
- N+1 prevention actually applied: `@EntityGraph`/`JOIN FETCH` (Spring), `relations`/
  `leftJoinAndSelect` (TypeORM), `include`/`select` (Prisma) — verify by reading the generated
  query or an actual query-count assertion in a test, not by assuming the annotation is enough.
- Batch operations (`saveAll`/bulk insert) used instead of a loop of single-row writes where the
  workload does more than a handful of rows at once.

## 5. Transaction Scope [MUST]

```java
// vulnerable — holds the DB transaction (and its connection/locks) for the external call's latency
@Transactional
public void process() {
    db.update();
    externalApi.call();   // BAD — DB connection held during a network round-trip
    kafka.send();
    db.update();
}
// required — short, deterministic, DB-only transaction
public void process() {
    var prepared = validateAndPrepare();
    dbTransactionalStep(prepared);      // short @Transactional method, DB only
    externalApi.call();                 // outside the transaction
    kafka.send();                       // outside the transaction
}
```

Verify by reading the actual `@Transactional`/transaction-block boundaries: does anything inside
it do HTTP, blocking Kafka I/O, file I/O, a large computation, or a sleep/retry? Any yes is a
finding — flag it even if the design didn't call it out explicitly, since this is one of the
highest-impact regressions in a banking-style backend (a connection pool exhausts under load
because every request holds a connection through an external call).

## 6. Index Verification [MUST for a new/changed query pattern]

Verify the query's `WHERE`/`ORDER BY` columns are actually covered by an index matching that
column order (composite index order matters — `(tenant_id, status, created_at)` serves a query
filtering both and sorting by the third; `(status, tenant_id)` does not as well). Run `EXPLAIN`/
`EXPLAIN ANALYZE` (or the ORM's query-log equivalent) on a production-critical query before calling
it done — a missing index shows up as a sequential scan.

## 7. Connection Pools & Concurrency [MUST]

Verify DB/HTTP-client/Redis/Kafka pool sizes are explicit config, not framework defaults left
unexamined, and that the design's `instances × pool size ≤ downstream capacity` sizing (if stated)
is what's actually configured. Verify no unbounded thread pool / goroutine spawn:

```go
// vulnerable — unbounded goroutines, one per item, no cap
for _, item := range items {
    go process(item)
}
// required — bounded concurrency
sem := make(chan struct{}, maxConcurrency)
for _, item := range items {
    sem <- struct{}{}
    go func(i Item) { defer func() { <-sem }(); process(i) }(item)
}
```

## 8. Timeout [MUST for every external call]

```go
// vulnerable — no timeout, a hung dependency hangs this call forever
resp, err := http.Get(url)
// required
client := &http.Client{Timeout: 3 * time.Second}
resp, err := client.Get(url)
```

Verify every HTTP client, DB driver, and RPC call in the changed code has an explicit
connect/read/overall timeout configured — check the actual client construction, not just that a
config key exists somewhere unused.

## 9. Retry [MUST if retry logic exists]

Verify retries are bounded, use exponential backoff with jitter, and only retry transient failures
(timeouts, connection errors, 502/503/504) — never 400/401/403/validation errors. A retry loop with
no cap or no backoff is a self-inflicted-DoS risk under a real outage.

## 10. Circuit Breaker / Bulkhead [SHOULD, if the design called for one]

Verify the actual failure-threshold/open-duration config matches what the design specified, and
that a slow/failing dependency's calls are isolated (separate pool/queue) from unrelated features
sharing the same process — a report endpoint's slow external call shouldn't exhaust the thread pool
a payment endpoint needs.

## 11. Cache Implementation [MUST if a cache was designed]

Verify TTL is actually set (a cache write with no expiry is a bug even if it "works" in testing),
and that the invalidation path the design specified is wired on the actual write path — a cache
that's populated but never invalidated on update is a stale-data bug waiting to surface.

## 12. Cache Stampede [SHOULD, for a hot cache key]

Verify the mechanism the design named (single-flight, distributed lock, jittered TTL, or
background refresh) is actually implemented — a naive `if not cached: compute and cache` under
concurrent load lets every concurrent miss hit the backing store simultaneously.

## 13. Serialization / Response Shape [SHOULD]

Verify the endpoint returns a DTO/projection matching what the design specified, not the raw
entity/full object graph — check for a `dangerouslySetInnerHTML`-adjacent smell: a response object
serializing far more than the caller's documented needs.

## 14. Memory & Streaming [MUST]

```python
# vulnerable — loads the entire table into memory
rows = db.query("SELECT * FROM transactions").fetchall()
# required — cursor/batch processing
for batch in db.query("SELECT * FROM transactions").yield_per(1000):
    process(batch)
```

Grep for `findAll()`/`.fetchall()`/`SELECT *`-equivalent with no `LIMIT`/pagination/cursor on a
table that can grow large. For an export/bulk-read endpoint, verify it's implemented as an async
job (not held open on the request thread for minutes) if the design specified that.

## 15. Async Processing [SHOULD, if designed]

Verify the async handoff (queue publish → 202 response → background processing) implements the
idempotency/ordering/retry/duplicate-handling behavior the design specified — an async path that
drops these on the floor trades a performance problem for a correctness one.

## 16. Messaging (Kafka/etc.) [SHOULD, if this code produces/consumes messages]

Verify partition key, batch/linger config, and consumer concurrency match what the design
specified — and that consumer lag is something the deployment actually monitors (see §17).

## 17. Observability [SHOULD]

Verify the code emits latency metrics as a histogram/summary that supports **P95/P99**, not just a
counter/average — an average-only metric hides exactly the tail-latency problem observability
exists to catch. Verify a `traceId`/correlation ID propagates through the call chain for any
request path spanning multiple services.

## 18. Performance Test Coverage [SHOULD, MUST if the design stated an RPS/latency target]

Verify load/stress/spike/soak tests exist matching what the design's Performance Acceptance
Criteria called for — a soak test in particular is the only one that catches a slow memory/
connection/goroutine leak, which a quick load test won't surface.

## 19. Anti-Pattern Grep Sweep [MUST — run these before claiming performance-reviewed]

```bash
# N+1 / query-in-loop smell (adapt per stack — this flags candidates, not certainties)
grep -n -B2 "findById\|\.get(\|SELECT " <changed_files> | grep -B2 "for \|while \|forEach\|\.map("

# unbounded findAll/fetch-all
grep -rn "findAll()\|fetchall()\|SELECT \*" <source_dir>

# missing timeout on an HTTP client construction (spot-check manually — hard to grep reliably)
grep -rn "http.Client{}\|new HttpClient()\|axios.create()" <source_dir>

# unbounded thread/goroutine/executor
grep -rn "newCachedThreadPool\|go func(" <source_dir>
```

Cross-check any hit against the full anti-pattern list in
`.claude/skills/design/references/performance-checklist.md` §25 (N+1, `SELECT *`, `findAll()`,
large `OFFSET`, unbounded list, nested/looped DB query, HTTP call inside a DB transaction, no
timeout, unbounded retry, unbounded thread pool/goroutine, new connection per request, huge JSON
payload, large in-memory collection, synchronous long-running job, missing pagination, missing
index, global lock, hot key/partition, cache stampede, busy-wait/sleep-retry loop).
