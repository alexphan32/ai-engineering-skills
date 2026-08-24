---
name: review
description: >
  Use when the user requests a review of any file, module, or system — "review file X", "check
  this code", "review SDS M-02", "review kiến trúc hệ thống này", "xem file này có vấn đề gì
  không", "code này đúng chưa", "tìm bug trong file Y", "review PR changes", "audit this module",
  "SDS này đủ chưa", "review design spec", "thiết kế module có vấn đề gì", or "review spec trước
  khi code". Covers implementation code — Python (incl. FastAPI), Go/Fiber, Next.js/TypeScript,
  Spring Boot (Java), NestJS, Rust (Axum/Actix), Angular, React, Android (Kotlin), iOS (Swift),
  Flutter (Dart) — and SDS/design spec `.md` files, auto-detecting which one applies. For a
  whole module/system's architecture or topology rather than one file or SDS, defers to the
  `architecture` skill's UPGRADE mode instead.
---

## OVERVIEW

Systematic review across two modes, auto-detected from the request — CODE (11 criteria: Algorithm,
Bugs, Performance, Security, Maintainability, Documentation, Testing, Compliance, Distributed &
Async Correctness, Data Integrity, Operations Readiness) or SDS (12 criteria: Completeness,
Clarity, Consistency, Feasibility, Testability, Interface, Traceability, Security & Data
Protection, Performance Design, Distributed & Async Design, Data Integrity, Operations Readiness).
No shortcuts in either mode.

**Core principle:** Every finding must state Problem → Consequence → Fix (or, for SDS,
Issue → Criterion → Analysis → Severity → Impact → Suggestion). Generic feedback ("this is slow",
"input specification is incomplete") is not a review.

**Every finding also carries a Confidence tag**: `Confirmed` (traced through the actual
execution path / actual SDS cross-reference to a concrete contradiction) or `Suspected`
(plausible from the pattern, but not traced end-to-end — e.g. "this looks like it could double-
charge under concurrent requests" without having walked the exact race). A hunch reported as
Confirmed wastes the reader's trust the first time it's wrong; reported as Suspected, it still
gets investigated, just correctly weighted.

---

## MODE DETECTION

| Condition | Mode |
|-----------|------|
| File ends with `.py`, `.go`, `.ts`, `.tsx`, or `.java` (or the equivalent for any of `design`'s 12 stacks) | **CODE** |
| File path matches an SDS doc location (e.g. `docs/04-sds/`) | **SDS** |
| Request contains "SDS", "design spec", "module spec" | **SDS** |
| Request contains "code", "function", "implementation" | **CODE** |
| Request is about a module/system's architecture, topology, service boundaries, or coupling — "kiến trúc", "architecture", "module structure", "microservices topology" — with no single file or SDS document named | **Not this skill** — invoke `architecture`, UPGRADE mode |
| No file path in request | `AskUserQuestion`: "Which file would you like to review?" |
| Ambiguous (e.g., README.md) | `AskUserQuestion`: code review or SDS review? |

A request can name a file *and* ask an architecture question about it (e.g. "does this file's
design fit our architecture?") — that's still **CODE** mode, whose "Scale & Architecture Fit"
sub-check (criterion 5) covers file-level coupling/over-engineering. Only route to `architecture`
UPGRADE when the ask is about the system/module as a whole, not one file's internal design.

---

## CODE MODE

For a frontend/mobile file (Angular/React/Android/iOS/Flutter), criteria 9–11 (Distributed &
Async Correctness, Data Integrity, Operations Readiness) are usually N/A — state that explicitly
rather than skipping silently — since a client app rarely owns a message queue, a database, or a
deployed service process; the client-relevant sliver of Security (token storage, XSS/deep-link/
intent validation) and Performance (list virtualization, bundle/app size, image loading, re-render
count) still applies fully.

<HARD-GATE>
Do NOT claim review is complete until:
1. PLAN has been stated — scope, goal, exclusions
2. Each function/method has been reviewed individually (SPLIT done)
3. All 11 criteria have been checked for each function
4. Every finding has: Issue + Analysis + Severity + Impact + Proposal + Confidence (`Confirmed`/`Suspected`)

Do NOT fix any code (Step 5 FIX) until:
5. User has explicitly said "fix it", "go ahead and fix it", or "apply changes"
6. The proposed fix was documented in Step 4 PROPOSE
</HARD-GATE>

**Violating any gate = violating the spirit of the skill.** Common rationalizations — each is a red
flag to stop and verify against, not just a thought to notice:

| Rationalization | Reality |
|---|---|
| "This function is too simple to need a full review" | Simple functions hide edge case bugs (None input, empty list, division by zero). Review anyway. |
| "I'll skip the PLAN step, I know what to review" | Without stated scope, reviews drift. PLAN keeps you focused on what matters. |
| "The issue is obvious, I'll just fix it without proposing" | Fixing without proposing bypasses user approval. Always PROPOSE first, FIX only when asked. |
| "I reviewed the whole file at once, splitting by function is overhead" | Batch reviewing misses issues in function 3 because you were thinking about function 1. Split first. |
| "I'll skip compliance checks, the project doesn't have SDS" | Even without SDS, magic numbers, forbidden patterns, and enum location checks still apply. |
| "This file has no HTTP endpoints, security doesn't apply" | Secrets, injection, logging, and dependency security apply to any code, not just request handlers. |
| Finding zero issues in a file >100 lines, or reporting issues with no severity classification | Both usually mean the review wasn't actually applied per-criterion — re-check before reporting either. |
| "Checked auth, function requires login" without checking authorization too | Authenticated ≠ authorized — role + resource ownership matters; IDOR is invisible if you stop at "is logged in." |
| "This code uses its own message queue/circuit breaker/service call, it's probably thorough so it must be good" | Check whether the SDS actually designed that complexity — undesigned scope creep costs build and maintenance time even when it "looks" careful. |
| "I'm pretty sure this is a bug, I'll report it as-is" | Tag it `Confirmed` only if you traced the actual path to the failure — otherwise `Suspected`. The reader weighs the two differently, and conflating them costs trust the first time a `Confirmed` turns out wrong. |

The domain-specific temptations for N+1, held transactions, consumer idempotency, timeout-as-UNKNOWN,
migration-backed uniqueness, and readiness/shutdown checks are the same ones the Required list
below exists to catch — that list states the check itself rather than restating the excuse for
skipping it.

### Step 1: PLAN — Define review scope

State: scope (file, module, function), goal (correctness/quality/risk), exclusions (what NOT in scope).

### Step 2: SPLIT — List functions to review

List each function/method. Review sequentially — never batch multiple functions into one review pass.

### Step 3: REVIEW — Apply 11 criteria per function

> **Full criteria:** Read `references/code-criteria-details.md`
>
> **Summary:** 1.Algorithm & Logic → 2.Bug & Edge Case → 3.Performance → 4.Security → 5.Maintainability & Scalability (SRP, coupling, layering violations, cohesion — plus Scale & Architecture Fit: does the file's architectural complexity match what the SDS/scale actually calls for; apply **Occam's Razor** — if a simpler design satisfies the same requirement, the extra complexity is the finding, not a style preference) → 6.Documentation & Style → 7.Testing → 8.Compliance & Standards (magic numbers, SDS cross-check, enum location, forbidden patterns) → 9.Distributed & Async Correctness (idempotency, state machine, unknown-result handling, reconciliation — for any function touching a message queue, external service call, or status/lifecycle field) → 10.Data Integrity (DB constraints actually migrated, duplicate prevention via real constraints not check-then-insert, multi-table write atomicity, money never as float, audit-entry shape — for any function writing to a table/collection this service owns) → 11.Operations Readiness (readiness vs. liveness, graceful shutdown wiring, config externalization, bounded per-request resource spawning — for any file that's a deployed service/worker/consumer).
>
> **Critical:** Record Issue → Analysis → Severity → Impact → Confidence (`Confirmed`/`Suspected`)
> for each finding.

### Step 4: PROPOSE — Suggest improvements

Each proposal: Problem → Reason → Impact if not fixed. Prioritize: small changes, clear impact, easy to verify.

### Step 5: FIX — Apply fixes (ONLY when user requests)

Only trigger when user says "fix it", "go ahead and fix it", "apply changes". Fix only what was proposed in Step 4. After fixing: run syntax check + tests.

### Step 6: SUMMARY — Classify and prioritize

> **Output template:** Read `references/code-output-format.md`
>
> Group issues by severity (critical/high/medium/low). List priority fixes. Recommend next steps.

### CODE severity (compact)

| Level | When | Examples |
|-------|------|----------|
| **Critical** | Immediately | SQL injection, data corruption, PII leaks |
| **High** | Current sprint | Logic errors, perf bottlenecks, race conditions |
| **Medium** | 2-3 sprints | Missing error handling, code smells, undesigned complexity (a message broker/circuit breaker/service call/distributed lock the SDS didn't call for, on a feature with no scale signal that warrants it) |
| **Low** | Backlog | Style, missing docs, refactoring suggestions |

> **Full severity definitions:** Read `references/code-criteria-details.md`

### CODE rules

**Forbidden:**
- ❌ Change behavior without being asked
- ❌ Fix unreviewed code
- ❌ Batch multiple functions into one fix
- ❌ Over-engineer (add unnecessary abstractions)
- ❌ Guess when information is missing
- ❌ Accept undesigned architectural complexity (a message queue, circuit breaker, distributed lock, or new service call with no corresponding SDS section) at face value just because it "looks thorough" — check whether the design actually called for it

**Required:**
- ✅ Every change must have a clear reason
- ✅ Priority: safety → correctness → minimality
- ✅ Surface security vulnerabilities first
- ✅ Every finding: Problem → Consequence → Fix direction
- ✅ For any function that returns/mutates a caller-identified resource: verify authorization checks role AND ownership, not just authentication
- ✅ For any state-changing function on balance/payment/approval: verify the concurrency-control/idempotency mechanism is actually applied, not just present elsewhere unused
- ✅ For any loop reviewed: verify it doesn't contain a query/repository call — flag as N+1 if it does
- ✅ For any DB transaction reviewed: verify nothing inside it does HTTP, blocking queue I/O, or a large computation
- ✅ For any external call reviewed: verify an explicit timeout is configured
- ✅ For any message-queue consumer reviewed: verify an idempotency/dedup check exists before the effect is applied
- ✅ For any status/lifecycle field mutation reviewed: verify it goes through a validated transition, not a direct assignment
- ✅ For any external-call timeout handling reviewed: verify it transitions to UNKNOWN/PENDING, not directly to a terminal failure state
- ✅ For any function writing to a table/collection this service owns: verify a business invariant/uniqueness the design named is backed by an actual migration-level constraint, not app logic alone
- ✅ For any monetary field reviewed: verify it's `Decimal`/minor-unit integer, never `float`/`double`
- ✅ For any audit-logged action reviewed: verify the write captures actor/before/after/correlation, not a bare message string
- ✅ For any deployed service/worker/consumer file reviewed: verify readiness and liveness checks are distinct, and any consumer/worker traps `SIGTERM` with a bounded drain
- ✅ For any per-request/per-message spawn reviewed (goroutine/thread/task): verify a concurrency cap exists
- ✅ For any code introducing distributed complexity (a message broker, circuit breaker, distributed lock, new inter-service call): cross-check against the SDS if one exists — flag as Medium if the SDS didn't design it and the file/feature shows no scale signal (see `.claude/skills/architecture/references/system-scale-checklist.md`) that would justify it

---

## SDS MODE

**Core principle:** Catch design issues BEFORE implementation. Interface mismatches caught in SDS review cost minutes; caught in integration testing cost days.

<HARD-GATE>
Do NOT claim review is complete until:
1. UNDERSTAND is done — module context, upstream/downstream dependencies identified
2. STRUCTURE check is done — all required sections verified present/absent
3. All 12 criteria checked against every section — including Security & Data Protection, Performance Design, Distributed & Async Design, Data Integrity, and Operations Readiness — never skipped just because the module "looks like" a plain data-pipeline module with no HTTP surface, low traffic, or a single-service scope
4. TRACE is done — every requirement traced to SRS, every output consumed downstream
5. Readiness assessment is stated: ready / needs revision / incomplete

Do NOT skip prerequisites:
6. SDS file has been read
7. Related SRS has been checked (or noted as "not found")
8. Upstream SDS has been read for interface verification (or noted as "not found")
</HARD-GATE>

**Violating any gate = violating the spirit of the skill.** Common rationalizations — each is a red
flag to stop and verify against, not just a thought to notice:

| Rationalization | Reality |
|---|---|
| "The SDS is short, I can review it without checking upstream modules" | Short SDS can still have interface mismatches. Interface bugs are the #1 source of integration issues. |
| "I'll skip SRS traceability, there's no SRS file" | Note "SRS not found — skip criterion 7". Don't silently skip — the reader needs to know what was and wasn't checked. |
| "This section looks fine, I don't need to deep-read it" | Surface-level review misses contradictions between sections. Cross-check input/output fields across the entire SDS. |
| "Ambiguous specs are a minor issue, the implementer will figure it out" | "May"/"should"/"usually" → each implementer interprets differently → inconsistent implementation. Flag as High. |
| Finding zero issues in a 200+ line SDS, or skipping straight to a readiness assessment | Both usually mean a criterion got skimmed rather than checked — re-pass before reporting. |
| "This module has no API, so the security section probably isn't needed" | Only the Security Design *section requirement* is API-specific — secrets/untrusted-input/logging checks still apply to a pipeline module. |
| "The SDS has Saga/circuit-breaker/Kafka all fully specified, it's probably thorough so it must be good" | Thoroughness isn't free — check the Scale Tier first; Tier 3 machinery on a feature with no Tier 3 signal is over-engineering, and it's a finding too. |

The rest of the domain-specific temptations (JWT-means-authorized, no-perf-target-means-unimportant,
simple-query-means-no-N+1-risk, single-call-means-no-idempotency-needed, timeout-as-FAILED,
prose-is-enough-no-DB-constraint, not-a-service-means-no-ops-readiness, low-traffic-means-Tier-1)
are exactly what the Forbidden list below exists to catch — it states the check itself rather than
restating the excuse for skipping it.

### Step 1: UNDERSTAND — Context and prerequisites

> **Full prerequisites checklist:** Read `references/sds-criteria-details.md`
>
> **Summary:** Read the SDS file. Identify upstream modules → read their SDS for interface verification. Identify downstream consumers. Check related SRS for traceability. Note any missing prerequisite documents explicitly.

### Step 2: STRUCTURE — Verify required sections

Check all 9 required sections: Module Overview, Input Specifications, Input Validation Rules, Output Specifications, Processing Logic, Configuration Parameters, Performance Requirements, Error Handling, Dependencies. Mark each ✅/❌.

**Before judging depth, check for a stated Scale Tier** (Tier 1 MVP / Tier 2 Async-Growing / Tier 3
Enterprise-Distributed, near the top — Architecture Context or a "Scale & Architecture Fit" note).
Its absence is itself a Completeness finding (full definitions/Applicability Matrix:
`.claude/skills/architecture/references/system-scale-checklist.md`). This tier is the lens for
every judgment below — a thin Security/Performance/Distributed section is correct for a justified
Tier 1, Blocking for a Tier 3 system. Don't apply one fixed depth regardless of the stated tier.

Then determine the module's shape — it changes what "required" means for Security, Performance,
and Distributed & Async:
- **API/full-stack module** (endpoints, Server Actions, controllers, or handlers — anything with an
  external caller, not just an upstream module): **Security Design** AND **Performance Design**
  sections are both required; either missing is a Blocking finding, same tier as a missing Error
  Handling section. **Distributed & Async Design** is additionally required if the module crosses
  a service boundary, publishes/consumes a message, runs anything async, or calls an external
  system (Core Banking, payment gateway) — otherwise it may state N/A.
- **Data-pipeline module** (pure DataFrame/batch transform, no external caller): dedicated
  Security/Performance/Distributed Design sections are optional, but the SDS must still address
  secrets/untrusted-input/logging (criterion 8), complexity/memory (criterion 9), and
  checkpoint/resume for a large batch job (criterion 10) at a minimum — skip the section, never
  the underlying checks.

Two more shape questions, independent of the API/pipeline split above:
- **Does this module own persistent state** (any new/changed table, collection, or durable
  output)? If yes, criterion 11 (Data Integrity) applies — its checks (DB constraints,
  referential integrity, audit-trail shape) can live in Processing Logic/Output Specifications
  rather than a dedicated section.
- **Does this module deploy as its own service/process** (API, worker, consumer — not a pure
  library)? If yes, criterion 12 (Operations Readiness) applies — its checks can live in Error
  Handling/Dependencies/Configuration Parameters, or an appended "Operations Readiness" section
  alongside Design Decisions.

### Step 3: VALIDATE — Apply 12 criteria

> **Full criteria:** Read `references/sds-criteria-details.md`
>
> **Summary:** 1.Completeness (all sections, edge cases, assumptions, a stated Scale Tier) → 2.Clarity (terminology, precision, no "may") → 3.Consistency (internal + external, matches SRS + upstream/downstream) → 4.Feasibility (implementable with tech stack, data available, and — the scale-fit judgment — the architecture/checklist depth chosen is consistent with the stated Scale Tier per `.claude/skills/architecture/references/system-scale-checklist.md` §4's Applicability Matrix: neither Tier 3 machinery on an unjustified Tier 1 feature, nor Tier 1 thinness on a feature that clearly answers a Tier 3 signal; apply **Occam's Razor** — if a simpler design satisfies the same tier's requirements, the extra machinery is the finding) → 5.Testability (every requirement has test case, edge cases enumerated) → 6.Interface (input/output schema compatibility) → 7.Traceability (every requirement traces to SRS, design rationale documented) → 8.Security & Data Protection (authN/authZ chain, injection/SSRF/secrets, business security for state-changing ops, mandatory security test cases — full: `.claude/skills/design/references/security-checklist.md`) → 9.Performance Design (performance baseline, N+1/complexity, transaction scope, timeout/retry/connection pools, cache stampede, memory/streaming, observability — full: `.claude/skills/design/references/performance-checklist.md`) → 10.Distributed & Async Design (data ownership, source of truth, consistency classification, idempotency, state machine, Saga/compensation, unknown-result handling, reconciliation — full: `.claude/skills/design/references/distributed-systems-checklist.md`) → 11.Data Integrity (DB constraints as first-line enforcement, referential integrity, duplicate prevention, atomicity, lost-update on a single DB, audit-trail shape, reconciliation for non-distributed data — full: `.claude/skills/design/references/data-integrity-checklist.md`) → 12.Operations Readiness (structured logging/correlation, business vs. technical metrics, health checks, graceful shutdown, config vs. secret vs. feature-flag, dependency-chain depth, resource bounds, availability/DR only when the SRS states a target, data lifecycle, separation of duties — full: `.claude/skills/design/references/operations-readiness-checklist.md`) — same checklists `/design` drafts against.
>
> **Critical:** Record Issue → Criterion → Analysis → Severity → Impact → Suggestion → Confidence
> (`Confirmed`/`Suspected`) for each finding.

### Step 4: TRACE — Verify traceability

Check SRS coverage (X/Y requirements traced), orphan requirements (no SRS reference), unused outputs (no downstream consumer), missing requirements (SRS not covered in SDS).

### Step 5: SUMMARY — Assess readiness

> **Output template:** Read `references/sds-output-format.md`
>
> Group issues by severity (blocking/high/medium/low) and by criterion. State readiness: ready to implement / needs revision / incomplete. List blocking issues first.
>
> If the SDS has its own "Implementation Readiness" section (`/design` writes
> READY/PARTIALLY_READY/BLOCKED), cross-check it against your own findings — a self-declared READY
> with a blocking issue you just found is itself a finding (the gate is stale), and a self-declared
> BLOCKED/PARTIALLY_READY constrains what "ready to implement" can mean here: don't call the
> document ready to implement if it says otherwise.

### SDS severity (compact)

| Level | When | Examples |
|-------|------|----------|
| **Blocking** | Cannot implement | Missing critical sections, contradictory requirements, interface mismatch, infeasible specs, missing Security/Performance/Distributed Design section on a module that needs one, no authorization spec for an endpoint that returns/mutates another user's data, a query/call designed inside a loop, a distributed transaction designed as shared-DB ACID instead of Saga/Outbox, a timeout on an external call designed to transition directly to FAILED, a business invariant/uniqueness requirement with no DB-constraint enforcement point named, money represented as floating point, a readiness probe design that always returns healthy, an approval workflow whose authorization design doesn't forbid self-approval |
| **High** | Fix before implement | Incomplete validation, ambiguous specs, missing error handling, inconsistent naming, no idempotency/concurrency-control design for a state-changing financial operation, secrets sourced from a literal in the SDS's example config, a DB transaction spanning an external call, no timeout stated for an external call, no max page size on a list endpoint, a Kafka/queue consumer designed with no idempotency mechanism, a status field with no state-machine transition rules, no reconciliation design for a financial distributed workflow, a delete design silent on referencing-row behavior, an audit-log requirement with no before/after/correlation shape stated, no graceful-shutdown design for a consumer/worker, an operator-tunable value designed as a hardcoded constant |
| **Medium** | Improve quality | Missing examples, weak traceability, suboptimal algorithms, missing rationale, Tier 3 machinery (Saga, circuit breaker, formal RTO/RPO) designed for a feature with no stated Tier 3 signal |
| **Low** | Nice to have | Missing optional sections, formatting, typos |

A missing Scale Tier statement is **Blocking** only when it leaves the reviewer unable to judge
whether a thin Security/Performance/Distributed section is a considered decision or a gap —
otherwise it's a Completeness finding at whatever severity the actual downstream gap warrants
(e.g. a genuinely Tier 3 feature with no distributed design and no tier statement is Blocking via
the Distributed criterion, regardless of how the tier question is framed).

> **Full severity definitions:** Read `references/sds-criteria-details.md`

### SDS rules

**Forbidden:**
- ❌ Don't propose requirement changes without clear rationale
- ❌ Don't review SDS without reading SRS and related modules
- ❌ Don't assume implementation details (if SDS doesn't specify, that's an issue)
- ❌ Don't accept ambiguous specs ("may", "usually", "should")
- ❌ Don't skip interface compatibility checks
- ❌ Don't skip the Security criterion because the module "is just a data pipeline" — secrets, untrusted-input handling, and logging safety still apply; only the depth changes
- ❌ Don't accept an authorization design that stops at "user is authenticated" for an endpoint that touches another user's data — that's a Blocking finding, not a style note
- ❌ Don't accept a state-changing financial/transfer design with no stated concurrency-control or idempotency mechanism
- ❌ Don't skip the Performance criterion because the module "looks low-traffic" — a missing performance baseline is a finding, not an assumption to fill in silently
- ❌ Don't accept a processing step designed with a query/call inside a loop, or a DB transaction that spans an external call — both are Blocking/High regardless of how "unlikely" the load seems today
- ❌ Don't accept a design that writes directly to another service's owned database, or that wraps a cross-service operation in a single ACID transaction instead of Saga/Outbox/Idempotency/Compensation
- ❌ Don't accept a design where a timeout on an external call transitions directly to a terminal failure state — the correct design is an UNKNOWN/PENDING intermediate state resolved by status inquiry or reconciliation
- ❌ Don't accept a Kafka/queue consumer design with no idempotency mechanism, or a status/lifecycle field with no defined allowed-transition graph
- ❌ Don't accept a business invariant or uniqueness requirement stated only in prose with no DB-constraint or app-enforcement point named
- ❌ Don't accept money designed as a floating-point field
- ❌ Don't accept an audit-log requirement satisfied by "application logs" with no before/after/actor/correlation shape stated
- ❌ Don't accept a readiness probe design that always returns healthy, or a liveness design that depends on a downstream dependency
- ❌ Don't accept an operator-tunable threshold designed as a hardcoded/compile-time constant
- ❌ Don't accept an invented availability/RTO/RPO number with no SRS or user-stated source
- ❌ Don't accept an approval/maker-checker design whose authorization check doesn't explicitly forbid the maker approving their own resource
- ❌ Don't accept a design with no stated Scale Tier when the section depths look inconsistent (some sections fully built, others silently thin) — the reader needs to know if that's deliberate
- ❌ Don't flag a thin Security/Performance/Distributed section as a gap without first checking whether the stated Scale Tier's Applicability Matrix (`system-scale-checklist.md` §4) actually calls for that depth — a justified Tier 1 baseline is not the same finding as an unjustified omission
- ❌ Don't accept a Tier 1 classification for a feature that clearly answers a Tier 3 signal (external critical-system integration, multi-team independent deployment, a stated compliance requirement) just because current traffic is low

**Required:**
- ✅ Cross-check with SRS: every requirement must trace to SRS
- ✅ Cross-check with modules: input/output schemas must match upstream/downstream
- ✅ Identify blocking issues first (interface mismatch, contradictions)
- ✅ Verify testability: every requirement must have a way to test
- ✅ Check feasibility: requirements must be implementable with tech stack
- ✅ Provide constructive suggestions: not just "missing" but suggest what to add
- ✅ Assess readiness clearly: ready to implement / needs revision / incomplete
- ✅ For API/full-stack modules: verify the Security Design section covers the `[MUST]` items in `.claude/skills/design/references/security-checklist.md` (auth, authorization chain, injection, secrets, business security, CORS/CSRF, mandatory security test cases) — flag a missing MUST as Blocking, a missing SHOULD as High/Medium depending on impact
- ✅ For data-pipeline modules: verify secrets sourcing, untrusted external input validation, and logging safety are addressed or explicitly noted N/A
- ✅ For API/full-stack modules: verify the Performance Design section covers the `[MUST]` items in `.claude/skills/design/references/performance-checklist.md` (performance baseline, no query-in-loop, pagination with a max page size, short/DB-only transactions, timeouts on external calls, bounded connection pools/concurrency) — flag a missing MUST as Blocking
- ✅ For data-pipeline modules: verify time/space complexity is stated for non-trivial processing steps and that large-input handling (chunking/streaming) is addressed or explicitly noted N/A
- ✅ For a module that crosses a service boundary, uses messaging, or calls an external system: verify the Distributed & Async Design section covers the `[MUST]` items in `.claude/skills/design/references/distributed-systems-checklist.md` (data ownership, consistency classification, idempotency, state machine, unknown-result handling) — flag a missing MUST as Blocking
- ✅ For a synchronous, single-service module with no external dependency: confirm it's explicitly marked N/A for Distributed & Async Design rather than silently missing
- ✅ For any module owning persistent state: verify the `[MUST]` items in `.claude/skills/design/references/data-integrity-checklist.md` (DB constraints for stated invariants, referential-integrity behavior per FK, real uniqueness constraint for duplicate prevention, atomicity of multi-table writes, no money as float, audit-entry shape) are satisfied — flag a missing MUST as Blocking
- ✅ For any module deployed as its own service/process: verify the `[MUST]` items in `.claude/skills/design/references/operations-readiness-checklist.md` (readiness/liveness distinguished, graceful-shutdown sequence for consumers/workers, config vs. secret vs. feature-flag labeled correctly, per-request/per-message resource bound stated) are satisfied; verify an availability/RTO/RPO number is never invented (mark `[AVAILABILITY TARGET NEEDED]` if the SRS is silent) — flag a missing MUST as Blocking
- ✅ For a maker-checker/approval workflow: verify the authorization design explicitly forbids the maker approving their own resource, not just a role check
- ✅ Verify the SDS states a Scale Tier with a one-line reason, and that the depth of the Security/Performance/Distributed/Data-Integrity/Operations-Readiness sections is consistent with that tier's Applicability Matrix — flag both directions: unjustified Tier 3 machinery on a small feature (Medium), and Tier 1 thinness on a feature answering a Tier 3 signal (Blocking, via whichever specific checklist the gap falls under)

---

## REFERENCE

| File | Content | Load when |
|------|---------|-----------|
| `references/code-criteria-details.md` | Full 11 CODE criteria with sub-checks, severity definitions, priority order | CODE Step 3 REVIEW |
| `references/code-output-format.md` | Full CODE output template + good vs bad examples | CODE Step 6 SUMMARY |
| `references/sds-criteria-details.md` | Full 12 SDS criteria with sub-checks, severity definitions, priority order | SDS Step 3 VALIDATE |
| `references/sds-output-format.md` | Full SDS output template + good vs bad examples | SDS Step 5 SUMMARY |
