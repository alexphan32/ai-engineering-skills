# SDS Review — 12 Criteria Details

> Loaded during Step 3 VALIDATE. Full criteria definitions with all sub-checks.

`1` Completeness · `2` Clarity & Precision · `3` Consistency · `4` Feasibility (incl. Scale &
Architecture Fit) · `5` Testability · `6` Interface Compatibility · `7` Traceability & Rationale ·
`8` Security & Data Protection · `9` Performance Design · `10` Distributed & Async Design · `11`
Data Integrity · `12` Operations Readiness — plus Severity Classification and Review Priority
Order at the end.

**Shared rule for criteria 8-12**: each links the same checklist `/design` drafts that section
against, so a finding there reads as "the design didn't satisfy its own checklist," not a new
standard imposed after the fact. And for all five: silence on the topic is an omission (flag it,
usually Blocking/High since these are the checks that catch data corruption and production
incidents, not style issues) — an explicit "N/A — reason" is a considered decision (accept it).
Per-criterion notes below only add what's specific to that criterion.

---

## 1. Completeness

**Required Sections:**
- Module Overview (Module Name, ID, Level, Purpose)
- Input Specifications (data format, columns, types, constraints)
- Input Validation Rules (data quality, minimum requirements, outlier handling)
- Output Specifications (output format, columns, naming conventions)
- Processing Logic (algorithms, calculations, transformations)
- Configuration Parameters (with default values)
- Performance Requirements (time/memory constraints, optimization strategies)
- Error Handling Strategy (exception cases, fallback behavior)
- Dependencies (upstream/downstream modules, external libraries)

**Check for Missing:**
- Edge cases not documented
- Assumptions not stated explicitly
- Constraints not clearly defined
- Error scenarios not covered
- A stated Scale Tier (Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed) with a
  one-line reason — `.claude/skills/architecture/references/system-scale-checklist.md` §0. Without it,
  a reviewer can't tell whether a thin Security/Performance/Distributed section is a considered
  scale-fit decision or something forgotten.

## 2. Clarity & Precision

**Language Quality:**
- Terminology consistent (no multiple terms for same concept)
- Technical terms clearly defined
- Ambiguity: avoid "might", "should", "usually" → use "must", "required"
- Concrete examples for complex logic

**Specification Clarity:**
- Data types declared precisely (float32 vs float64, int vs bool)
- Ranges and boundaries defined (>0 vs >=0, 0-100 vs 0-1)
- Formulas in precise mathematical notation
- Code examples (if any) syntactically correct

## 3. Consistency

**Internal Consistency:**
- Output of one section matches input of another
- Naming conventions consistent throughout SDS
- Units consistent (%, decimal, basis points)
- Enums and constants match M-00 Common Definitions

**External Consistency:**
- Matches SRS requirements (every requirement traces to SRS)
- Matches upstream module outputs
- Matches downstream module expectations
- No conflicts with design decisions in other modules

## 4. Feasibility

**Technical Feasibility:**
- Algorithms implementable with current tech stack (pandas, numpy, ta)
- Performance requirements realistic (1M rows in <5s vs <50ms)
- Dependencies available and stable (no experimental libraries)
- Memory constraints feasible with target hardware

**Data Feasibility:**
- Input data requirements can be met (source data has required fields)
- Calculations have sufficient data points (SMA200 needs ≥200 rows)
- Assumptions about data quality realistic

**Scale & Architecture Fit** (a specific angle of feasibility — not "can this be built" but "is
*this much* architecture the right amount for what this feature actually is"):

> Full tiers, decision questions, and the Applicability Matrix:
> `.claude/skills/architecture/references/system-scale-checklist.md`.

- Read the stated Scale Tier and its one-line reason. If none is stated, that's a Completeness gap
  (criterion 1) — note it, then judge section depth against what the *evidence in the SDS itself*
  implies about scale (traffic mentioned, number of services touched, external integrations named).
- **Check for over-engineering**: does the design introduce a message broker/service split/Saga/
  circuit-breaker/formal RTO-RPO for a feature that, per the checklist's 5 decision questions,
  looks like a single-team, single-service, internally-consumed feature with no stated compliance
  requirement? If so, that's unnecessary complexity — flag it as a Medium finding (it doesn't block
  implementation, but it costs real build time and ongoing maintenance for a problem the system
  doesn't have).
- **Check for under-engineering**: does the design answer "yes" to any of the 5 decision questions
  (especially the external-critical-system-integration or multi-team-ownership ones) while still
  reading like a Tier 1 design — thin/absent Distributed & Async Design, no idempotency, no data-
  ownership statement? If so, the tier classification itself is wrong, and the resulting gaps are
  Blocking findings under whichever specific criterion they fall under (8/9/10/11/12) — the tier
  mismatch is the root cause worth calling out explicitly, not just the individual symptom.
- A design that changes tier mid-document (e.g., states Tier 1 but designs a Saga anyway) is
  internally inconsistent — flag it under Consistency (criterion 3) as well.

## 5. Testability

**Test Specification:**
- Each requirement can have a test case written
- Expected outputs defined for sample inputs
- Edge cases enumerated (empty data, single row, NaN values)
- Validation rules have measurable acceptance criteria

**Test Data Requirements:**
- Sample inputs/outputs in SDS (or reference to test data)
- Boundary conditions defined
- Error conditions have expected behaviors

## 6. Interface Compatibility

**Input Interface:**
- Input schema matches upstream output schema
- Required fields provided by upstream
- Data types compatible (no string→float without validation)

**Output Interface:**
- Output schema meets downstream requirements
- Downstream modules don't rely on fields SDS doesn't produce
- Backward compatibility if updating existing module

## 7. Traceability & Rationale

**Requirements Traceability:**
- Each major requirement references SRS section
- Design decisions have rationale (why algorithm X over Y?)
- Trade-offs documented (accuracy vs performance)

**Change History:**
- Version history (if SDS updated)
- Deprecated features/parameters (if any)
- Migration path for breaking changes

## 8. Security & Data Protection

> Full checklist (threat-modeling questions + 21 categories, MUST/SHOULD/MAY):
> `.claude/skills/design/references/security-checklist.md` (Section 7).

**First, classify the module** (from STRUCTURE step): API/full-stack (has endpoints, Server
Actions, controllers, or any external caller) vs. data-pipeline (pure DataFrame/batch transform).

**For an API/full-stack module**, verify Section 7 Security Design actually states:
- **Authentication**: mechanism named (JWT/session/etc.), and if JWT — signature verification,
  `exp`/`iss`/`aud` checks stated, no client-controlled algorithm
- **Authorization**: the full chain (Auth → Role → Permission → Resource ownership → Action) for
  every endpoint that touches another user's data — "requires login" alone is a Blocking gap,
  not a style note; this is the single most common miss
- **Input validation & injection**: untrusted-input boundary named; SQL/NoSQL injection
  prevention stated (parameterized/ORM, never string-concat or raw operator passthrough)
- **Secrets**: sourced from env var/secret manager in every example — a literal credential
  anywhere in the SDS's sample config is itself a finding
- **Business security**: for any state-changing operation on balance/payment/approval —
  concurrency-control mechanism named (lock/optimistic version/distributed lock) AND, for
  transfer-like operations, an idempotency mechanism (`Idempotency-Key` or equivalent)
- **Error handling**: the client-facing error shape can't leak stack trace/SQL/internal paths
- **CORS/CSRF**: the auth style (Bearer vs cookie) is stated along with the matching protection
- **Rate limiting**: stated for auth/OTP/payment/search endpoints, with a page-size cap for
  list endpoints
- **Audit logging**: named for LOGIN/CREATE/UPDATE/DELETE/APPROVE/REJECT/TRANSFER/
  CHANGE_PERMISSION/CHANGE_PASSWORD actions this module performs
- **Security test cases**: the test plan/traceability table includes unauthenticated,
  unauthorized/IDOR, expired/invalid token, replay, rate-limit-exceeded, and — if multi-tenant —
  cross-tenant access

**For a data-pipeline module** (no Security Design section required), verify the SDS still
addresses, even briefly:
- **Secrets**: any credential/API key this module reads comes from env var/secret manager, not
  a literal default in the enums/config file
- **Untrusted input**: if any input column originates outside this project's own upstream
  modules (external API, uploaded file, webhook), §2.3 Validation Rules treats it as untrusted,
  not just type-checked
- **Logging**: if the module handles PII/financial data, the SDS states that debug logging
  won't dump full rows

**Either way**: apply the shared silence-vs-N/A rule above.

## 9. Performance Design

> Full checklist (25 categories, MUST/SHOULD/MAY, performance-by-design principle):
> `.claude/skills/design/references/performance-checklist.md` (Section 9).

**Use the same module-shape classification as criterion 8** (API/full-stack vs. data-pipeline).

**For an API/full-stack module**, verify Section 9 Performance Design actually states:
- **Performance baseline**: expected RPS/QPS, concurrent users, P95/P99 latency target, error-rate
  target — or `[PERF TARGET NEEDED]` if the SRS doesn't specify one. A section with zero workload
  assumption can't be judged for whether its pagination size, cache TTL, or pool sizing make sense.
- **Algorithm/complexity**: any processing step with a query or external call inside a loop is a
  Blocking finding (O(N) DB calls) — the design must show batch-fetch + in-memory map instead
- **Pagination**: default + **max** page size stated for every list endpoint; keyset/cursor
  pagination stated (not offset) for a dataset that can grow large or is queried at deep offsets
- **Database**: query access pattern stated so an index can be designed against it; batch
  operations for bulk workloads
- **Transaction scope**: every DB transaction stated as short/deterministic/DB-only — no external
  HTTP call, blocking Kafka publish, large computation, or sleep/retry inside it. This is the
  single highest-value check for a banking-style backend — flag its absence even if the SDS
  doesn't call out transactions explicitly, since an implicit transaction boundary is itself a gap.
- **Connection pools & concurrency**: pool sizes stated and sized against
  `instances × pool size ≤ downstream capacity`; any concurrency/fan-out bounded, not unbounded
- **Timeout & retry**: every external call states connect/read/overall timeout; any retry states
  bound + exponential backoff + jitter, excluding 4xx/validation errors
- **Cache**: if a cache is designed, TTL/invalidation/eviction stated; if the key is hot, stampede
  mitigation (single-flight, distributed lock, jittered TTL) stated
- **Memory**: no design step that loads an unbounded dataset into memory — pagination, streaming,
  or an async job for bulk export/read
- **Observability**: P95/P99 latency metrics stated as exposed, not just an average/count

**For a data-pipeline module** (no Performance Design section required), verify the SDS still
addresses, even briefly:
- **Complexity**: time/space complexity stated for non-trivial processing steps, flagging any
  step that could become O(N²) as row count grows
- **Memory**: large-input handling (chunking/streaming vs. a single in-memory transform) addressed
  if this module can receive an unusually large input

**Either way**: apply the shared silence-vs-N/A rule above.

## 10. Distributed & Async Design

> Full checklist (34 categories, the 8 architecture-sequencing questions, the 20 MUST invariants,
> Red Flags, mandatory failure-scenario tests):
> `.claude/skills/design/references/distributed-systems-checklist.md` (Section 10).

**Applicability**: this criterion applies whenever the module crosses a service boundary,
publishes/consumes a message (Kafka/queue), runs work asynchronously, or calls an external
system (Core Banking, payment gateway, another microservice). A plain synchronous CRUD module
within one service and one database may state N/A — but confirm that's actually true (does it
really never call anything external?) rather than accepting an unexamined assumption.

**For a module this criterion applies to**, verify the Distributed & Async Design section states:
- **Data ownership & source of truth**: which service owns each entity this module touches
  (including read-only dependencies — those still route through an API/event, never a direct
  cross-service DB read), and which system is authoritative for each important field
- **Consistency classification**: STRONG or EVENTUAL stated per operation — never defaulted to
  EVENTUAL because it's easier; an unstated classification is itself a Blocking gap
- **No shared-database transactions**: any cross-service operation uses Saga/Outbox/Idempotency/
  Compensation, never a single ACID transaction spanning two services' databases
- **Durable async**: any business-critical async operation is backed by a durable queue or
  persisted job — never a bare `@Async`/`go func()` design with no persistence
- **Idempotency**: every consumer of an at-least-once source has a stated dedup mechanism, and
  the idempotency/correlation key is named as propagating through the full chain (client → API →
  event → consumer → external system), not regenerated at each hop
- **Message ordering**: the ordering scope (Global/Tenant/Account/Aggregate) and partition key
  are stated explicitly — never assumed to be global
- **State machine**: any status/lifecycle field has its full allowed-transition graph defined,
  and the design states that only a validated transition (not a direct field write) changes it
- **Saga & compensation**: for a multi-service business transaction, every step has both a
  forward action and a compensation defined, plus retry/timeout/final-state/recovery
- **Retry & DLQ**: retryable vs. non-retryable errors classified; a DLQ defined for any consumer
  with retry, carrying enough fields to triage without re-deriving context
- **Unknown result & timeout ≠ failure**: this is the single most-violated invariant in payment/
  banking flows — verify the design explicitly states that a timeout calling an external system
  transitions to UNKNOWN/PENDING, resolved via status inquiry or reconciliation, never directly
  to FAILED
- **Reconciliation**: for a financial/critical distributed workflow, a reconciliation mechanism
  comparing this service's record against the authoritative external system is defined
- **Correlation tracing**: `traceId`/`correlationId`/`causationId` stated as propagating through
  the full multi-hop flow

**For a data-pipeline module with no external caller**, this section may be N/A, but if the
module runs as a long batch/migration job over a large dataset, verify checkpoint/resume is
addressed (see `design/references/distributed-systems-checklist.md` §18) so a crash mid-run
doesn't require restarting from zero.

**Either way**: apply the shared silence-vs-N/A rule above — here specifically, the failure modes
(double-debit, stuck state, lost transaction) corrupt data, so silence is Blocking, not Medium.

## 11. Data Integrity

> Full checklist (16 categories, MUST/SHOULD/MAY, DB-constraints-as-first-line-of-defense
> principle): `.claude/skills/design/references/data-integrity-checklist.md` (folded into
> Processing Logic/Output Specifications rather than a dedicated numbered section).

**Applicability**: any module that owns persistent state — a new/changed table, collection, or
durable output another system treats as fact.

**For a module this criterion applies to**, verify the design states:
- **DB constraints for stated invariants**: every business rule the SRS/SDS states about a field
  ("amount must be positive," "reference number unique per tenant") names whether it's enforced by
  a DB constraint (`CHECK`/`UNIQUE`/`NOT NULL`), app logic, or both — "app logic only" for a
  financial/uniqueness-critical field is a High-severity gap, not an accepted default
- **Referential integrity**: every FK relationship states its delete/update behavior
  (`RESTRICT`/`CASCADE`/`SET NULL`) deliberately, not left to ORM defaults
- **Duplicate prevention**: a uniqueness requirement is backed by an actual DB uniqueness
  constraint, not just an app-level check-then-insert (which has a race window)
- **Atomicity**: a multi-table write states its transaction boundary (short/DB-only, per the
  Performance criterion) or, if cross-service, the Saga/Outbox design (per the Distributed
  criterion) — never left implicit
- **Lost update on a single DB**: any row multiple requests can update concurrently names a
  concurrency-control mechanism, even outside a distributed context
- **Money**: never designed as a floating-point type — `DECIMAL`/`NUMERIC`/minor-unit integer only
- **Audit trail shape**: for any action `security-checklist.md` §11 requires an audit log for, the
  design states the entry's shape (actor/action/resource/before/after/timestamp/correlation), not
  just "log it" — and states it's stored in a durable audit store, not solely application logs
- **Reconciliation**: a ledger/running-total design states a periodic check against its source rows

**Either way**: apply the shared silence-vs-N/A rule above — invariant-enforcement and
audit-trail-shape gaps are Blocking, since their absence lets bad data enter permanently.

## 12. Operations Readiness

> Full checklist (16 categories, MUST/SHOULD/MAY):
> `.claude/skills/design/references/operations-readiness-checklist.md` (appended alongside Design
> Decisions, or folded into Error Handling/Dependencies/Configuration Parameters).

**Applicability**: any module that deploys as its own service/process (API, worker, consumer —
not a pure library).

**For a module this criterion applies to**, verify the design states:
- **Health checks**: readiness and liveness are distinguished — liveness never depends on a
  downstream dependency, readiness actually checks the dependencies this instance needs
- **Graceful shutdown**: any consumer/worker states its `SIGTERM` sequence (stop accepting → drain
  in-flight → stop consumers → commit offsets → close resources)
- **Structured logging & correlation**: `correlationId`/`traceId` stated as present on every log
  line for this module
- **Observability metrics**: named metrics classified as business vs. technical, with no
  unbounded-cardinality label
- **Configuration discipline**: every new operator-tunable threshold labeled Configuration, not a
  compile-time constant; no environment-name branch standing in for a feature flag; no secret
  outside a secret manager
- **Dependency-chain depth**: the synchronous call depth on this module's critical path is stated
  and considered, not an unexamined number
- **Resource bounds**: every per-request/per-message spawn (goroutine/thread/connection) has a
  stated cap
- **Availability/DR**: an availability/RTO/RPO number is present only when the SRS states one
  (never invented) — and when a target exists, that the backup/restore approach states a tested
  restore, not just "backups run"
- **Data lifecycle**: PII or legally-retained data states a retention period and deletion/
  anonymization path
- **Separation of duties**: a maker-checker/approval design explicitly forbids self-approval

**Either way**: apply the shared silence-vs-N/A rule above — readiness/liveness-conflation, missing
graceful shutdown, and a hardcoded operator-tunable value are the gaps that turn a correct design
into a 3am incident, so treat them as Blocking/High.

---

## Severity Classification

| Severity | When to fix | Examples |
|----------|-------------|----------|
| **Blocking** | Cannot implement, fix immediately | Missing critical sections, contradictory requirements, interface mismatch, infeasible specs, orphan requirements, missing Security/Performance/Distributed Design section on a module that needs one, authorization design that stops at "authenticated" for an endpoint touching another user's data, a processing step designed with a query/call inside a loop, a DB transaction designed to span an external call, a cross-service transaction designed as shared-DB ACID instead of Saga/Outbox, a timeout designed to transition directly to FAILED instead of UNKNOWN, a business invariant/uniqueness requirement with no DB-constraint enforcement point named, money designed as floating point, a readiness probe design that always returns healthy, a maker-checker design that doesn't forbid self-approval |
| **High** | Fix before implementation | Incomplete validation, ambiguous specs, missing error handling, unrealistic perf, inconsistent naming, missing config params, no idempotency/concurrency-control design for a state-changing financial operation, no rate-limit design for auth/payment endpoints, secrets sourced from a literal value in the SDS, no timeout stated for an external call, no max page size on a list endpoint, no performance baseline for a performance-critical API, a Kafka/queue consumer with no idempotency mechanism designed, a status field with no state-machine transition graph, no reconciliation design for a financial distributed workflow, a delete design silent on referencing-row behavior, an audit-log requirement with no before/after/correlation shape, no graceful-shutdown design for a consumer/worker, an operator-tunable value hardcoded as a constant |
| **Medium** | Improve quality | Missing examples, weak traceability, suboptimal algorithms, missing rationale, inconsistent format, missing audit-log design for a sensitive action, CORS/CSRF posture left implicit, no cache-stampede mitigation on a stated hot key, no observability metrics stated, no DLQ field shape specified, ordering scope left implicit, no reconciliation path for a ledger/aggregate value, no data-lifecycle/retention statement for PII, Tier 3 machinery (Saga, circuit breaker, formal RTO/RPO, service split) designed for a feature with no stated Tier 3 signal |
| **Low** | Nice to have | Missing optional sections, formatting, typos, could add diagrams, missing security headers design for a browser-facing route, no distributed-tracing design for a multi-service call path, no stated dependency-chain depth for a shallow synchronous path |

---

## Review Priority Order

1. Blocking issues (Interface mismatch, Contradictory requirements, Infeasible specs, missing/incomplete Security/Performance/Distributed Design on a module that needs one — including a module misclassified as Tier 1 despite answering a Tier 3 decision question, since the resulting thin sections are the same Blocking gap under whichever criterion they fall under)
2. Completeness (Missing critical sections)
3. Security & Data Protection (authorization gaps and business-security gaps are cheap to catch here, expensive to catch after implementation)
4. Data Integrity, for a module owning persistent state (a missing DB constraint or audit-trail shape lets bad data in permanently — this corrupts data the same way a distributed-consistency gap does)
5. Distributed & Async Design, for a module that crosses services/uses messaging (idempotency, unknown-result handling, and state-machine gaps corrupt data — this is not a "nice to have" tier even though it's listed after Security/Performance)
6. Performance Design (N+1 and transaction-scope gaps are the two highest-frequency regressions across every stack this pipeline produces — equally cheap to catch here, equally expensive after a load test)
7. Operations Readiness, for a module deployed as its own service (a readiness/liveness conflation or a missing graceful-shutdown design becomes a production incident on the very first deploy, not a slow-burn quality issue)
8. Clarity (Ambiguous specs leading to wrong implementation)
9. Consistency (Internal conflicts, mismatch with SRS/other modules)
10. Traceability (Orphan requirements, missing SRS references)
11. Testability & Feasibility
