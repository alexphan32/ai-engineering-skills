# SELECT — Full Workflow

Step-by-step detail for MODE: SELECT (choose an architecture for a new system, service, or
component). Loaded once SELECT is the confirmed mode — see `SKILL.md`'s HOW TO USE for mode
detection and the condensed step list.

For a new system, service, or component where the topology/domain-modeling/communication approach
isn't decided yet, or the user asks "how should I structure this."

---

## 1. GATHER CONTEXT

- If inside an existing project: run `explore-workflow.md`'s SCAN §A (stack/manifest detection) to
  identify the target stack, and glob for adjacent existing services/modules this new work must fit
  alongside — reuse `design` skill's Architecture Context discipline: classify anything touched as
  Existing/Modified/New/External before proposing a new component.
- If genuinely greenfield: ask the user directly for the stack, expected team size, and anything
  it must integrate with, if not already stated.

## 2. CLASSIFY SCALE TIER

Load `references/system-scale-checklist.md` §0. Answer the five classification questions honestly
— check the SRS's Dependencies/NFR sections first if one exists (same rule `design` follows), only
falling back to asking the user if it's genuinely undocumented. State the resulting Tier and a
one-line reason. Everything below depends on this being right.

## 3. WALK THE THREE AXES

Load `references/architecture-selection.md`. For each axis, state the choice and the alternative
considered:

- **Axis 1 — Deployment topology**: `architecture-selection.md` §1 maps Tier directly to a
  default. Load `references/modular-monolith.md` or `references/microservices.md` for the detail
  once the axis is decided.
- **Axis 2 — Domain modeling approach**: per bounded context/module, not once for the whole
  system — `architecture-selection.md` §2. Load `references/domain-driven-design.md` when the
  answer justifies tactical patterns.
- **Axis 3 — Communication style**: `architecture-selection.md` §3. Load
  `references/event-driven-architecture.md` when an actual async or cross-boundary need is
  present — never by default.

## 4. APPLY THE STACK PATTERN

Detect the stack (from GATHER CONTEXT) and load the matching reference:
`references/frontend-patterns.md` (Angular/React), `references/mobile-patterns.md`
(Android/iOS/Flutter), or `references/backend-script-patterns.md`
(Rust/FastAPI/Go-Fiber/Spring-Boot-Java/scripts). Pick the idiomatic internal structure for that
stack, expressed *inside* the topology chosen in Axis 1 (e.g. a FastAPI service organized as
`app/features/*` within a Tier 1 monolith deployable; a Rust workspace split into
per-bounded-context crates within a Tier 2 modular monolith; a Go/Fiber service laid out as
`internal/domain|usecase|adapter|infrastructure` per module; a Spring Boot service laid out as
`domain/repository/service/controller` per module — both matching `design` skill's MODE B/D
package layout so the two skills never disagree about where things live).

For a Tier 2 modular monolith specifically, don't stop at the logical module boundary — apply
`references/modular-monolith.md` §5a's directory/build conventions (independent build entrypoint,
per-module Dockerfile, per-module migration namespace) alongside the stack layout above, so the
system stays cheap to split later without deploying it as separate services today.

## 5. DOCUMENT THE DECISION

Write an **Architecture Decision** — as a new file under `docs/02-architecture/decisions/` (or ask
where the project keeps decision records if a convention already exists) — with this shape:

```markdown
# Architecture Decision: {system/component name}

## Context
[What's being built, and what prompted this decision]

## Scale Tier
[Tier 1/2/3] — [one-line reason from the five classification questions]
Graduation trigger: [the specific signal that would mean re-evaluating this — system-scale-checklist.md §5]

## Axis 1 — Deployment Topology
Decision: [Monolith / Modular Monolith / Microservices]
Reason: [...]
Alternative considered: [...] — rejected because [...]

## Axis 2 — Domain Modeling Approach
Decision: [per bounded context/module — Transaction Script / DDD tactical patterns]
Reason: [...]

## Axis 3 — Communication Style
Decision: [Synchronous only / Async job queue / In-process events / Event-driven via broker]
Reason: [...]

## Stack-Specific Structure
[The chosen pattern from frontend/mobile/backend-script-patterns.md, with the actual folder layout for this project]

## Alternatives Considered
[Any option seriously weighed and rejected, with the reason]
```

**Never skip the "alternative considered" line for any axis** — a decision with no stated
alternative reads as if nothing else was weighed, which a reviewer can't verify either way.
