# Code Review — 11 Criteria Details

> Loaded during Step 3 REVIEW. Full criteria definitions with all sub-checks.

---

## 1. Algorithm & Logic

- Verify algorithm correctness
- Detect logic errors, wrong conditions, incomplete handling
- Validate input/output assumptions

## 2. Bug & Edge Case

- Find potential bugs, runtime errors, boundary data errors
- Check edge cases: null/empty, boundary limits, abnormal data, concurrency

**Error Handling:**
- Try/except specific? Avoid bare except
- Error messages have enough debug context?
- Retry logic / circuit breaker when needed?
- Graceful degradation vs fail-fast strategy

**Resource Management:**
- File/DB connections properly closed? (context managers)
- Memory leaks in loops / long-running processes
- Thread pool / connection pool sizing
- Cleanup in finally blocks

**Data Validation:**
- Input validation (type, range, format)
- Output validation (schema consistency)
- Data sanitization before DB storage

## 3. Performance

> **Full checklist with code patterns per stack**: `.claude/skills/implement/references/performance-implementation-checklist.md`. Load it when the file under review has a loop over a query, a list/export endpoint, a DB transaction, an external call, a cache, or a queue consumer — the summary below is what to check on every pass regardless. Principle: performance-by-design — catch the bottleneck in review, not in a production load test.

- Time & memory complexity analysis
- Detect bottlenecks, redundant loops, suboptimal I/O
- Evaluate load capacity at scale

**Database Optimization:**
- **N+1 / query-in-loop**: a repository/query call sitting inside a `for`/`while`/`.map`/`.forEach` is the single most common performance regression — verify it's a batch query + in-memory map instead, not "it's fine because N is usually small" without a stated bound
- Index usage (missing indexes, unused indexes) — matched to the query's actual filter/sort column order, not just "an index exists somewhere on this table"
- Bulk operations vs individual queries
- **Transaction scope**: verify no `@Transactional`/transaction block contains an external HTTP call, a blocking queue publish, a large computation, or a sleep/retry — this is the highest-impact regression for a banking-style backend (a held DB connection during a network round-trip exhausts the pool under load)
- Connection pooling configuration — explicit and sized, not left at framework defaults for a performance-critical path

**Resource Bounds:**
- **Timeout**: every external call (HTTP client, DB driver, RPC) has an explicit connect/read/overall timeout — no timeout means one slow dependency can hang every caller
- **Retry**: bounded, exponential backoff + jitter, transient-errors-only (never retrying 400/401/403/validation) — an unbounded or unjittered retry can turn a blip into a self-inflicted overload
- **Concurrency**: no unbounded thread pool / goroutine-per-item spawn with no cap — verify a bound (semaphore, worker pool, `p-limit`-equivalent) exists for any fan-out over a caller-controlled collection
- **Memory / streaming**: no `findAll()`/`.fetchall()`/`SELECT *`-equivalent loading an entire large table into memory — verify pagination, a cursor, or batch processing for anything that can grow large; an export/bulk-read endpoint should be an async job, not held open on the request thread
- **Cache stampede**: if a cache read exists on a hot key, verify a stampede mitigation (single-flight, distributed lock, jittered TTL, or background refresh) rather than a naive "miss → recompute" that lets every concurrent miss hit the backing store at once
- **Observability**: latency instrumentation (if present) should support P95/P99, not just an average/count — an average-only metric hides tail latency

**Anti-pattern grep sweep** (candidates — verify each hit by hand):
```bash
grep -n -B2 "findById\|\.get(\|SELECT " <file> | grep -B2 "for \|while \|forEach\|\.map("
grep -n "findAll()\|fetchall()\|SELECT \*" <file>
```

## 4. Security

> **Full checklist with vulnerable/secure code patterns per stack**: `.claude/skills/implement/references/security-implementation-checklist.md`. Load it when the file under review touches auth, payments/state-changing operations, file handling, secrets, or external calls — the summary below is what to check on every pass regardless.

- **Authorization, not just authentication**: every non-public function/handler checks role AND resource ownership before acting — verify by reading the actual guard/decorator/check, never assume from a function name or docstring. An endpoint that fetches `resource_id` from the request and returns it without checking `resource.owner == current_user` is an IDOR, and IDOR is the single most common gap between "looks reviewed" and "is reviewed."
- **Injection**: SQL/NoSQL (parameterized queries / ORM binding only — flag any string-concatenated query or client-supplied Mongo operator object), command injection (`shell=True`, `os.system`, unsanitized `subprocess`/`exec.Command` args — flag any shell interpolation of external input)
- **SSRF**: if the code fetches a URL supplied by a request/config value, check for a host allowlist and rejection of loopback/link-local/private-IP/cloud-metadata targets before the request fires
- **File upload/path handling**: extension + MIME + magic-byte checks (not just the declared `Content-Type`), server-generated filenames (never `request.filename` written straight to disk), storage path can't be walked via `../`
- **Secrets**: sourced from env var/secret manager, never a literal — `git grep -iE "(password|secret|api_key|token)\s*=\s*['\"]"` on the changed files as a mechanical check
- **Business security**: for a state-changing operation on balance/payment/approval, verify the concurrency-control mechanism (transaction + row lock, optimistic version check, or distributed lock) is actually applied around the read-modify-write, and that a transfer/payment-like action checks an idempotency key rather than trusting "the client won't double-submit"
- **Error handling / data leaks**: verify the code's error response never lets a stack trace, raw SQL, file path, internal hostname, or dependency version reach the caller — internal detail belongs in the log only
- **Logging security**: no password/token/OTP/full-PII/`Authorization` header in any log statement — `log.info("request=%s", request)` is a smell whenever `request` can carry any of those
- **CORS/CSRF** (if this file defines HTTP handlers): confirm the auth style (Bearer vs cookie) and that the corresponding protection is actually present — no `Access-Control-Allow-Origin: *` combined with credentialed requests
- **Rate limiting**: present on auth/OTP/password-reset/payment/search endpoints if the codebase has a rate-limit mechanism available
- **Dependency security** (CVEs in third-party packages), **cryptography** (weak algorithms — MD5/SHA1/bare-SHA256 for passwords, hardcoded IVs/keys), **race conditions** in shared state
- **Security test coverage**: for any protected/state-changing function reviewed, check whether tests exist for unauthenticated access, unauthorized/IDOR access, expired/invalid token, and — if applicable — replay and rate-limit-exceeded. Their absence is itself a finding (Testing criterion #7), not just a Security one.

## 5. Maintainability & Scalability

This criterion has two distinct halves. The checks below (coupling, cohesion, SRP, layering) are
everyday code-structure problems that show up regardless of scale — a two-file script can violate
SRP just as easily as a distributed system. "Scale & Architecture Fit" further down is a different
question — whether the *amount* of architectural machinery (queues, circuit breakers, service
splits) matches the system's actual scale. Check both; neither substitutes for the other.

- **Single Responsibility**: a function/class handling more than one distinct reason to change
  (validation + business logic + persistence + notification all inline) is harder to test and
  riskier to modify than the same logic split along its natural seams:
  ```python
  # vulnerable — one function owns validation, calculation, persistence, and notification;
  # a change to any one concern risks breaking the others, and none can be tested in isolation
  def process_order(order):
      if not order.items:
          raise ValueError("empty order")
      order.total = sum(i.price for i in order.items)
      db.save(order)
      email.send(order.customer_email, "Order confirmed")

  # required — each concern has its own seam; this function only orchestrates
  def process_order(order):
      validate(order)
      order.total = calculate_total(order)
      order_repository.save(order)
      notifier.notify_order_confirmed(order)
  ```
- **Coupling** (code reaching past another module's public API into its internals) and
  **layering violations** (business/data-access logic embedded directly in a controller/handler,
  or a repository importing a web-framework type) are the same underlying problem as SRP above,
  just at a module/layer boundary instead of a function boundary: a change on one side of the seam
  can silently break the other, and the misplaced logic can't be reused or tested independently
  (a controller that queries the DB itself can't be reused by a scheduled job or CLI entry point;
  reaching into `billing.internal.database` instead of `BillingService` means a change to billing's
  internals breaks a caller with no compiler/type error to catch it).
- **Cohesion**: a class/module bundling unrelated concerns "for convenience" (a `Utils` class
  mixing date formatting, HTTP calls, and price calculation) means a reader can't tell what the
  module is *for*, and a change to one concern requires re-reviewing all the unrelated ones next
  to it.
- Extensibility, testability, readability

**Anti-pattern grep sweep** (candidates — verify each hit by hand; a high count is a signal to
read the function, not an automatic finding):
```bash
# a single function with an unusually high branch count is a common SRP/complexity smell
grep -c "if \|for \|while \|switch \|case " <file>

# code reaching into another module's internal/private namespace instead of its public API
grep -rn "\.internal\.\|_internal\b\|from \.\.\..*internal" <changed_files>

# business/data-access logic embedded directly in a controller/handler
grep -n "SELECT \|INSERT INTO\|UPDATE .* SET" <controller_or_handler_file>
```

**Scale & Architecture Fit** (over-engineering is a maintainability problem too — a distributed
mechanism nobody asked for is one more thing to understand, test, and keep working):

> Full tiers and decision questions: `.claude/skills/architecture/references/system-scale-checklist.md`.

- If this file introduces a message queue/broker call, a circuit breaker, a distributed lock, a
  new inter-service HTTP/RPC call, or a service split — check whether the corresponding SDS
  actually designed it. If no SDS exists or it's silent on this, judge it against the checklist's
  5 decision questions using evidence in the code/project itself (is there already more than one
  deployed service here? does this call an external system of record? is there a stated compliance
  need?). Flag as Medium if the complexity doesn't seem warranted — it costs real maintenance time
  regardless of whether it currently "works."
- The inverse also applies: if the surrounding codebase already shows Tier 3 signals (multiple
  services, an external critical-system integration, a compliance-driven audit table) but this
  function handles a duplicate-message or timeout scenario naively, that's not "keeping it
  simple" — it's the specific gap `distributed-systems-implementation-checklist.md` and
  `data-integrity-implementation-checklist.md` already flag, just now with the scale context that
  explains *why* it matters here and not everywhere.

**API Design Quality:**
- Consistent naming conventions
- RESTful principles (if REST API)
- Versioning strategy
- Backward compatibility

**Monitoring & Observability:**
- Logging levels appropriate (DEBUG/INFO/WARNING/ERROR)
- Metrics/tracing for critical paths
- Structured logging (JSON format)
- Alert thresholds reasonable
- No PII/sensitive data in logs

**Concurrency & Thread Safety:**
- Race conditions in shared state
- Deadlock risks, lock ordering
- Atomic operations when needed

**Configuration Management:**
- Hardcoded values vs environment variables
- Feature flags usage
- Configuration validation on startup

**Dependency Management:**
- Dependency versions pinned correctly
- Circular dependencies
- Unused dependencies

## 6. Documentation & Code Style

- Docstrings, comments, README
- Coding conventions compliance
- Naming consistency

## 7. Testing

- Test coverage for critical paths
- Test case quality (edge cases, mocking)
- Test maintainability and performance

## 8. Compliance & Standards

- Team/project coding standards
- Regulatory compliance (GDPR, PCI-DSS if applicable)
- License compatibility for dependencies

**8.1 Magic numbers check (use Grep, adapt the file extension to the project's stack — `.py`, `.go`, `.ts`, `.java`):**
```bash
grep -n '\b[0-9]\{2,\}\(\.[0-9]*\)\?\b\|\b[0-9]\+\.[0-9]\{2,\}\b' <module_path>/*.<ext>
```
Report any magic number not in enum/constants file.

**8.2 Logic vs SDS check:**
- Find SDS in project SDS directory — if exists → read Output and Processing sections
- Compare function logic with SDS spec
- If SDS not found: note "SDS not found — skip SDS compliance check"

**8.3 Enum/Constants location:**
- Check project CLAUDE.md for enum file mapping per module
- Every magic number must be in the corresponding constants/enum file

**8.4 Forbidden patterns (check project CLAUDE.md):**
- God Modules: Mixing Data + Analysis + Reporting in 1 file
- Circular Dependencies: Module A → B → A
- Hidden Side Effects: Modifying global state or another module's data
- Duplicate Constants: Re-defining constants from shared enums

## 9. Distributed & Async Correctness

> **Full checklist with code patterns per stack**: `.claude/skills/implement/references/distributed-systems-implementation-checklist.md`. Load it when the file under review publishes/consumes a message, calls another service or an external system (Core Banking, payment gateway), or manages an entity with a status/lifecycle field — the summary below is what to check on every pass regardless. This is a different failure mode than criteria 2-4: the bug shows up later, intermittently, only under retry/timeout/duplicate-delivery/crash — which is exactly why it's easy to miss in review and expensive to debug in production.

- **Data ownership**: flag any code in this file that writes to (or queries) a table/collection this service doesn't own — that's a shared-database violation regardless of how it's phrased in code
- **Durable async**: a business-critical operation run via `@Async`/`asyncio.create_task`/an unsupervised background thread with no persistence is a Red Flag — verify it's backed by a durable queue or a persisted job the process can resume after a crash
- **Idempotent consumers**: any message-queue consumer (Kafka, RabbitMQ, SQS) must check whether the message/event ID was already processed before applying its effect, and mark it processed in the same transaction as the business update — not a separate, best-effort write
- **Transactional outbox**: if a DB write and an event publish must be atomic, verify an outbox-table row is written in the same transaction as the business update, and that publishing happens from a separate poller — not an inline publish call sequenced after a commit that can independently fail
- **State machine transitions**: grep for a status/lifecycle field being set directly (`entity.status = ...`, `.setStatus(...)`) instead of through a transition method that validates the current state permits the change — a consumer setting `status = COMPLETED` directly is how "impossible" states end up in production data
- **Unknown result / timeout ≠ failure**: verify a `catch`/`except` on a timeout calling an external system (Core Banking, payment gateway) transitions the record to `UNKNOWN`/`PENDING`, never directly to a terminal failure — the remote side may have already succeeded, and marking it failed risks a duplicate effect on retry
- **Retry classification**: verify retries exclude non-retryable errors (4xx, validation, business rejection) and use bounded attempts with exponential backoff + jitter
- **DLQ**: a consumer with retry but no dead-letter path (message just disappears after retries exhaust) is a Red Flag
- **Reconciliation**: for a financial/critical distributed workflow, verify a reconciliation mechanism exists (or is explicitly out of scope for this file) rather than trusting the local DB/log to be correct
- **Correlation propagation**: verify `correlationId`/`idempotencyKey`/`transactionId` are forwarded through outgoing calls/events rather than regenerated at each hop

## 10. Data Integrity

> **Full checklist with code patterns**: `.claude/skills/implement/references/data-integrity-implementation-checklist.md`. Load it when the file under review writes to a table/collection this service owns — the summary below is what to check on every pass regardless. Design-time rationale: `.claude/skills/design/references/data-integrity-checklist.md`.

- **DB constraints actually exist**: for any invariant/uniqueness the code assumes ("this amount is always positive," "this reference is unique"), check the migration files actually add the matching `CHECK`/`UNIQUE`/`NOT NULL`/`FK` — app-level validation alone is one bypassed code path away from a bad row
- **Duplicate prevention**: flag a check-then-insert pattern (`if not exists(): create()`) with no backing unique constraint — verify instead a real constraint exists and the conflict is caught and turned into a clean business response
- **Multi-table write atomicity**: a business operation touching more than one table/row is wrapped in the shortest transaction that covers exactly those statements, or is an explicit Saga/Outbox design if cross-service
- **Optimistic locking wired, not just modeled**: a version column exists but its "0 rows updated" result is checked and treated as a concurrency conflict, not silently ignored
- **Money**: never `float`/`double`/bare JS `number` — `Decimal`/minor-unit integer only
- **Audit entries**: a write to the audit trail captures actor/before/after/correlation, not a bare log message; ideally written in the same transaction as the business change
- **Reconciliation**: for a ledger/aggregate value, a periodic check against source rows exists if the design called for one

## 11. Operations Readiness

> **Full checklist with code patterns**: `.claude/skills/implement/references/operations-readiness-implementation-checklist.md`. Load it when the file under review is a deployed service, worker, or consumer — the summary below is what to check on every pass regardless. Design-time rationale: `.claude/skills/design/references/operations-readiness-checklist.md`.

- **Health checks**: readiness and liveness handlers are distinct — liveness never calls the DB or another dependency
- **Graceful shutdown**: any consumer/worker traps `SIGTERM`, drains in-flight work with a bounded timeout, then commits offsets/closes resources — not left to the orchestrator's SIGKILL default
- **Structured logging**: log calls on critical paths include `correlationId`/`traceId` from context, not a bare message string
- **Configuration discipline**: a value the design labeled Configuration is read from env/config service, not a hardcoded literal; no `if (environment.equals("prod"))` standing in for a feature flag
- **Resource bounds**: no goroutine/thread/task spawned per request/message with no concurrency cap; every manual resource acquire (connection, file handle, lock) has a guaranteed release on the error path too (context manager/`try-finally`/`defer`)

---

## Severity Classification

| Severity | When to fix | Examples |
|----------|-------------|----------|
| **Critical** | Immediately | SQL injection, data corruption, production crashes, PII leaks, DB transaction holding an external HTTP call under load, a timeout treated as business failure on a payment/transfer path, a consumer with no idempotency check on a financial event, money stored as floating point on a financial path, a uniqueness invariant with no backing DB constraint on a financial/duplicate-sensitive path |
| **High** | Current sprint | Logic errors in core functionality, perf bottlenecks, race conditions, memory leaks, missing auth, N+1 query on a hot path, external call with no timeout, unbounded `findAll()`/`fetchall()` on a growable table, a status field set directly instead of through a validated transition, a business-critical operation running as fire-and-forget async, a check-then-insert with no backing unique constraint, an audit entry with no before/after shape, a liveness probe that depends on a downstream dependency, a goroutine/thread spawned per request/message with no cap |
| **Medium** | 2-3 sprints | Missing error handling, incomplete validation, code smells, missing edge case tests, a retry with no backoff/jitter, no DLQ on a consumer, no reconciliation check on a ledger/aggregate value, a resource acquire with no guaranteed release on the error path |
| **Low** | Backlog | Style inconsistencies, missing docs, optimization opportunities, refactoring suggestions |

---

## Review Priority Order

1. Security & Critical bugs (Critical/High severity)
2. Distributed/async correctness and Data Integrity on financial or state-changing paths (idempotency, unknown-result handling, state machine, missing DB constraints — these corrupt data rather than just degrading performance)
3. Logic errors & Edge cases
4. Critical path performance
5. Operations Readiness on a deployed service/worker (a readiness/liveness mixup or a missing graceful shutdown surfaces on the very first deploy, not gradually)
6. Maintainability & Documentation
