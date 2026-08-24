---
name: spec
description: >
  Use when adding a new module/feature, when requirements are missing, or when an existing
  feature's business behavior is changing (not just its code) — "viết SRS", "/spec", "thêm rule
  mới", "đổi state machine". Covers Python data-pipeline/script modules and any backend, frontend,
  or mobile feature (Go/Fiber, FastAPI, Rust, Spring Boot, NestJS, Next.js, Angular, React,
  Android, iOS, Flutter) — business requirements are the same shape regardless of the eventual
  stack, which `/design` picks separately. Do NOT use once a design/implementation already exists
  for a *new* feature — go to `/design` instead.
---

# Spec (SRS)

## Overview

Gather requirements → write a Software Requirements Specification. First step in the pipeline: spec → design → implement.

**Core principle:** an SRS makes business behavior unambiguous *before* anyone (human or AI)
invents mechanics to satisfy it. A vague requirement that survives into the SRS gets resolved
differently by whoever reads it next — catching it here costs one clarifying question; catching
it in code review costs a rewrite.

**2 modes — auto-detected:**
- **MODE A**: Python data-pipeline or script/automation module (detected from CLAUDE.md "Module
  Architecture" — same shape whether it's a multi-stage pipeline or a standalone scheduled script)
- **MODE B**: any backend, frontend, or mobile feature — REST/full-stack API (Go/Fiber, FastAPI,
  Rust, Spring Boot, NestJS, Next.js) or a UI feature (Angular, React, Android, iOS, Flutter).
  Business requirements (actors, permissions, user stories, lifecycle, auth) are the same shape
  regardless of which of `/design`'s modes eventually implements it — this skill doesn't need to
  know or ask which stack yet.

**Scope boundary:** this skill owns *business* clarity — actors, rules, invariants, states,
scenarios, unknowns. It does NOT own technical mechanics — authN/authZ implementation,
performance tuning, Saga/idempotency design, DB schema. Those belong to `/design`, checked by
`/review`. Designing *how* instead of *what* must be true? Write `[NEEDS DESIGN]` and move on.

## When to Use

```
User says: "add new module", "write SRS", "/spec", "missing requirements"
           ↓
  Feature already has an SRS + this is a BEHAVIOR CHANGE, not a new capability?
           → CHANGE MODE (see references/change-impact.md) — do this instead of a fresh SRS
           ↓
  CLAUDE.md has "Module Architecture" → MODE A (Python pipeline / script system)
  User says "REST API", "feature", "screen", "F-XX", or names any stack
  (Go/Fiber, FastAPI, Rust, Spring Boot, NestJS, Next.js, Angular, React,
  Android, iOS, Flutter) → MODE B
           ↓
  DETECT → GATHER → ANALYZE → DRAFT → VALIDATE → GATE → FINALIZE
```

**Do NOT use `/spec` when:**
- Technical design is needed (use `/design`)
- Module already has SRS and you just need code with no behavior change (use `/implement`)
- Reviewing existing SRS (use `/review`)

## Reference Templates

Load on demand:

| Topic | File | When |
|-------|------|------|
| Template A (pipeline) | `references/mode-a-template.md` | Drafting MODE A SRS |
| Template B (REST API) | `references/mode-b-template.md` | Drafting MODE B SRS |
| Dangerous-word list, assumption labels, conflict detection | `references/ambiguity-and-assumptions.md` | ANALYZE, and again before GATE |
| Change impact workflow | `references/change-impact.md` | Request modifies an existing feature's behavior |
| Functional Requirement quality bar + worked example | `references/functional-requirement-quality.md` | Drafting FR-XX in DRAFT; checking FR completeness in VALIDATE |

## Workflow (7 Steps)

### 0. DETECT — Project mode & structure

- Read CLAUDE.md → "Module Architecture" section → MODE A
- Glob `docs/03-srs/*.md` for a file that does NOT match `F-*.md` → MODE A (a pipeline SRS
  carries no F-prefix; a bare module-named file is MODE A's signature, since both modes now share
  the same folder)
- User specifies "Go", "Fiber", "FastAPI", "Rust", "Spring Boot", "NestJS", "Next.js", "Angular",
  "React", "Android", "iOS", "Flutter", "REST API", "screen", "F-XX" → MODE B — this skill doesn't
  need to resolve which specific stack; that's `/design`'s DETECT step
- Ambiguous? AskUserQuestion once: "Pipeline/script module, or a backend/frontend/mobile feature?"
- **Change vs. new**: Glob for an existing SRS on this feature. Found, and the request alters
  behavior rather than adding a net-new capability? → CHANGE MODE (`references/change-impact.md`)
  instead of the steps below.

**Discovery (no hardcoded paths):**
- MODE A: Glob `docs/03-srs/*.md` (excluding `F-*.md`) → SRS file; Glob `src/**/*.py` → module paths
- MODE B: Glob `docs/03-srs/F-*.md` → compute next F-XX number

### 1. GATHER — Minimum required info

**MRI checklist — must have ALL before drafting:**

| MODE A (pipeline) | MODE B (REST API) |
|---|---|
| Module purpose (1-2 sentences) | Feature purpose |
| Pipeline level (M-XX) + upstream | Who uses it, per actor: role + explicit permissions (not just "User") |
| ≥1 input column (name + type) | ≥2 user stories |
| ≥1 output column (name + description) | Auth requirement (JWT/public/role) |
| ≥1 config key/threshold | Does the main entity have a lifecycle (states beyond exists/deleted)? |
| — | Sync or async? Can two actors act on the same resource at once? |
| — | Does this call, or get called by, a system this team doesn't control (Core Banking, a third-party API, another team's service)? |
| — | Is there a stated compliance/audit/uptime requirement, or is this explicitly an internal/pilot/low-stakes tool? |

**Why these four exist:** business facts, not implementation detail — silence forces `/design` to
guess or re-ask; the last two feed its Scale Tier classification directly
(`.claude/skills/architecture/references/system-scale-checklist.md` §0).

**Termination**: If MRI satisfied from user's initial request → skip questions, go to ANALYZE.
If ≥2 items missing → AskUserQuestion ONE time with only the missing items.

**Exception — genuinely open-ended ask** (a request that names an outcome but not a shape, e.g.
"add a rewards system" with no actor/entity/lifecycle implied by the wording): a single batch of
questions here tends to get short, low-effort answers precisely because the requester hasn't
formed the shape yet either. Switch to asking one question at a time instead, each paired with
your own best guess at the answer ("I'm guessing rewards accrue per completed order, not per
signup — is that right?") so the requester is confirming/correcting rather than generating from
scratch. Stop once you could state the MRI checklist's remaining items yourself with reasonable
confidence — don't turn this into an open-ended interview once the batch would work.

### 2. ANALYZE — Extract structure

- **MODE A**: Input schema, output schema, config keys, business rules, pipeline dependencies
- **MODE B**: User stories (US-01…), functional requirements (FR-01…), NFRs, business rules.
  Every FR needs a Main Flow and Error Handling, not just a restated User Story — see
  `references/functional-requirement-quality.md` if it would otherwise be just Description +
  Priority.
- **Capability scope check** (MODE B, before drafting FRs): if the emerging FR list spans more
  than one independently shippable capability with distinct primary actors or lifecycles — e.g.
  "user management" turning out to be registration + profile + permissions + audit in one draft —
  stop and split into separate `F-XX-a`, `F-XX-b`... SRS files, one per capability, each gated
  independently in GATE. Share only cross-referenced Business Invariants across them; don't let a
  single SRS grow just because the request named one feature. FRs that don't share a primary
  actor or lifecycle are the signal — not FR count alone.
- **Submodule check** (MODE B, and MODE A when a pipeline module's stages carry their own business
  rules): don't confuse this with the capability scope check above — a submodule is still ONE
  capability, sharing the same primary actor(s)/lifecycle/invariants, but naturally decomposes
  into stable internal sub-flows (e.g. F-05 "Order Management" containing Order Creation,
  Fulfillment, and Cancellation as sub-flows of the same order lifecycle, not separate
  capabilities). When that internal structure is real and stable — not just "this file got long"
  — split into `F-XX.1-sub-name.md`, `F-XX.2-sub-name.md`... keeping `F-XX` itself as a thin
  parent: shared actors/permissions, the Business Invariants spanning all sub-flows, and a table
  pointing to each submodule file. Each submodule gets its own FRs/acceptance criteria and its own
  GATE status; the parent's readiness rolls up from its children — `READY` only when every
  submodule is `READY`. The dot notation (`.1`, `.2`) keeps this visually distinct from the
  hyphen-lettered sibling split (`-a`, `-b`) above — a reader should tell "independent capability"
  from "sub-flow of one capability" from the filename alone.
- **Philosophy check**: Glob `docs/00-context/*.md` → check against core principles → flag violations
- **Ambiguity scan**: check every requirement/rule/NFR draft against the dangerous-word list
  (`references/ambiguity-and-assumptions.md` §1) before DRAFT. A flagged word isn't a requirement
  yet — resolve it to a number you already have, or an `[OPEN QUESTION]`.
- **Business Invariants** (MODE B, and MODE A when applicable): keep separate from Business
  Rules. A Rule gates one action ("Maker MUST NOT approve their own transaction"); an Invariant
  holds across *every* flow and state, forever ("A transaction MUST NOT be financially applied
  more than once"). Mixing them hides invariants inside a rule list, where a later unrelated
  change can violate them. Find invariants with **First Principles**: strip away the current
  flow/UI/API shape and ask what must hold true regardless of how the action is triggered — that's
  the test for whether a statement belongs here rather than in Business Rules.
- **State Machine & Transition Matrix** (MODE B, only if GATHER flagged a lifecycle): every
  state, plus a `Current → Action → Actor → Condition → Next` table. This is the *business*
  state machine — `/design` derives the technical one (retries, compensation) from it. "The
  states are obvious" is exactly where an unstated transition (can REJECTED be resubmitted?)
  gets silently decided by whoever writes the code.
- **External systems & compliance signal** (MODE B): populate the Dependencies table's "Team
  Controls It?" column and NFR-04 (Compliance & Availability) from what GATHER already collected
  — don't leave these implicit even when the answer is "no external system"/"not stated." A
  silent Dependencies section reads as forgotten, not confirmed.
- **Edge cases — required categories, don't wait for the user to list them**: duplicate
  request/submission, empty/zero/negative/maximum input, expired/stale resource, concurrent
  action on the same resource, an actor acting on their own disallowed resource, permission
  changed mid-flow, and (MODE B) downstream timeout/lost response. Each gets an explicit
  yes/no/N/A, not silence. Beyond this fixed list, apply **Inversion** — ask "what input, actor,
  or timing would break this rule?" — to surface the next edge case a checklist can't anticipate.
- **Assumption labeling**: tag every non-`[REQUIRED]`/`[CONFIRMED]` statement `[ASSUMPTION]`,
  `[OPEN QUESTION]`, or `[DECISION]` per `references/ambiguity-and-assumptions.md` §2. An
  `[ASSUMPTION]` touching authorization, money, or an irreversible state transition escalates to
  `[OPEN QUESTION]` — see that file's Escalation rule.

### 3. DRAFT — Write SRS

- **Check existing**: Glob before writing — if section/file exists, ask: "Update or create new?"
- **MODE A**: Load `references/mode-a-template.md`, append section to SRS file
- **MODE B**: Load `references/mode-b-template.md`, create `docs/03-srs/F-XX-feature-name.md`
- If the Submodule check (Step 2) triggered: write `docs/03-srs/F-XX.1-sub-name.md`,
  `docs/03-srs/F-XX.2-sub-name.md`... (each from the same mode template) plus a thin `F-XX` parent
  file, instead of the single file above

### 4. VALIDATE — Quality check

- All output columns/requirements have descriptions
- Config keys have defaults
- **Conflict detection**: check NFRs, business rules, and dependencies pairwise for
  contradictions (e.g. an API timeout shorter than a dependency's own latency) — see
  `references/ambiguity-and-assumptions.md` §3. Found one → write it as `CONFLICT:` and turn it
  into a blocking `[OPEN QUESTION]`, never pick a side silently.
- MODE B: Every user story has ≥1 acceptance criteria (Given/When/Then), every FR traces to ≥1 US
- MODE B: Every FR states a Main Flow and Error Handling, not just Description + Priority — see
  `references/functional-requirement-quality.md`
- MODE B: Every Business Rule and Invariant is deterministic/testable (no "handle appropriately")
- MODE B: Dependencies table states "Team Controls It?" for every row (never left blank), and
  NFR-04 explicitly answers audit/retention/availability — "not stated" is acceptable, blank is not
- MODE B: §8 Out of Scope names genuine deliberate exclusions (a capability someone could
  reasonably assume is included, plus why it isn't) — not left as a template placeholder, and not
  a restatement of §1.3's In Scope list

### 5. GATE — Implementation Readiness

Before writing/reporting, classify the SRS:

- **READY**: no blocking `[OPEN QUESTION]`s remain (an `[ASSUMPTION]` that didn't need
  escalation is fine — it's visible in the doc for a reviewer to catch).
- **PARTIALLY_READY**: blocking questions exist, but they're scoped to specific
  sections/use-cases — say which parts `/design` can safely start on and which are blocked.
- **BLOCKED**: a blocking question touches a core actor, invariant, or the primary flow — no
  part of this feature should go to `/design` yet.

State this explicitly in the SRS itself (a short "Implementation Readiness" block: status +
blocking questions + critical assumptions), not just in your chat response — the next reader
of the file needs it as much as the current user does.

### 6. FINALIZE — Save & handoff

- Write/update file
- Report: readiness status, columns/configs/questions count
- **Next step**: `Run /design <module-name> to design the technical solution` (only unblocked
  for READY/PARTIALLY_READY scope — say so explicitly if BLOCKED)

## Rules

**Prohibited:**
- ❌ Skip GATHER (no SRS without business context)
- ❌ Vague language: "may", "should" → use "must", "shall", "required" (full list: `references/ambiguity-and-assumptions.md`)
- ❌ Accept non-measurable/non-testable requirements
- ❌ Hide open questions (list explicitly)
- ❌ Silently resolve a requirement conflict by picking one side — flag it as `CONFLICT:`
- ❌ Ship an `[ASSUMPTION]` about authorization/money/irreversible state as if it were `[CONFIRMED]`
- ❌ Merge Business Rules and Business Invariants into one undifferentiated list
- ❌ Mark a spec `READY` while a blocking question touches a core actor, invariant, or primary flow
- ❌ MODE B: SRS without acceptance criteria per user story
- ❌ MODE B: an FR that just restates its User Story with no Main Flow or Error Handling
- ❌ MODE B: skip the State Machine/Transition Matrix when the entity has a lifecycle
- ❌ Design technical mechanics here (auth implementation, retries, schema) — flag `[NEEDS DESIGN]` and defer to `/design`
- ❌ Hardcode project-specific paths — always discover via CLAUDE.md or Glob

**Required:**
- ✅ Detect mode from project structure (not project name)
- ✅ Detect CHANGE MODE when the feature already has an SRS and the request alters behavior
- ✅ MODE A: Glob existing SRS to avoid conflicts
- ✅ MODE A: Spec input columns (type, required/optional)
- ✅ MODE A: Spec output columns (type, description)
- ✅ MODE A: Define config keys with defaults
- ✅ MODE B: Every US has ≥1 acceptance criteria (Given/When/Then)
- ✅ MODE B: Every FR traces to ≥1 user story
- ✅ MODE B: Every actor lists explicit permissions, not a bare "User"
- ✅ Business rules and invariants must be unambiguous and labeled separately
- ✅ Every requirement/rule/NFR traces to `[REQUIRED]`/`[CONFIRMED]`/`[ASSUMPTION]`/`[DECISION]`, or lives in Open Questions
- ✅ State the Implementation Readiness gate (READY/PARTIALLY_READY/BLOCKED) before handoff
- ✅ MODE B: State whether the feature depends on a system the team doesn't control, and whether a compliance/audit/availability requirement exists — explicitly, even when the answer is "no"/"not stated"
- ✅ MODE B: Populate §8 Out of Scope with real exclusions someone could plausibly assume are in — the most valuable single section for a reader deciding what NOT to build, not an afterthought

## Mistakes & Rationalizations — Go back to GATHER, ANALYZE, or GATE

| Mistake / tempting thought | Fix |
|---|---|
| Skipping GATHER because "the user already knows the requirements" | Run the MRI checklist anyway — confirm nothing's missing |
| Assuming the mode, or that output columns match a previous module | DETECT and verify — don't carry an assumption from a different module |
| Inventing config keys without user input | Mark `[ASSUMPTION]`/`[OPEN QUESTION]`, not a bare default |
| Overwriting an existing SRS section, including "for speed" on a change request | Glob first, AskUserQuestion if it exists; a behavior change goes through CHANGE MODE, never a silent overwrite |
| Accepting "it should be fast" as an NFR, or a requirement that "isn't measurable but it's obvious" | Demand measurable: "< 200ms p95," not "fast" — or remove it |
| Drafting before ANALYZE | ANALYZE catches contradictions and missing invariants before they reach the document |
| An FR that just rewords its User Story | Add Trigger, Main Flow, Error Handling — see `references/functional-requirement-quality.md` |
| Treating a business invariant as just another business rule | Pull it into its own section — invariants get violated by *later, unrelated* changes precisely because they were buried |
| "This business rule is obvious, no rationale needed," or marking READY because "the open questions are minor" | Add rationale, or check what a question actually touches — one question about self-approval outranks five about copy text |
| Leaving Dependencies/NFR-04 blank because "no external calls here" | State it explicitly — silence reads as forgotten, not confirmed |
| Assuming two NFRs/dependencies "surely" don't conflict | Check pairwise before drafting |
| "This assumption is surely correct" on something touching auth/money/irreversible state | Escalate to an Open Question, never guess |
| Leaving §8 Out of Scope as the template placeholder, or "In Scope already implies what's out" | Name the specific things a reader could plausibly assume are included but aren't — that's the section's whole value |
| Batching every missing MRI item into one question round for a genuinely open-ended ask | Switch to one-question-at-a-time with your own guess attached — a big batch to an unformed idea gets rushed, low-effort answers |

**REQUIRED NEXT STEP:** the SRS is a contract for *what* must be true, not *how* — hand off to
`/design` for the mechanics, scoped to whatever part of the readiness gate allows.
