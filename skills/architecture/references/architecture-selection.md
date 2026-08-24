# Architecture Selection — Decision Framework

Load this in MODE: SELECT and MODE: UPGRADE, right after classifying the Scale Tier
(`system-scale-checklist.md` §0). It walks the three independent decisions that together define
"the architecture" for a system or component, then points to the detail file for whichever
pattern the decision lands on.

## 0. Three Independent Axes — Don't Collapse Them Into One Choice

A common mistake is treating "microservices vs. monolith", "DDD vs. not", and "event-driven vs.
request/response" as one big either/or choice. They're three separate axes that compose:

```text
Axis 1 — Deployment topology:     Monolith / Modular Monolith  ⟷  Microservices
Axis 2 — Domain modeling approach: Transaction Script / CRUD    ⟷  Domain-Driven Design
Axis 3 — Communication style:      Synchronous request/response ⟷  Event-Driven
```

- A **modular monolith** can (and often should) use DDD tactical patterns internally, and can
  dispatch in-process domain events between modules — none of that requires microservices.
- **Microservices** almost always need *some* event-driven communication for cross-service
  consistency, but the reverse isn't true: plenty of event-driven systems are a single deployable
  with an in-process event bus.
- **DDD's strategic design (Bounded Contexts)** is the *input* to deciding microservice
  boundaries, not a competing choice — if you're evaluating microservices, do the bounded-context
  exercise first (`domain-driven-design.md` §1) rather than splitting by team org chart or by
  technical layer.

Answer each axis with its own reasoning. A system can be "modular monolith + DDD tactical patterns
+ mostly synchronous with one async job" — that's a coherent, common, correct combination, not a
half-finished decision.

## 1. Axis 1 — Deployment Topology

Load `system-scale-checklist.md` §0 first — the Tier classification drives this axis directly:

| Tier | Default topology | Reasoning |
|---|---|---|
| Tier 1 (MVP) | Monolith | One team, one deployable, no independent-deployment need. A monolith is the *correct* choice, not a starting point to outgrow immediately. |
| Tier 2 (Async/Growing) | Modular Monolith | Real usage, maybe a background-job need, but still one team/system of record. Enforce module boundaries now so extraction later (if it ever happens) is cheap. |
| Tier 3 (Enterprise/Distributed) | Microservices — but only along the axis that actually triggered Tier 3 | Multiple teams needing independent deployability, or a stated compliance/availability requirement, or genuine cross-service data ownership. Extract services along Bounded Context seams (`domain-driven-design.md` §1), not by picking components that "feel separable." |

**Load next:** `modular-monolith.md` for Tier 1/2, `microservices.md` for Tier 3.

**The one-way door to watch for:** going from Monolith → Modular Monolith is cheap (it's an
internal refactor with no deployment change). Going from Modular Monolith → Microservices is
expensive (new deployment pipelines, network boundaries, data ownership splits, distributed
failure modes). Going from Microservices back to a monolith is *very* expensive and rarely
attempted. This asymmetry is why the default under uncertainty is always the cheaper-to-reverse
option — Tier 1/2 signals should never be talked up to "prepare for" a Tier 3 that hasn't actually
arrived.

## 2. Axis 2 — Domain Modeling Approach

This axis is about **domain complexity**, not scale — a Tier 1 system with genuinely complex
business rules (e.g. a pricing engine with dozens of interacting rules) can still warrant DDD
tactical patterns, and a Tier 3 system with mostly CRUD screens around simple entities doesn't need
them everywhere.

Ask, per bounded context / module (not once for the whole system):

```text
1. Does this area have business rules and invariants that are non-trivial to state correctly —
   rules that interact, that change with new requirements, or that a junior engineer would
   plausibly get wrong without domain knowledge?
2. Is there a rich vocabulary domain experts use that the code should mirror (ubiquitous language),
   or is this just moving fields between a form and a table?
3. Will this area be actively developed and evolved, or is it a stable, rarely-touched CRUD screen?
```

- Mostly "no" → **Transaction Script / plain CRUD** is correct: a service function per use case,
  simple data-access layer, no Aggregates/Value Objects/Repositories ceremony. Adding DDD tactical
  patterns here is pure ceremony with no payoff — this is over-engineering exactly like adding
  Kafka for a Tier 1 feature.
- Mostly "yes" → load `domain-driven-design.md` for tactical patterns (Entity, Value Object,
  Aggregate, Repository, Domain Event, Domain Service).

**A system rarely answers this the same way everywhere.** It's normal for the core pricing/risk
domain to justify full DDD tactical patterns while the admin/reporting/audit-log modules next to it
stay plain CRUD. State the boundary explicitly rather than applying one approach uniformly.

## 3. Axis 3 — Communication Style

| Situation | Style | Detail |
|---|---|---|
| Everything the user waits on, single deployable, no cross-boundary async need | Synchronous request/response only | No event bus, no broker. This is correct for most of a Tier 1 system. |
| A workflow needs to run outside the request cycle (email, export, slow third-party call, scheduled job) but there's still one system of record | One narrowly-scoped async mechanism (durable job queue) | `system-scale-checklist.md` §2 — not a general event bus |
| Modules within one deployable need to react to something happening elsewhere without a direct call (e.g. "when Order is placed, Inventory should reserve stock") | In-process domain events (mediator/pub-sub within the monolith) | `event-driven-architecture.md` §3 |
| Independently-deployed services need to stay consistent without a distributed transaction | Event-driven via a real broker (Kafka/SQS/RabbitMQ), often with Saga/Outbox | `event-driven-architecture.md` §4, then the mechanics in `.claude/skills/design/references/distributed-systems-checklist.md` |

**Don't reach for event-driven because it sounds decoupled.** Every event hop is a fact that a
future engineer has to trace across services/modules to understand one business flow — that's a
real debugging cost, paid whether or not the decoupling was actually needed. Justify it against a
concrete async or cross-boundary requirement, not a general preference for loose coupling.

## 4. Applying the Stack

Once the three axes are decided, the *implementation shape* for whatever platform this system is
built on is a separate, narrower decision — the topology/domain/communication choices above don't
change based on whether it's a script, a mobile app, or a backend API, but the idiomatic way to
express "modular" or "layered" absolutely does. Load the matching file:

| Platform | File |
|---|---|
| CLI tools, one-off/scheduled scripts | `backend-script-patterns.md` §1 |
| Rust backend services | `backend-script-patterns.md` §2 |
| Python FastAPI backend services | `backend-script-patterns.md` §3 |
| Go + Fiber backend services | `backend-script-patterns.md` §4 |
| Spring Boot (Java) backend services | `backend-script-patterns.md` §5 |
| Next.js + Prisma full-stack | `backend-script-patterns.md` §6 |
| NestJS backend services | `backend-script-patterns.md` §7 |
| Angular frontend | `frontend-patterns.md` §1 |
| React frontend | `frontend-patterns.md` §2 |
| Android (native) | `mobile-patterns.md` §1 |
| iOS (native) | `mobile-patterns.md` §2 |
| Flutter (cross-platform) | `mobile-patterns.md` §3 |

## 5. Output — State a Decision, Not a Survey

MODE: SELECT and MODE: UPGRADE don't end with "here are the options" — they end with a stated
choice per axis, each with a one-line reason and the alternative considered. See the "Architecture
Decision" output format in `SKILL.md`'s MODE: SELECT section. A decision without a stated
alternative reads as if no other option was considered, which is rarely true and not verifiable by
a reviewer.

## 6. Anti-Patterns Across All Three Axes

- **Resume-driven architecture**: choosing microservices/event-sourcing/CQRS because they're the
  "modern" pattern, not because a Tier 3 signal or a real domain-complexity/async need is present.
- **Cargo-culting a pattern from a previous project** without checking whether *this* system's
  Tier, domain complexity, and async needs actually match the project it was copied from.
- **Solving all three axes with one decision** — e.g. "we're doing microservices" answering the
  domain-modeling and communication questions by assumption instead of by their own reasoning.
- **Re-litigating the decision on every feature** — the axes are decided at the system/bounded-
  context level; a new feature within an already-decided context inherits that context's answers
  unless it has its own Tier 3 signal (`system-scale-checklist.md` §0.3–.4 apply per-feature, not
  just per-system).
