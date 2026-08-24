# Event-Driven Architecture

Communication style (Axis 3, `architecture-selection.md` §3) — orthogonal to deployment topology.
Load this once a concrete async or cross-boundary need is identified; never as a default style
"because it's decoupled."

## 1. What It Is

Components communicate by publishing events — facts that already happened, named in past tense
(`OrderPlaced`, not `PlaceOrder`) — rather than calling each other directly. A producer doesn't
know or care who (if anyone) consumes an event; consumers subscribe to what they care about. This
is what enables producers and consumers to evolve and deploy independently, at the cost of the
tracing/debugging difficulty called out in §6.

## 2. Event Patterns

```text
Event Notification         — a thin event ("OrderPlaced, id=123") with no payload; consumers that
                              need details make a follow-up call to fetch them. Simple, but creates
                              a synchronous dependency at consumption time even though publishing
                              was async.
Event-Carried State Transfer — the event carries the data consumers need (order id, items, total)
                              so they don't have to call back. Reduces coupling and load on the
                              producer, at the cost of a larger event and a versioning surface
                              (§5) on that payload.
Event Sourcing             — the system of record IS the event log; current state is derived by
                              replaying events, not stored directly. Powerful for audit/replay/
                              temporal-query requirements, but a genuinely heavyweight pattern —
                              adopt only when audit trail or point-in-time reconstruction is an
                              actual stated requirement, not because event-driven is already in use.
CQRS                        — separate models for writes (commands) and reads (queries), often
                              paired with Event Sourcing but independently useful whenever the read
                              and write shapes have diverged enough that one model serves neither
                              well. Not a default — adds a second model and a sync mechanism between
                              them.
```

## 3. In-Process (Within a Modular Monolith)

A monolith doesn't need a message broker to get the decoupling benefit of events between its
internal modules: an in-process mediator/event bus dispatches a domain event
(`domain-driven-design.md` §2) to any in-process subscribers after the triggering transaction
commits. This is the mechanism `modular-monolith.md` §3 points to for "module A needs to react to
something in module B without B needing to know about A." No durability/ordering/broker concerns
apply here — it's a function call dispatched by name instead of by direct import.

## 4. Cross-Service (Real Broker)

Once the event crosses a deployment boundary (microservices, or a monolith talking to an external
system), it needs an actual broker (Kafka, SQS, RabbitMQ, etc.) and the durability/idempotency/
ordering/versioning concerns become real engineering problems, not stylistic choices:

- **Durability** — a consumer that's down when an event publishes must still see it later.
- **At-least-once delivery is the default assumption** — every consumer must be idempotent; "it'll
  only fire once" is not a safe assumption for any real broker.
- **Ordering** — usually only guaranteed within a partition/key, not globally; design consumers
  that don't assume global ordering unless the broker and partitioning scheme specifically
  guarantee it for the keys that matter.
- **Envelope** — every event needs `eventId`, `eventType`, `eventVersion`, `correlationId`,
  `causationId` at minimum, so consumers can dedupe, route by version, and trace a flow across
  services. A bare payload with no envelope is the single most common way a "minor" event schema
  change breaks a consumer that was never told to expect a new shape.
- **Cross-service consistency (Saga/Outbox)** — when a business operation spans services with no
  shared database, use the Outbox pattern (write the event in the same local transaction as the
  state change, publish it via a separate relay) to avoid the dual-write problem, and Saga
  (with explicit compensation per step) instead of a distributed transaction. The full mechanics —
  idempotency keys, DLQ, compensation design, unknown-result handling for external calls — live in
  `.claude/skills/design/references/distributed-systems-checklist.md`; this file is about *when*
  to choose event-driven, that one is about *how* to implement it correctly once chosen.

## 5. Tier Mapping

| Tier | What event-driven means here |
|---|---|
| Tier 1 | None — synchronous request/response only (`architecture-selection.md` §3). |
| Tier 2 | At most one narrowly-scoped durable job queue for out-of-request-cycle work (`system-scale-checklist.md` §2) — not a general event bus. In-process domain events (§3) are fine and don't change this classification, since they carry no cross-system durability requirement. |
| Tier 3 | A real event-driven backbone for cross-service consistency is justified — but still only for the flows that actually cross a service boundary, not retrofitted onto every internal interaction "for consistency of style." |

## 6. Anti-Patterns

- **Event-driven as a default style** for a feature with no actual async or cross-boundary need —
  every event hop is a fact a future engineer must trace to understand one business flow; paying
  that cost with no decoupling need to justify it is a net loss, not a best practice.
- **Choosing Event Sourcing for a plain CRUD entity** with no audit/replay/temporal-query
  requirement — the replay/rebuild machinery and the harder-to-query current-state problem it
  introduces have no corresponding benefit there.
- **Publishing events with no envelope** (§4) — works fine until the first schema change, then
  breaks every consumer that assumed the old shape with no version signal to detect it.
- **Treating "the message is published" as "the message is delivered and processed"** — without a
  DLQ and visibility into stuck/failing consumers, a systematically failing consumer fails silently
  (`system-scale-checklist.md` §2's "Visible" requirement for any async mechanism).
- **Introducing a message broker for a single background email send** — a durable job queue
  (`system-scale-checklist.md` §2) is the right-sized tool; a broker is infrastructure overhead
  with no payoff at that scale.
- **Assuming global event ordering** without checking what the broker/partitioning scheme actually
  guarantees — a consumer built on that assumption breaks the first time load increases enough to
  add partitions/consumers.
