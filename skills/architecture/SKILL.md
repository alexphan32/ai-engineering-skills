---
name: architecture
description: >
   Use whenever a system's architecture needs to be understood (EXPLORE — document/onboard),
   chosen (SELECT — monolith vs. microservices, DDD, event-driven, or a stack-specific structure
   for a new system), or re-evaluated (UPGRADE — split/migrate an existing one) — "phân tích kiến
   trúc", "chọn kiến trúc hệ thống", "nâng cấp kiến trúc", "microservices hay monolith", "how
   should I structure this Go/FastAPI/Next.js project" (even without the word "architecture").
   Auto-discovers the stack; works for any language/framework, including Angular, React, mobile,
   and script/CLI tools.
---

## HOW TO USE

**Three modes — detect which one the request needs before doing anything else:**

| Mode | When | Trigger phrases |
|---|---|---|
| **EXPLORE** | Document/understand a system that already exists | "analyze architecture", "explain this codebase", "onboard me", "document this project" |
| **SELECT** | Choose an architecture for a new system, service, or component — nothing built yet, or the shape isn't decided | "what architecture should I use", "monolith or microservices", "should I use DDD here", "how should I structure this Angular/FastAPI/Flutter project" |
| **UPGRADE** | An architecture already exists and may need to change | "should we split this into microservices", "migrate to event-driven", "our monolith is getting hard to manage", "is this still the right architecture" |

SELECT vs. UPGRADE ambiguous (e.g. "design the architecture for this feature" in a codebase with
other features)? Check whether the target already has an established pattern to extend
(UPGRADE-adjacent) or is genuinely new ground (SELECT). Prefer extending the existing pattern
unless the request explicitly asks to reconsider it — same principle `design` uses.

**Reached from:** `/discovery` (EXPLORE) when the ask is "document the whole system," not a
bounded orientation pass. `/spec`/`/design` (SELECT, or UPGRADE for an existing system) when a
topology/domain-modeling/communication-style decision surfaces that neither owns. Hands output —
the 7-file set or an ADR — back to whoever sent the request; doesn't route onward itself.

**Input (optional, any mode):**
- Limited scope: only specific modules/components
- Output directory: defaults to `docs/02-architecture/` — can be overridden
- Update mode: only update a specific section in existing docs

**When to use:**
- Onboarding a new member who needs to understand the system quickly (EXPLORE)
- Architecture docs have become outdated after many iterations (EXPLORE)
- Starting a new system/service/component and the topology, domain-modeling approach, or
  communication style isn't decided yet (SELECT)
- Picking the idiomatic structure for a specific stack — Angular, React, Android, iOS, Flutter,
  Rust, FastAPI, or a script/CLI tool (SELECT)
- A monolith is showing a real scale signal and might need to split, or an existing system's
  architecture should be re-evaluated against how it's actually being used now (UPGRADE)

---

## REFERENCE FILES

Load on demand — never load all of these for one request:

| Topic | File | When |
|---|---|---|
| EXPLORE full workflow (SCAN/DEEP_DIVE/SYNTHESIZE/DOCUMENT/VALIDATE steps + update-mode for stale docs) | `references/explore-workflow.md` | MODE: EXPLORE — load as soon as this mode is confirmed |
| SELECT full workflow (GATHER_CONTEXT/CLASSIFY/AXES/STACK_PATTERN/DOCUMENT steps) | `references/select-workflow.md` | MODE: SELECT — load as soon as this mode is confirmed |
| UPGRADE full workflow (UNDERSTAND/TRIGGER/RE-CLASSIFY/RECOMMEND/MIGRATE/DOCUMENT steps) | `references/upgrade-workflow.md` | MODE: UPGRADE — load as soon as this mode is confirmed |
| Document templates (7-file EXPLORE output) | `references/document-templates.md` | MODE: EXPLORE, step DOCUMENT |
| System scale & architecture fit checklist | `references/system-scale-checklist.md` | **Load first** in MODE: SELECT/UPGRADE, before any other reference below — classifies Tier 1 (MVP) / Tier 2 (Async-Growing) / Tier 3 (Enterprise-Distributed), which drives every other decision in this skill. Also loaded by `design` during its own ANALYZE step — one shared classification |
| Architecture selection decision framework | `references/architecture-selection.md` | MODE: SELECT/UPGRADE, immediately after Tier classification — walks the three independent axes (topology / domain modeling / communication style) and routes to the detail file for each |
| Modular monolith | `references/modular-monolith.md` | Axis 1 lands on monolith/modular monolith (Tier 1/2, the common case) |
| Microservices | `references/microservices.md` | Axis 1 lands on microservices (Tier 3 only) |
| Domain-driven design | `references/domain-driven-design.md` | Axis 2 — evaluating or applying DDD strategic/tactical patterns |
| Event-driven architecture | `references/event-driven-architecture.md` | Axis 3 — evaluating or applying event-driven communication, in-process or cross-service |
| Frontend patterns (Angular, React) | `references/frontend-patterns.md` | Stack detected as Angular or React |
| Mobile patterns (Android, iOS, Flutter) | `references/mobile-patterns.md` | Stack detected as Android, iOS, or Flutter |
| Backend & script patterns (Rust, FastAPI, Go/Fiber, Spring Boot Java, scripts/CLI) | `references/backend-script-patterns.md` | Stack detected as Rust, FastAPI, Go/Fiber, Spring Boot (Java), or a standalone script/CLI tool |

---

## GOALS

* **Accuracy first**: All information must be read from actual source code — no guessing, no fabricating
* **Completeness**: Cover all components/modules of the project (EXPLORE), or all three decision axes (SELECT/UPGRADE)
* **Right-sized, not maximal**: recommend the architecture the Scale Tier and domain complexity actually justify — matching `system-scale-checklist.md`'s anti-over-engineering stance is as much a goal as covering every pattern
* **Navigability**: Documentation has cross-references, so the reader knows where to look next
* **Maintainability**: Every claim has a source ref → easy to update when code changes
* **Actionability**: The reader can start contributing (EXPLORE) or implementing the decision (SELECT/UPGRADE) after finishing reading

---

## MODE: EXPLORE — Document Existing Architecture

5 steps — full detail, per-language glob/grep patterns, and the update-mode flow for stale docs
are in `references/explore-workflow.md` (load it now):

1. **SCAN** — discover project structure: root indicators, source roots, existing docs, entry points
2. **DEEP_DIVE** — read each module/component in detail: entry point, public API, data models, config
3. **SYNTHESIZE** — build the dependency graph, data-flow trace, and cross-cutting-pattern picture
4. **DOCUMENT** — write the 7-file output set (see OUTPUT STRUCTURE below; templates in `references/document-templates.md`)
5. **VALIDATE** — coverage/accuracy/navigability checklist against the actual source

If the output directory already exists with stale docs, `explore-workflow.md`'s UPDATE MODE
section covers re-running SCAN, diffing against the existing docs, and updating only what changed.

---

## MODE: SELECT — Choose an Architecture

For a new system, service, or component where the topology/domain-modeling/communication approach
isn't decided yet, or the user asks "how should I structure this." 5 steps — full detail in
`references/select-workflow.md` (load it now):

1. **GATHER_CONTEXT** — target stack, adjacent existing services/modules, greenfield inputs if none
2. **CLASSIFY_SCALE_TIER** — Tier 1/2/3 via `references/system-scale-checklist.md` §0; everything below depends on this
3. **WALK_THE_THREE_AXES** — deployment topology, domain-modeling approach, communication style,
   each with the alternative considered. Use **Inversion** to stress-test each axis choice: ask
   what would make it fail, then check whether that failure mode actually applies at the
   classified Scale Tier — a sharper test than just listing an alternative and moving on
4. **APPLY_THE_STACK_PATTERN** — idiomatic internal structure for the detected stack, inside the topology chosen in step 3
5. **DOCUMENT_THE_DECISION** — write the Architecture Decision (ADR) with all three axes + stack structure + alternatives

---

## MODE: UPGRADE — Evaluate and Evolve an Existing Architecture

For an existing architecture showing a real strain signal, or one the user wants re-evaluated.
6 steps — full detail, the migration-pattern catalog (Strangler Fig, Branch by Abstraction, Extract
by Bounded Context, Event-Carried State Transfer), and the ADR template are in
`references/upgrade-workflow.md` (load it now):

1. **UNDERSTAND_CURRENT_STATE** — build or read the current-state model before proposing anything
2. **IDENTIFY_THE_TRIGGER** — a fired graduation trigger, a concrete pain point, or "no real
   signal" (say so). Apply **Second-Order Thinking**: a trigger that looks urgent today (e.g. one
   bottleneck) can cost more two steps out (e.g. the distributed-transaction problem splitting it
   out introduces) — weigh that downstream cost, not just the immediate pain, before recommending
   the split
3. **RE-CLASSIFY** — re-run the Tier/axis classification against current reality, state what actually changed
4. **RECOMMEND_THE_TARGET_AND_THE_DELTA** — target architecture plus the specific delta from today
5. **PLAN_THE_MIGRATION** — incremental by default; each step independently shippable and reversible
6. **DOCUMENT** — Architecture Decision + Migration Plan section

---

## HARD RULES

* ❌ **DO NOT hardcode** information — every fact must be read from source code or docs
* ❌ **DO NOT guess** function signatures or field names
* ❌ **DO NOT fabricate** rationale if not found in docs (write "inferred" or leave blank)
* ❌ **DO NOT recommend microservices, DDD tactical patterns, or event-driven communication without
  a stated Tier/domain-complexity/async trigger** (`references/system-scale-checklist.md` §6) —
  same anti-over-engineering discipline `design` applies to its own checklists, applied here to the
  architecture pattern itself
* ❌ **DO NOT propose a big-bang rewrite in MODE: UPGRADE** without stating why an incremental path
  (§5) genuinely doesn't apply
* ✅ Every claim in EXPLORE output must have a **source file reference** (path:line or "source: filename")
* ✅ Every axis decision in SELECT/UPGRADE output must state **the alternative considered and why
  it was rejected**
* ✅ Classify the Scale Tier before choosing any pattern along any axis
* ✅ If the source is unclear → read more files before documenting
* ✅ If information conflicts between docs and actual code → **prioritize actual code**
* ✅ Adapt file discovery patterns to the project's language/stack — don't assume Python-specific
  or backend-specific patterns when the target is a frontend or mobile codebase
* ✅ Tag every trigger and axis recommendation in SELECT/UPGRADE `[CONFIRMED — cites the signal]`
  or `[INFERRED — reasoned but no explicit signal]` — a reader deciding whether to act on a
  recommendation needs to know whether it's traced to something concrete or a judgment call, the
  same way EXPLORE's source-file references let a reader tell a sourced fact from a guess
* ✅ Give the ADR a `Status` field (`Proposed`/`Accepted`/`Superseded by ADR-NNNN`/`Deprecated`).
  A later UPGRADE that changes an earlier decision marks the old ADR `Superseded by ADR-{new}`
  rather than deleting or silently ignoring it — the history of why the architecture is what it
  is stays intact

---

## COMMON RATIONALIZATIONS

**Violating any HARD RULE above = violating the spirit of this skill.** Each row is both the
tempting thought and the red flag it produces — stop and go back to source, not past it:

| Rationalization | Reality |
|---|---|
| "This will obviously need to scale eventually, might as well design microservices now" | No stated Tier 3 signal = no microservices. Designing for scale not yet reached is over-engineering, not foresight — check the Scale Tier first. |
| "The docs already describe this module, no need to open the actual file" | Docs go stale, code doesn't lie — when they conflict, code wins. |
| "I can't find why this decision was made, but it's probably for performance" | Fabricated rationale is worse than none — write "inferred" or leave it blank, never invent one that sounds plausible. |
| "This function/field is probably named like the others in this module" | Never guess a signature or field name — read the source, or read more if it's still unclear. |
| "The monolith is struggling, let's just rewrite it as microservices" | Big-bang rewrites are prohibited without stating why an incremental path (Strangler Fig, Branch by Abstraction, etc.) genuinely doesn't apply. |
| "DDD/event-driven is industry best practice, let's apply it here" | Best practice in general ≠ best practice for this Tier/domain-complexity — apply a pattern only when its own trigger fires. |
| "Scope is small (one module), I can skip the Tier classification" | Classify the Scale Tier before choosing any pattern on any axis, even for narrow scope — skipping it is how a small decision locks in the wrong architecture. |
| "The user's request already implies SELECT, no need to check for an existing pattern" | Check for an established pattern to extend before treating it as greenfield — extending what exists is usually cheaper, and skipping the check is how conflicting components get built. |
| "This trigger/recommendation is obviously right, no need to tag it" | Tag it `[CONFIRMED]`/`[INFERRED]` anyway — the reader can't tell a cited signal from a reasoned guess unless it's marked, even when you're confident. |
| "This ADR is being replaced, I'll just delete/overwrite the old one" | Mark the old ADR `Superseded by ADR-{new}` — deleting it erases the record of why the prior decision was made and when it stopped applying. |

**Red Flags — stop and go back to source before continuing:**
- Writing a claim in EXPLORE output with no source file reference
- Recommending microservices, DDD tactical patterns, or event-driven communication with no stated trigger
- Proposing a rewrite instead of an incremental migration path in UPGRADE
- Choosing a pattern along any axis before the Scale Tier is classified
- "Inferring" a rationale that isn't actually written down anywhere in the source
- An axis recommendation or migration trigger with no `[CONFIRMED]`/`[INFERRED]` tag
- Deleting or overwriting a superseded ADR instead of marking it `Superseded by ADR-{new}`

---

## OUTPUT STRUCTURE

**MODE: EXPLORE:**
```
{output_dir}/          ← discovered in SCAN (default: docs/02-architecture/)
├── README.md                   # Index + validation checklist
├── 01-system-overview.md       # Philosophy, goals, high-level Mermaid
├── 02-module-architecture.md   # Module map (Mermaid), module table, per-module details
├── 03-data-flow.md             # Pipeline trace with actual code snippets
├── 04-data-models.md           # Data structure catalog + field tables
├── 05-tech-stack.md            # Stack table + rationale (from project files)
└── 06-configuration-system.md  # Config pattern + examples (from actual code)
```

**Minimum viable output** (if scope is limited):
- README.md + 01-system-overview.md + 02-module-architecture.md is the minimum set
- The remaining files can be created separately in a subsequent session

**Large systems** (roughly >12-15 modules/components): keep `02-module-architecture.md` as an
index — overview Mermaid + module table only — and write each module's per-module detail into its
own `modules/<module-name>.md` file, linked from the table. Same navigability goal as the minimum
viable output above, opposite direction: split for readability instead of cramming every module's
detail into one file just because the template lists one.

**MODE: SELECT / UPGRADE:**
```
docs/02-architecture/decisions/ADR-{NNNN}-{slug}.md   # One Architecture Decision document
                                                     # (§5 of MODE: SELECT / §6 of MODE: UPGRADE)
                                                     # — not the 7-file EXPLORE structure
```

Every ADR opens with a `Status: Proposed | Accepted | Superseded by ADR-{NNNN} | Deprecated`
line, and every axis decision/trigger inside it is tagged `[CONFIRMED]` or `[INFERRED]`. Superseding
an earlier ADR means editing *that* file's Status line, not deleting it — the decisions directory
is an append-and-mark-superseded log, never a place old decisions disappear from.

**Key files reference:** per-language patterns (entry points, data models, config, persistence) are
in `references/explore-workflow.md`'s SCAN (step D) and DEEP_DIVE (steps B/C/D) — reuse those
glob/grep patterns rather than repeating them here.
