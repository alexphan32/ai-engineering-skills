# UPGRADE — Full Workflow

Step-by-step detail for MODE: UPGRADE (evaluate and evolve an existing architecture). Loaded once
UPGRADE is the confirmed mode — see `SKILL.md`'s HOW TO USE for mode detection and the condensed
step list.

For a system that already has an architecture and either shows a real strain signal or the user
wants it re-evaluated.

---

## 1. UNDERSTAND CURRENT STATE

- If no architecture docs exist yet, or they're stale: run `explore-workflow.md`'s SCAN + DEEP_DIVE
  (at minimum) to build an accurate current-state model before proposing anything — recommending a
  change against an assumed-but-wrong current state is worse than not recommending one.
- If docs exist and are current: read them, especially `02-module-architecture.md` and any prior
  "Issues Discovered" section.

## 2. IDENTIFY THE TRIGGER

State explicitly what's prompting this — don't skip straight to a recommendation:
- A `system-scale-checklist.md` §5 graduation trigger has actually fired (new team needing
  independent deployability, a new external critical-system integration, a stated compliance
  requirement)?
- A concrete pain point (deploy contention between teams, a module whose changes keep breaking
  unrelated ones, a specific incident)?
- Or is this "the codebase feels big/old" with no concrete signal — in which case say so, and
  weigh whether a change is actually warranted (§6 anti-patterns in `microservices.md` and
  `event-driven-architecture.md` apply to *unnecessary* upgrades just as much as to premature
  initial choices).

## 3. RE-CLASSIFY

Re-run `references/system-scale-checklist.md` §0 against the *current* reality, and re-walk the
three axes (`references/architecture-selection.md`) the same way MODE: SELECT does. State whether
the Tier/axis answers actually changed, or whether the trigger in step 2 doesn't actually move the
classification — a real answer either way, not an assumption that "we've grown, so it must have."

## 4. RECOMMEND THE TARGET AND THE DELTA

State the target architecture (same three-axis shape as MODE: SELECT's output) and the specific
delta from the current state — which modules/boundaries change, not just the end state.

## 5. PLAN THE MIGRATION — Incremental, Never Big-Bang

Default to an incremental path; a full rewrite needs an explicit, stated reason it's actually
cheaper than incremental extraction (it rarely is):

```text
Strangler Fig            — route an increasing share of traffic/calls to the new implementation
                            while the old one still handles the rest, until nothing depends on the
                            old path and it can be removed.
Branch by Abstraction     — introduce an interface in front of the piece being replaced, migrate
                            callers to the interface, swap the implementation behind it, then
                            remove the abstraction if it's no longer earning its keep.
Extract by Bounded Context — for a monolith → microservices step, use the Context Map
                            (`domain-driven-design.md` §1) to find the seam with the fewest and
                            simplest cross-boundary dependencies first — that's the cheapest,
                            lowest-risk service to extract, and validates the approach before a
                            harder extraction is attempted. Check whether the module already has
                            the directory/build properties in `modular-monolith.md` §5a (its own
                            build entrypoint, Dockerfile, migration namespace) — if not, doing that
                            split first, while the module is still in-process, is itself the
                            lowest-risk first step. Then load the "Extraction Mechanics" note at
                            the end of the relevant stack's section in `backend-script-patterns.md`
                            for what concretely moves as-is vs. what needs a new adapter.
Event-Carried State Transfer / dual-write-then-cutover
                          — for decoupling data during an extraction: the old and new stores stay
                            in sync via events during a transition window, with a defined cutover
                            point and rollback plan, rather than one atomic data migration.
```

Each step in the plan should be independently shippable and independently reversible — if step 3
of 5 turns out to be wrong, steps 1–2 should still be a net improvement on their own, not a
half-finished migration stuck mid-flight.

## 6. DOCUMENT

Same Architecture Decision shape as MODE: SELECT §5 (in `select-workflow.md`), plus a **Migration
Plan** section: the ordered steps from §5 above, what stays synchronous vs. eventually-consistent
during the transition, and the rollback point for each step.
