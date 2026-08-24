# Operations Readiness Checklist

Load this for any module deployed as its own running service/process (MODE B/D/E always; MODE C
when it's more than a static page — anything with a background worker/queue consumer; MODE A only
for the Data Lifecycle/Resource Management angles on a long-running batch job). This covers what a
system needs to be **run**, not just built: observability, operability, configuration discipline,
dependency/resource bounds, and — for anything with a stated availability or retention
requirement — disaster recovery and data lifecycle. A system that's correct but impossible to
operate at 3am during an incident is still an unfinished design.

## Priority levels

Same convention as the other checklists: **[MUST]** blocks the SDS from being done for a module
this applies to, **[SHOULD]** needs an explicit reason if skipped, **[MAY]** is a recommendation.
Several sections here are workload/criticality-dependent — a low-traffic internal admin screen
doesn't need a graceful-shutdown design the way a Kafka consumer does. State "N/A — reason" rather
than silently omitting.

## 1. Structured Logging & Correlation [MUST]

State the fields every log line for this module carries: `correlationId`/`traceId`, `userId`/
`tenantId` (when applicable), `requestId`, and a structured (JSON, not free-text-interpolated)
format. This overlaps with `security-checklist.md` §11 (what must NEVER appear in a log) — this
section is about what SHOULD always appear, so an incident can be traced by ID rather than
grepped for by guessing a substring.

## 2. Metrics — Business vs. Technical [MUST for any module handling production traffic]

Name the metrics this feature exposes, and classify each as **business** (meaningful to a product
owner — did the thing the system is for actually happen) or **technical** (meaningful to an
on-call engineer — is the infrastructure healthy):

```text
business:   transaction.failed.total, transaction.approved.total, payment.declined.total
technical:  transaction.processing.duration, kafka.consumer.lag, db.connection.pool.exhausted,
            http.request.duration.p99
```

State the metric name, type (counter/gauge/histogram), and the labels/dimensions it carries — and
flag any label whose cardinality is unbounded (e.g. a raw `userId` label on a counter) as a design
smell, since that can silently blow up a metrics backend's cardinality budget.

## 3. Alerting Thresholds [SHOULD]

For a metric that matters enough to page someone, state the threshold and the reason it was
chosen (SLO-derived, not arbitrary) — e.g. "page if `error_rate > 1%` over 5 minutes, because the
SRS's error-rate target is 0.5%." A metric with no stated threshold is a dashboard curiosity, not
an operational signal; don't design ten metrics and leave "someone will figure out alerting later"
implicit.

## 4. Health Checks — Liveness vs. Readiness [MUST for any module deployed as its own service/pod]

These answer different questions and mixing them up causes real outages:

```text
Liveness:  "is this process stuck and needs a restart?"
           — should NOT check downstream dependencies; a slow DB shouldn't cause the
             orchestrator to kill and restart a perfectly healthy process in a crash loop
Readiness: "should traffic be routed to this instance right now?"
           — SHOULD check the dependencies this instance actually needs (DB reachable,
             required cache/queue connection established) before receiving requests
```

State what each endpoint checks for this specific module — a readiness probe that always returns
200 provides no protection, and a liveness probe that checks the database can turn one slow
dependency into a cluster-wide restart storm.

## 5. Graceful Shutdown [MUST for any consumer/worker process; SHOULD for a plain request-serving API]

State the shutdown sequence this module follows on `SIGTERM`, so an in-flight request or a
partially-consumed message isn't dropped or double-processed on deploy:

```text
SIGTERM
  → stop accepting new requests / new poll from the queue
  → finish in-flight requests (bounded by a drain timeout)
  → stop message consumers
  → commit offsets / acknowledge processed messages
  → close DB/HTTP/cache connections
  → exit
```

A worker that gets killed mid-message with no drain period is how "processed but not
acknowledged" duplicates happen on every rolling deploy, independent of any application bug.

## 6. Configuration vs. Code vs. Secret vs. Feature Flag [MUST]

Every value this module reads falls into exactly one of these categories — collapsing the
distinction is where operational pain comes from:

```text
Code:          a value that only changes when the code changes and is redeployed
               (e.g. the shape of a formula)
Configuration: a value operators need to change WITHOUT a redeploy — timeouts, retry counts,
               feature thresholds, rate limits
Secret:        a credential, key, or token — never in a config file or environment variable
               committed to source control; sourced from a secret manager
Feature Flag:  a boolean/enum that changes behavior at runtime, typically for gradual rollout
```

```java
if (environment.equals("prod")) { ... }   // hardcoded environment branch — a config/flag instead
MAX_RETRY = 5;                            // fine if it's truly load-bearing-only-at-compile-time;
                                           // WRONG if an operator needs to tune it during an
                                           // incident without waiting for a deploy — then it's
                                           // Configuration, not a code constant
```

For every threshold/limit/timeout this module introduces, state which category it is — this
determines whether it belongs in the enum/constants file `implement` uses, or in externalized
config the deployment platform injects.

## 7. Deployment Strategy & Rollback [SHOULD, MUST for a change with schema/contract risk]

For a change with real blast radius (a schema migration, a behavior change on a critical path, a
new external dependency), state the deployment approach — rolling, blue/green, or canary — and
confirm a rollback path actually exists and was considered, not assumed. A migration that's
one-directional (§ below, and `distributed-systems-checklist.md` §36 for schema compatibility) has
no rollback path by definition — flag that explicitly rather than discovering it during an
incident.

## 8. Dependency Chain Depth [MUST for a synchronous request path]

State the depth of synchronous calls this feature's critical path makes, end to end:

```text
API → ServiceA → ServiceB → ServiceC → ServiceD → CoreBanking
```

Every hop adds its latency (and its own failure probability) to the total — five hops at
50-100ms each is 300ms+ before any single hop looks slow in isolation, and a single slow/degraded
hop degrades the entire chain (this is also covered from the latency-budget angle in
`performance-checklist.md` §19; this section is the "should this chain exist at all" question).
For a deep or growing chain on a critical path, consider: can a hop be parallelized, cached,
moved off the critical path (async), or collapsed via an aggregating API? State the answer, even
if it's "no, this depth is accepted because X."

## 9. Circular Service Dependency [MUST]

The module-level circular-dependency check already exists in code review (`review` skill's CODE
mode, Compliance criterion). State it here at the service level too: Service A calling Service B calling
Service A (directly, or transitively through C) creates a deployment-ordering problem and a
cascading-failure risk that doesn't show up in a single codebase's import graph. If this feature
adds a call from A to B, verify B (or anything B calls) doesn't already call back into A.

## 10. Resource Management — Bounded, Released, Timeout, Leak [MUST]

`performance-checklist.md` §6-7 already covers DB/HTTP connection pools and thread/goroutine
concurrency bounds for the *performance* angle. This section asks the same question about every
other resource type the process holds, from the *operability* angle — what happens over hours/days
of uptime, not just under one request's load:

```text
For every resource this module acquires (file handle, socket, DB connection, HTTP client,
Kafka consumer, goroutine/thread, timer/scheduled task):
  Bounded?   — is there a hard cap, or can it grow with input size / traffic?
  Released?  — is there a guaranteed release path (finally/defer/try-with-resources), including
               on the error path, not just the happy path?
  Timeout?   — can this resource be held forever by a stuck operation?
  Leak?      — under a soak test (sustained run), does usage of this resource grow monotonically?
```

```text
for request:
    go process()          // spawns one goroutine per request with no cap — 1M concurrent
                           // requests spawns 1M goroutines and the process falls over
```

State the bound explicitly for anything spawned per-request or per-message, not just "the
framework handles it."

## 11. Availability Target & Disaster Recovery [MUST when the SRS states an availability/RTO/RPO target; otherwise N/A]

Never invent an availability number, RTO, or RPO if the SRS doesn't state one — mark
`[AVAILABILITY TARGET NEEDED — SRS §X.Y or user input]`, the same discipline as a missing
performance baseline. When a target does exist, state:

```text
Availability = 99.95%   RTO = 30 minutes   RPO = 5 minutes
```

and the mechanism that achieves it (multi-AZ, read replica promotion, backup frequency matching
the RPO). The one invariant that applies regardless of whether a formal target exists: **a backup
that has never had its restore procedure tested is not a reliable backup** — if this module
introduces a new datastore or a new critical table, state that a restore drill is planned/exists,
don't just state that backups run.

## 12. Data Lifecycle & Retention [SHOULD, MUST if this module stores PII or data with a legal/regulatory retention requirement]

Data that's created but never expires becomes a growing cost and a growing liability. State, for
any entity with unbounded growth or PII content:

```text
Create → Active → Archive → Retention period → Delete/Anonymize
```

Specifically: how long is this data actively queried before it can move to cheaper storage or be
archived, what's the legally-required minimum retention (if any — this is a business question,
`[NEEDS SPEC CLARIFICATION]` if the SRS doesn't say), and — for PII — what the deletion/
anonymization path looks like when a retention period ends or a user requests deletion. "This data
is retained forever" is a valid answer only when explicitly justified, not the silent default.

## 13. Compliance — Separation of Duties [MUST for any approval/maker-checker workflow]

Beyond the authorization chain `security-checklist.md` §2 already requires (Auth → Role →
Permission → Resource ownership → Action), a maker-checker workflow needs one more explicit rule:
**the maker and the approver must not be the same identity**, even if that identity holds both
roles. State this as part of the authorization design for the approval action —
`user.id != resource.makerId`, not just `user.hasRole(APPROVER)` — since a role check alone
permits self-approval whenever one person is granted both roles.

## 14. Anti-Patterns — Red Flags

If any of these appear in a design, stop and redesign: a liveness probe that checks downstream
dependencies; a readiness probe that always returns 200; a worker with no drain/shutdown sequence
that can be killed mid-message on every deploy; an environment check (`if prod`) standing in for a
feature flag or config value an operator needs to change without a redeploy; a resource
(goroutine/thread/connection/timer) spawned per-request or per-message with no cap; an
availability/RTO/RPO number invented without an SRS source; a backup design with no stated restore
verification; PII with no stated deletion or retention path; an approval workflow whose
authorization check would permit the same user to author and approve the same resource; a
synchronous critical path whose hop count was never counted or questioned.

## 15. Invariants

```text
1. Liveness and readiness probes check different things and neither is a stub that always passes.
2. Every consumer/worker process has a stated graceful-shutdown sequence.
3. Every operator-tunable value is externalized configuration, not a recompiled constant.
4. No secret ever lives in a config file, environment variable dump, or code literal.
5. Every per-request/per-message resource allocation has a stated bound.
6. No availability/RTO/RPO number is invented without an SRS or explicit user-stated source.
7. A backup is not "reliable" until its restore procedure has been exercised at least once.
8. PII and legally-retained data have a stated retention period and deletion/anonymization path.
9. A maker-checker workflow's authorization design explicitly forbids self-approval.
10. A synchronous dependency chain's depth on a critical path is a stated, considered number — not an emergent one nobody counted.
```

## 16. Mandatory Test Cases [MUST include in the test plan for a module this checklist applies to]

Readiness probe returns unhealthy when a required dependency is down (and liveness still passes);
graceful shutdown under a `SIGTERM` with an in-flight request completes it rather than dropping
it; a config value change takes effect without a redeploy (verifies it's actually externalized,
not baked in); a resource-bound test — a soak/load test confirms the resource in question
(connections, goroutines, file handles) doesn't grow unboundedly over the run; for an approval
workflow, a test that the maker attempting to approve their own request is rejected; for a module
with a stated RTO/RPO, a restore-from-backup drill exists (even if run outside the automated test
suite, its existence and cadence should be stated).
