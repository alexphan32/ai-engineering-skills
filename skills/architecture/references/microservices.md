# Microservices

Only the correct topology when a real Tier 3 signal is present (`system-scale-checklist.md` §0,
§3) — more than one team needing independent deployability, a stated compliance/availability
requirement, genuine cross-service data ownership, or a scale constraint a single well-configured
instance/database can't absorb. Load this in MODE: SELECT/UPGRADE only after that check; load it
in MODE: EXPLORE when documenting an existing microservices system, to know what to look for.

## 1. Core Principles

- **One service = one bounded context = one team = one database.** No service shares a database
  or a table with another — cross-service reads/writes go through that service's API or events,
  never a direct DB connection. A service reaching into another service's database is the single
  most common way "microservices" quietly becomes a distributed monolith (§4).
- **Boundaries come from Bounded Contexts, not org charts or technical layers.** Use
  `domain-driven-design.md` §1's context-mapping exercise to find the seams — "the auth team" or
  "the frontend-facing services" are not bounded contexts.
- **Decentralized data management.** Each service picks its own storage technology and schema;
  consistency across services is eventual, not a shared ACID transaction (`event-driven-
  architecture.md` §4, and the mechanics in `.claude/skills/design/references/
  distributed-systems-checklist.md`).
- **Failure isolation.** A dependency's slowness or outage must not cascade — timeouts on every
  call, circuit breakers on unreliable dependencies, bulkheads so one overloaded dependency doesn't
  exhaust the resources needed to serve unrelated requests.
- **Independent deployability is the actual point.** If two services must always be deployed
  together for the system to stay correct, they are not actually independent services yet — that
  coupling needs a stated reason or the boundary needs redrawing.
- **Observability is not optional infrastructure, it's how anyone debugs a request that crossed
  three services.** Correlation IDs propagated on every call, distributed tracing, and per-service
  health/liveness are part of the architecture, not an ops afterthought
  (`.claude/skills/design/references/operations-readiness-checklist.md`).

## 2. Communication Patterns

- **Synchronous (REST/gRPC)** for a caller that needs an answer now to proceed (a read, a
  validation check). Every synchronous cross-service call needs a stated timeout and a stated
  fallback/degraded behavior if the callee is unavailable — an unbounded synchronous chain is how
  one slow service takes the whole request path down with it.
- **Asynchronous (events via a broker)** for propagating state changes across services and for
  workflows spanning more than one service's data (Saga/Outbox pattern) —
  `event-driven-architecture.md` §4. This is where most cross-service consistency actually lives
  in a mature microservices system; reaching for a synchronous call chain to keep two services'
  data in sync is usually the wrong choice once more than two services are involved.
- **Depth limit on synchronous chains**: if satisfying one incoming request requires a
  synchronous call chain more than 2–3 services deep, that's a design smell — either the boundary
  is wrong (data that's actually one bounded context split across services) or the chain should be
  broken with an async step / a read-model that's kept in sync via events instead of queried live.

## 3. Costs — State These Explicitly, Don't Let Them Go Unsaid

Microservices trade implementation simplicity for organizational scalability. Never adopt them
without naming these costs in the decision (`architecture-selection.md` §5):

```text
- Operational complexity: N deployment pipelines, N sets of infrastructure, N services to monitor
  instead of one.
- Distributed transactions: no more ACID across a business operation that spans services — Saga/
  Outbox/Compensation must be designed explicitly per `.claude/skills/design/references/
  distributed-systems-checklist.md`.
- Network unreliability: every cross-service call can time out, partially succeed, or arrive
  duplicated — code that assumed a function call now has to assume a network call.
- Testing complexity: integration/contract tests across service boundaries, harder-to-reproduce
  bugs that only appear under real network conditions.
- Eventual consistency: data read from one service may be momentarily stale relative to a write
  just made in another — every read path that can't tolerate that needs its own design (synchronous
  call, or a documented staleness window).
- Team/organizational overhead: someone has to own cross-cutting concerns (shared auth, service
  discovery, a platform/infra team) or every service reinvents them inconsistently.
```

## 4. Anti-Patterns

- **Distributed monolith**: services that must be deployed together, that share a database, or
  that make long synchronous call chains to satisfy one request — all the operational cost of
  microservices with none of the independent-deployability benefit. This is the most common failure
  mode of a premature or poorly-bounded microservices split.
- **Extraction with no clear bounded context** — splitting by "this file got big" or by guessing
  at future team structure, instead of by an actual domain seam (`domain-driven-design.md` §1).
  A service boundary drawn in the wrong place is far more expensive to fix than a module boundary
  in a monolith, because fixing it means changing a network contract with live consumers.
- **Nanoservices** — splitting far past the point bounded contexts justify (a service per CRUD
  entity, a service per verb) multiplies the operational costs in §3 without any corresponding
  benefit; a bounded context is usually coarser-grained than a single entity.
- **Adopting microservices for a Tier 1/2 system "to scale later"** — this is exactly the
  over-engineering `system-scale-checklist.md` §6 warns against: paying the full cost in §3 today
  for a Tier 3 signal that hasn't appeared and may never appear.
- **Sharing a client library that couples services' internal models** — a shared "domain model"
  package imported by every service reintroduces the same coupling a database would, just moved
  into a library; each service's model is its own, translated at the boundary if needed.

## 5. When Documenting an Existing Microservices System (MODE: EXPLORE)

Look specifically for the anti-patterns in §4 as part of SYNTHESIZE's cross-cutting pattern
detection — a shared database across "microservices," a synchronous call chain deeper than 2–3
services, or a shared model library are architecturally significant findings, not incidental
details, and belong in the "Issues Discovered" section of the architecture docs.
