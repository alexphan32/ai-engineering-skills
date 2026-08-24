# Domain-Driven Design (DDD)

Load this for Axis 2 (`architecture-selection.md` §2) once a bounded context has answered "yes"
to enough of that section's questions to justify tactical patterns, and always load §1 (Strategic
Design) when evaluating a microservices split — bounded contexts are the seam that decision is
made along.

## 1. Strategic Design — Finding the Boundaries

- **Ubiquitous language**: the vocabulary domain experts actually use, mirrored exactly in code —
  class/module names, not a translation layer between "what the business calls it" and "what the
  code calls it." If a domain expert wouldn't recognize a term, it's not ubiquitous language yet.
- **Bounded Context**: a boundary within which a model and its language are consistent and
  unambiguous. The same word can mean different things in different contexts — "Customer" in a
  Sales context (someone who might buy) and "Customer" in a Billing context (an account with a
  payment method) are legitimately different models, not a naming inconsistency to unify. Forcing
  one shared "Customer" model across both contexts is a common source of an ever-growing entity
  that satisfies neither context well.
- **Context Map**: how bounded contexts relate to and integrate with each other. Common patterns:

```text
Shared Kernel        — two contexts deliberately share a small, jointly-owned model subset.
                        Only for contexts with a very tight relationship and shared team ownership
                        — a Shared Kernel between contexts owned by different teams recreates
                        cross-team coupling on every change.
Customer/Supplier     — the upstream context's team commits to meeting the downstream's needs;
                        downstream has a voice in upstream's roadmap.
Conformist            — downstream just accepts upstream's model as-is, no negotiation power
                        (common when upstream is a third-party/legacy system).
Anticorruption Layer  — downstream translates upstream's model into its own at the boundary,
                        protecting its own model from upstream's design (or a legacy system's mess)
                        leaking in. The default choice when integrating with an external system of
                        record this team doesn't control.
Open Host Service /
Published Language    — upstream publishes a well-defined, stable API/schema for many downstream
                        consumers, rather than negotiating per-consumer.
```

- **Subdomain classification** — spend modeling effort where it pays off:

```text
Core        — what makes this business actually competitive/differentiated. Worth full tactical
              DDD investment; this is where the complexity genuinely lives.
Supporting  — necessary, but not differentiating (e.g. internal notifications). Simpler modeling
              is fine; don't over-invest here.
Generic     — solved problems with existing solutions (auth, payments processing, email delivery).
              Buy or use an existing library/service rather than modeling it at all.
```

## 2. Tactical Design — Patterns Within a Bounded Context

Only reach for these once Axis 2's questions (`architecture-selection.md` §2) actually justify
them for this context — applying them to a CRUD screen is ceremony with no payoff.

- **Entity**: has identity that persists across state changes (an `Order` is the same order even
  after every field changes) — equality is by ID, not by field values.
- **Value Object**: defined entirely by its attributes, no identity (`Money`, `Address`,
  `DateRange`) — immutable, equality by value. Prefer Value Objects over primitive fields whenever
  a primitive is really a domain concept with its own invariants (an `Email` value object that
  validates format beats a bare `string`).
- **Aggregate**: a cluster of Entities/Value Objects treated as one consistency boundary — exactly
  one Entity is the Aggregate Root, and everything outside the aggregate refers to it only by ID,
  never by holding a reference into its internals. **One transaction touches at most one
  aggregate.** This is the rule most often violated, and violating it is what causes an aggregate
  to silently grow until it spans half the domain.
- **Repository**: one per Aggregate Root, providing collection-like access (`findById`, `save`) —
  never a generic repository per table, and never a way to load part of an aggregate without its
  invariants.
- **Domain Event**: a fact that happened within the domain (`OrderPlaced`, `PaymentCaptured`),
  named in past tense, carrying the data other parts of the system need to react — the mechanism
  for both in-process (`event-driven-architecture.md` §3) and cross-service (§4) reactions.
- **Domain Service**: domain logic that doesn't naturally belong to one Entity/Value Object
  (a pricing calculation spanning several aggregates) — stateless, operates on the domain model
  passed to it.
- **Application Service / Use Case**: orchestrates a single use case — loads aggregate(s) via
  Repository, calls domain logic, persists, publishes events. Contains no business rules itself;
  it's a thin coordination layer. Business rules belong in the domain model, not here.
- **Factory**: encapsulates complex aggregate creation when a plain constructor can't enforce the
  aggregate's invariants at creation time.

## 3. When DDD Tactical Patterns Are Overkill

Most systems have both kinds of area, often side by side:

- **Use it**: a pricing/discount engine with dozens of interacting rules, a workflow with many
  valid/invalid state transitions, a domain where getting an invariant wrong has real business
  consequences.
- **Skip it**: an admin CRUD screen, a reporting/read-only view, a settings page — a plain
  transaction script (a function per use case, straightforward data access) is simpler, easier to
  read, and loses nothing, because there's no rich behavior to protect. Wrapping these in
  Aggregates/Repositories/Domain Events is the DDD-flavored version of over-engineering
  `system-scale-checklist.md` already warns against.

State this per bounded context/module in the Architecture Decision output
(`architecture-selection.md` §5) — "core pricing domain: full tactical DDD; admin/reporting
modules: plain CRUD" is a coherent, common decision, not an inconsistency to resolve.

## 4. Anti-Patterns

- **Anemic domain model**: classes named like Entities but containing only getters/setters, with
  all actual logic living in a separate "service" layer that manipulates them from outside. This is
  DDD vocabulary without DDD's actual benefit (behavior colocated with the data it protects) — if
  the domain objects have no behavior, it's a transaction script wearing DDD naming, not DDD.
- **God aggregate**: one aggregate that grows to encompass most of the domain because boundaries
  were never drawn — every operation ends up loading and locking it, killing concurrency. Split
  along the actual consistency requirements: does this operation truly need both pieces of data
  updated atomically, or would eventual consistency (a domain event) between two smaller aggregates
  be correct?
- **Applying full tactical DDD uniformly** across Core, Supporting, and Generic subdomains alike —
  wastes the modeling budget on parts of the system where it doesn't pay off (§3).
- **Skipping the Context Map** and letting bounded contexts integrate ad hoc — without a stated
  integration pattern (§1), each new integration reinvents translation logic inconsistently, and
  an Anticorruption Layer that should exist quietly doesn't.
- **Using DDD's strategic design once, then never revisiting bounded-context boundaries** as the
  domain understanding deepens — bounded contexts are a hypothesis validated by building against
  them, not a one-time exercise.
