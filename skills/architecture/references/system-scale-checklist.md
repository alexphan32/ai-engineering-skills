# System Scale & Architecture Fit Checklist

Owned by the `architecture` skill and shared across the lifecycle — `design` loads it during
ANALYZE before drafting Security/Performance/Distributed/Data-Integrity/Operations-Readiness
sections, and `architecture` loads it first in MODE: SELECT/UPGRADE, before choosing any
architecture pattern (`architecture-selection.md`) at all. `spec`, `implement`, `test`, `review`,
and `operate` all reference this same file rather than re-deriving tiers on their own — one
classification, read everywhere it's needed.

Every checklist `design` owns describes what a mature, high-stakes system needs — applying all of
them at full strength to a 20-user internal tool is over-engineering (burning time on problems the
system doesn't have), while treating a system that already integrates with an external system of
record as a weekend MVP is the opposite mistake that causes real incidents. This checklist makes
that judgment a stated decision instead of an unexamined default in either direction.

## Priority levels

Same convention as the other checklists: **[MUST]** blocks the SDS from being done, **[SHOULD]**
needs an explicit reason if skipped.

## 0. Classify Before Designing [MUST]

Answer these during ANALYZE, honestly rather than answering the question the design *wants* to
have been asked:

```text
1. How many teams/services will independently deploy code touching this feature — one, or more than one?
2. Does any part of this feature's workflow need to run outside the request/response cycle that triggers it
   (email/SMS, report/export generation, a slow third-party call, a scheduled job, a retried webhook)?
3. Does this feature call, or get called by, a system this team doesn't control, where a wrong
   assumption about its failure mode would have real financial/legal/safety consequences?
4. Does the SRS or the business state a compliance, audit, or availability requirement — or is
   this explicitly a pilot/internal/low-stakes tool?
5. Is the expected scale (users, RPS, data volume) an order of magnitude that could exhaust a
   single well-configured instance/database, or is that a hypothetical concern with no current signal?
```

A "no" to all five means **Tier 1**. A "yes" to #3 in a regulated or financial context means
**Tier 3** regardless of current traffic — the failure-mode *consequence* is what matters, not
request volume. A "yes" to #2 alone, with "no" everywhere else, means **Tier 2**.

**Check the SRS before asking the user again.** If `/spec` produced this feature's SRS, questions
3 and 4 are pure business facts it should already have captured — the Dependencies table's "Team
Controls It?" column answers #3, and NFR-04 (Compliance & Availability) answers #4. Read those
sections first; only fall back to asking the user if the SRS predates this convention or is
genuinely silent on them.

## 1. Tier 1 — MVP / Small System

**Signals**: one team/developer; validating a hypothesis or serving an internal/limited audience;
low expected load (tens to low thousands of users, no sustained high RPS); one deployable service
is genuinely enough; no other team needs to own part of this data independently yet; a failure's
impact is inconvenience, not financial/regulatory/safety harm.

**Architecture fit**: a monolith — or a "modular monolith" with clear internal module boundaries
inside one deployable — is the *correct* choice here, not a compromise to fix later. Single
database. Synchronous request/response for everything the user waits on. No message broker, no
distributed lock, no Saga, no service mesh.

**What still applies regardless of tier** (never skip these — they're not scale-dependent):
authentication on anything not meant to be public, basic input validation, no SQL injection, no
plaintext passwords or secrets in source control, error handling that fails clean rather than
crashing the process, and a DB constraint for the handful of invariants the business genuinely
cannot tolerate being violated (e.g. an email-uniqueness constraint). See the Applicability Matrix
(§4) for exactly which items from each checklist these are.

**What's explicitly deferred** (not designed now, but not forgotten — see Graduation Triggers §5):
circuit breakers, bulkhead isolation, distributed tracing, Saga/Outbox, a formal SLA/RTO/RPO,
dedicated audit-trail infrastructure beyond application logs for non-regulated actions, cache
stampede protection (no cache needed yet), and connection-pool sizing math (framework defaults are
fine at this scale — revisit once a real load number exists).

## 2. Tier 2 — Growing System / Background Jobs & Async

**Signals**: the system has passed initial validation and has real, growing usage; a business
action now needs to happen *outside* the request/response cycle — send an email/SMS, generate a
report/export, call a slow third-party API, retry a flaky webhook, or run something on a schedule.
**The trigger for this tier is a workflow need, not a traffic number** — a 50-user internal tool
that needs to email a PDF report is already Tier 2 for that one feature. Typically still one
primary service/team, possibly with a worker process or scheduled-job runner alongside the main API.

**Architecture fit**: keep the modular monolith for the core domain. Add **one** narrowly-scoped
mechanism for async work — a durable job queue (a DB-backed job table with a worker, or a
lightweight queue like BullMQ/Sidekiq/SQS) — not a general-purpose event bus. A background job
needs three things designed explicitly:

```text
Durable   — the job survives a process restart (persisted, not in-memory)
Idempotent — the job can be safely retried without a duplicate effect
Visible   — a job that keeps failing is visible somewhere (a status field, a dashboard, an alert),
            never silently dropped
```

This is where `distributed-systems-checklist.md`'s idempotency (§7) and DLQ (§17) items start to
matter for the async mechanism itself — but NOT its cross-service data-ownership (§1) or Saga
(§14) items, since there's still one system of record and one team.

## 3. Tier 3 — Enterprise / Distributed System

**Signals**: more than one team owns and independently deploys part of the system; the system
integrates with an external system of record it doesn't control (Core Banking, a payment gateway,
another company's API) where a wrong assumption about that integration's failure mode has real
financial/legal/safety consequences; a compliance/audit/availability requirement is stated (or
implied by the domain — banking, healthcare, payments); traffic or data volume makes a single
database/instance a real constraint, not a hypothetical one.

**Architecture fit**: this is where crossing a service boundary, publishing/consuming real
messages, and the full `distributed-systems-checklist.md` / `data-integrity-checklist.md` /
`operations-readiness-checklist.md` machinery earns its cost. Multiple services, each with a clear
data-ownership boundary; async communication via a real broker where cross-service consistency
matters; formal availability/RTO/RPO targets when the business states them; dedicated
observability/audit infrastructure.

## 4. Applicability Matrix — How Much of Each Checklist to Apply

| Checklist (owned by `design`) | Tier 1 (MVP) | Tier 2 (Async/Growing) | Tier 3 (Enterprise/Distributed) |
|---|---|---|---|
| `.claude/skills/design/references/security-checklist.md` | Baseline only: §1 Auth, §2 Authorization, §3 Input Validation, §4 Injection, §7 Secrets, §9 API basics (auth+authz stated, no unbounded page size), §11 no-sensitive-data-in-logs | Tier 1 baseline + §10 Business Security (idempotency/concurrency) for any state-changing job, rate limiting for anything public-facing | Full — every `[MUST]` applies |
| `.claude/skills/design/references/performance-checklist.md` | Baseline only: §1 algorithm sanity (no query-in-loop), §4 basic DB access pattern, §8 timeouts on any external call | Tier 1 baseline + §9 retry/backoff for job calls, §16 async processing design | Full — every `[MUST]` applies |
| `.claude/skills/design/references/distributed-systems-checklist.md` | N/A | Applies only to the async mechanism itself: §5 durable async, §7 idempotency, §17 DLQ | Full — every `[MUST]` applies |
| `.claude/skills/design/references/data-integrity-checklist.md` | Baseline only: §1 DB constraints for the 1-2 invariants that truly matter, §6 invariant validation before persist, §8 money never as float | Tier 1 baseline + §12 idempotency at the data layer for any job that can retry | Full — every `[MUST]` applies |
| `.claude/skills/design/references/operations-readiness-checklist.md` | N/A, or just §6 config-vs-secret hygiene | §1 structured logging, §10 resource bounds for the worker process | Full — every `[MUST]` applies |

**State this classification explicitly in the SDS** — in Architecture Context (design step 3) or
a short "Scale & Architecture Fit" note near the top. A reviewer must be able to see *why*
Sections 7/9/10 (and the Data Integrity/Operations Readiness sections) are thin or N/A, rather
than wondering whether they were simply forgotten.

## 5. Graduation Triggers [MUST state, for a Tier 1 or Tier 2 SDS]

A tier classification isn't permanent — state the specific signal that would mean re-evaluating it,
so "we're small now" doesn't quietly outlive its truth:

```text
Tier 1 → Tier 2: the first time a request handler needs to do something slow/unreliable that the
                 user shouldn't wait for synchronously, or something that needs to run on a schedule.
Tier 2 → Tier 3: the first time two independently-deployed services need to agree on the state of
                 the same business entity, or an external system's failure mode (timeout, partial
                 success) can corrupt this system's data if mishandled.
```

Naming the trigger costs one sentence and turns "we'll deal with it when we get there" into an
actual, checkable condition instead of a hope.

## 6. Anti-Patterns — Both Directions

**Over-engineering** (the less-discussed failure mode here, but just as real and just as costly):
introducing microservices before more than one team needs independent deployability; adding
Kafka/a message broker for a single background email send that a job queue handles fine; designing
a Saga for a workflow that's entirely within one database and one transaction; writing a circuit
breaker for a dependency that's a static config file; demanding a formal RTO/RPO for an internal
tool nobody will notice is down for an hour; building a generic plugin/abstraction layer for a
feature that has exactly one implementation and no stated plan for a second.

**Under-engineering** (the failure mode the other checklists already exist to catch — restated
here as the flip side of the same judgment call): treating "we're small now" as a permanent
exemption after a graduation trigger (§5) has clearly fired; running a business-critical email/
notification/webhook synchronously in the request path "because it's simple," so a slow provider
makes users wait or a crash silently drops it; skipping idempotency on a job queue because "it
probably won't retry"; ignoring a stated compliance/audit requirement because the rest of the
system still looks like an MVP.

## 7. Invariants

```text
1. Every SDS states its scale tier and a one-line reason, before Sections 7/9/10 are drafted.
2. A Tier 1 classification is never used to skip the scale-independent baseline (auth, input
   validation, secrets hygiene, the 1-2 must-hold DB invariants).
3. A Tier 3 pattern (Saga, circuit breaker, formal RTO/RPO, multi-service data ownership) is never
   introduced for a system with no stated Tier 3 signal — it needs a reason, not a habit.
4. A Tier 1/2 SDS states its graduation trigger — the tier is a snapshot, not a permanent label.
5. A "yes" to the external-critical-system-integration question (§0.3) means Tier 3 regardless of
   current traffic — consequence severity outweighs volume for this one question.
```

## 8. Mandatory Statement in the SDS

Every SDS states, near the top (Architecture Context or equivalent): the tier classification, a
one-line reason referencing the decision questions (§0), and — if Tier 1 or Tier 2 — the specific
graduation trigger (§5) to watch for.
