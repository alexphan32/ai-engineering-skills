# Design Decisions, Alternatives, Risks & Implementation Mapping

> Reference for `design` skill — mode-independent. Append these as extra sections to whatever
> mode template you're drafting (after the mode-specific sections, before Test Plan), using the
> generic format below rather than something mode-specific — the content differs per feature,
> the *shape* doesn't need to.

## Why this exists

An SDS that jumps straight from "here's the schema" to "here's the API" hides the moment where
the real risk enters: the point where you picked Kafka over a synchronous call, or a distributed
lock over Kafka partitioning, without writing down why. Six months later, someone (maybe you)
looks at that choice, doesn't understand the reasoning, and either "fixes" it into something worse
or is too scared to touch it. Writing the alternatives and the reasoning down costs a few minutes
now and saves that whole class of regression.

## 1. Labeling technical statements

Same taxonomy as the `spec` skill's assumption labels, applied to *technical* rather than
business content — keep this consistent so a reader who's seen one recognizes the other:

| Label | Meaning |
|---|---|
| `[DESIGN DECISION]` | A technical choice you made within the freedom the SRS leaves you — record it as a mini-ADR (§2) |
| `[ASSUMPTION]` | A technical detail the SRS doesn't state and you filled in to keep drafting (e.g. assumed connection pool size, assumed a specific retry count) — low-risk ones can ship labeled; anything that would be expensive to change later should get surfaced in Open Questions instead |
| `[NEEDS SPEC CLARIFICATION]` | You've hit a **business** question, not a technical one, that the SRS didn't answer — this is not yours to decide. Stop, don't guess, and either ask the user or say the SDS is blocked pending `/spec`. This is the design-side mirror of `/spec`'s own escalation rule — the boundary between the two skills only holds if both sides respect it. |

The failure mode this prevents: an SRS says "Approver approves the transaction" without saying whether
self-approval is allowed, and a design silently assumes "no" and builds an authorization check
around that assumption. That's not a technical detail — it's a business rule the SRS never
stated, and it belongs in `[NEEDS SPEC CLARIFICATION]`, not a design footnote.

## 2. Design Decisions & Alternatives

**When required**: for a decision that would be expensive to reverse after implementation starts
— the messaging technology, the concurrency-control mechanism (optimistic lock vs. pessimistic
vs. distributed lock vs. partition-by-key), the consistency model for a piece of distributed
data, introducing a new service/component vs. extending an existing one, or any decision the
`security-checklist.md`/`performance-checklist.md`/`distributed-systems-checklist.md` flagged as
`[MUST]` and non-obvious. Skip it for decisions with one obvious answer (e.g. "use the existing
Postgres connection pool") — the point is to slow down at forks in the road, not pad the document.

**Format per decision:**

```markdown
### DECISION-01: [short name]

**Problem**: [what needs to be decided, and why it matters]

**Options considered:**
- Option A: [name] — [one-line description]
- Option B: [name] — [one-line description]
- Option C: [name] — [one-line description]

**Chosen**: [Option X]

**Reason**: [why this one, referencing the actual constraint — existing infra, throughput
target, team familiarity, ordering requirement — not just "it's better"]

**Trade-offs accepted**: [what you're giving up by not picking another option]
```

Two options is fine when the field is genuinely narrow (e.g. "Postgres row lock" vs. "Redis
distributed lock") — the point is showing the reasoning, not hitting a quota of three.

**Use Second-Order Thinking when weighing options**: don't stop at "this is faster" or "this is
simpler" — ask what that choice costs two steps later (the messaging tech that's easy to wire up
now but hard to change once a second consumer needs a different ordering guarantee). That's what
the **Trade-offs accepted** field is for — capture the second-order cost, not just the first-order
benefit.

## 3. Risks & Trade-offs

A short list, not a essay — what could make this design wrong, and what you're accepting anyway.
**Use a Pre-mortem to populate it**: imagine the design has already failed in production and ask
what caused it — each failure mode you can name this way belongs in the table below, not just the
ones a reviewer happens to ask about.

```markdown
| Risk | Likelihood | Impact | Mitigation / Accepted because |
|---|---|---|---|
| [e.g. "Core Banking P99 unknown — NFR-01's 3s timeout may be too aggressive"] | Medium | High | Flagged as `[PERF TARGET NEEDED]`; design uses async + polling so a wrong timeout degrades gracefully rather than failing hard |
```

Every `[ASSUMPTION]` from §1 that carries real risk if wrong should show up here too, cross-
referenced — this section is where a reviewer looks first to decide whether the design is safe
to build against, and duplicating the pointer costs one line.

## 4. Implementation Mapping

Close the gap between "here's the design" and "here's what to type" with a concrete directory/
class map — this is what makes `/implement` a translation instead of a second design pass:

```markdown
feature-name/
├── api/            # [Controller/Handler — one line on responsibility]
├── application/    # [Use case / Application Service — one line]
├── domain/         # [Entity, value objects, domain services, state machine — one line]
└── infrastructure/ # [Repository impl, external adapters, messaging — one line]
```

Adapt the folder names to whatever the mode/stack actually uses (Next.js's `lib/`+`app/`, Spring's
package-per-layer, NestJS's module folder) — the point is naming the actual files/classes this
feature touches or creates, not inventing a generic structure that doesn't match the codebase.

## 5. When a section has nothing to say

Don't omit these sections when they're thin — state that explicitly (`"No alternatives
considered — single viable approach given existing Kafka infrastructure"` or `"No new risks
beyond what's covered in Section 10"`). A missing section reads as "forgot to think about this";
an explicit one-liner reads as "considered and moved on."
