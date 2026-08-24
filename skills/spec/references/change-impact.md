# Change Impact Analysis

> Reference for `spec` skill — load when the request modifies a feature/module that already
> has an SRS (and likely an SDS and code), rather than introducing a brand-new one.

## When this applies

`/spec` normally refuses to run once design/implementation exist for a feature — that guidance
still holds for *new* features. But a request that changes the **business behavior** of an
*existing* feature ("Maker can now edit a transaction after submission", "add a rule that
approval is only allowed within 24h") is still a requirements question, not an implementation question — the risk is
exactly the same as a fresh SRS: guessing the business intent and coding it wrong. Route these
here instead of straight to `/implement`.

**Detection:** the target feature already has an SRS section/file (Glob found it) AND the user's
request describes a change to existing behavior (not a net-new capability with its own actors/
use cases). If genuinely unsure which this is, ask once: "Is this a behavior change to an
existing feature, or a new feature?"

## Workflow

1. **Locate the existing SRS** for the feature (and SDS if present) — read them, don't assume
   from memory what they say.
2. **State the change in one sentence**: what requirement/rule is being added, removed, or
   modified.
3. **Trace the blast radius** — for each of these, state affected / not affected, not just the
   obviously-affected ones:

   ```
   Requirement changed
         ↓
   Affected use cases / user stories
         ↓
   Affected business rules (including ones that might now conflict — see
     ambiguity-and-assumptions.md § Conflict Detection)
         ↓
   Affected state machine transitions (if the entity has a lifecycle)
         ↓
   Affected API contract / data model (flag for /design, don't redesign here)
         ↓
   Affected downstream consumers (other features reading this data/event)
         ↓
   Affected existing tests (flag for /implement, don't rewrite here)
   ```

4. **Classify impact**: `HIGH` (changes a business invariant, state machine, or authorization
   rule — needs design + review before touching code), `MEDIUM` (changes a business rule or
   adds a new field/case within existing structure), `LOW` (wording/validation-message-level,
   no behavior change).
5. **Update the SRS in place** — amend the affected sections (mark what changed vs. what's
   unchanged), don't create a parallel duplicate document. Add a short changelog note if the
   SRS doesn't already have version history.
6. **Hand off**: `HIGH`/`MEDIUM` impact → suggest `/design` to re-derive the technical design
   for affected sections before `/implement` touches code. `LOW` impact → `/implement` directly
   is fine, since no design assumptions are invalidated.

## What NOT to do here

- Don't redesign the API/data model/state machine mechanics — that's `/design`'s job. This step
  only says *which* of those are affected and how much re-design is warranted.
- Don't skip straight to editing code because "it's a small change" — a change that looks small
  in code (one new `if`) can be `HIGH` impact if it touches an invariant (e.g., "allow Approver
  to also be the Maker when tenant has only one user" touches INVARIANT-TXN-002-style rules).
