---
name: brainstorming
description: >
  Use when it's unclear which skill applies, a request spans multiple lifecycle phases, or before
  non-trivial work to size how much process it needs — "không biết nên bắt đầu từ đâu", "quy
  trình build feature này gồm những bước nào", "which skill should handle this". Also use to look
  up the Implementation Readiness gate contract (READY/PARTIALLY_READY/BLOCKED) shared by `/spec`,
  `/design`, `/implement`, `/review`. Do NOT use when the right skill is already obvious. Classifies
  and routes; never does the work itself.
---

## OVERVIEW

Front door for this skill library. Every other skill here owns one phase of the lifecycle and
assumes it's invoked at the right time, with the right ceremony already sized. `/brainstorming`
decides both "which skill" and "how much process" — for a multi-phase request, an unfamiliar
shape of ask, or one that names an outcome ("ship feature X") rather than a phase ("write an SRS
for X").

**Naming note:** this isn't superpowers' `brainstorming` — it doesn't explore ideas, propose
approaches, or add its own approval gate; those stay owned by `/spec` and `/design`, which already
have their own gates. What it borrows from superpowers is the *shape*: classify the ceremony a
request needs before routing, instead of pattern-matching request text against a flat table.

**Core principle:** `/brainstorming` never substitutes for the skill it routes to. It identifies
the tier and sequence, then hands off — the receiving skill still runs its own gates in full. If
`/brainstorming` finds itself drafting an SRS or writing code, it has stopped being a router.

---

## THE THREE TIERS

Classify before routing — say the tier out loud so the request's actual shape stays visible:

| Tier | Shape | Route to |
|---|---|---|
| **Spike** | A feasibility/orientation question — "does this already exist," "is X possible here," comparing libraries/approaches. Output is an answer, not a document. | `/discovery` (an internal question) or `/research` (external: libraries, frameworks, fact-checking) |
| **Bounded** | A well-scoped change to something that already exists — no new requirements decision needed. | `/implement` directly (or `/test`/`/review` if that's literally the ask). If it changes an *existing* feature's business behavior, not just its code, → `/spec` in CHANGE MODE first — that's still a requirements decision |
| **Architectural** | A new module/feature/system, or requirements that are unclear or don't exist yet — needs a topology decision inside a build, not instead of one. | Full chain: `/discovery` (if unfamiliar) → `/spec` → `/design` (+ `/architecture` if topology isn't decided) → `/implement` → `/test` (if needed) → `/review` → `/operate` |

**Decision test when the tier isn't obvious:** ask "is the gap in WHAT should happen (spec-shaped
→ Architectural), HOW it should be built (design-shaped → Architectural), or just getting it
written (implement-shaped → Bounded)?" — the answer usually collapses the ambiguity.

**When the request itself doesn't say enough to even run that test** (no target system, no
named entity/actor, no shape of outcome — "build me a rewards thing," "make onboarding better"):
ask ONE clarifying question before guessing a tier, pairing it with your own best guess so the
user is confirming/correcting rather than starting from a blank page. Don't default straight to
Architectural on a vague ask just because it's the safe-sounding choice — a wrong classification
made confidently is exactly the kind of thing the misclassification red flags below exist to catch.

Three request shapes cut across all three tiers rather than picking one:
- **A pure architecture question with no feature attached** — "explain/document this whole
  system," "should we split this into microservices," "monolith vs. microservices for a new
  service" — → `/architecture` alone (EXPLORE/SELECT/UPGRADE as fits), not the full chain. Only
  route through the full chain when a topology decision is a *step inside* building something,
  not the entire ask.
- **"Review this file/PR/SDS/architecture"** → `/review` regardless of tier — it auto-detects
  CODE/SDS mode itself, or defers to `architecture` UPGRADE for a whole-system ask.
- **Deploying, monitoring, incident, rollback, DR** → `/operate` regardless of tier.
- **A request naming more than one independently shippable capability** — e.g. "build user
  management" turning out to be registration + profile + permissions + audit — decompose before
  routing: run each capability through its own spec→design→implement chain, sequenced by
  dependency, instead of one oversized `/spec` call trying to cover all of them at once. This is
  still classification, not design work — naming the capabilities and their order, then handing
  each off, is as far as `/brainstorming` goes.

And one shape needs no tiering at all: **genuinely spans two phases with no clear split** (e.g.
"spec and design this together") — run them in order anyway. `/design` cannot start until
`/spec`'s gate is checked, so sequence holds even under one combined request.

**The ratchet is one-way:** hidden complexity discovered mid-request upgrades the tier — stop,
say so, and route to the heavier chain. Nothing downgrades mid-request; a Bounded fix that turns
out to touch a business rule becomes Architectural (→ `/spec`) the moment that's discovered, not
after `/implement` has already guessed the answer.

**Misclassification red flags** — each is a reason to take the heavier tier, not a reason to skip it:

| Thought | Reality |
|---|---|
| "This is obviously Bounded, I know this kind of codebase" | Bounded means the specific flow you're changing is already in this repo and you've read it — not that you recognize the app's kind. Haven't read the actual code? That's Spike/`/discovery` first. |
| "I'll call it Bounded so I can skip the spec step" | Reaching for a label to avoid work is the doubt itself — take the Architectural tier instead. |
| "The scope grew mid-implementation but I'm almost done" | Hidden complexity upgrades the tier — stop and route to `/spec`/`/design` before continuing, per the ratchet above. |
| "The user just wants an answer fast, skip stating the tier" | State it anyway — it's the cheapest way for them to catch a wrong classification before work starts at the wrong scope. |
| "The request is vague, I'll just guess Architectural to be safe" | A guessed tier — heavy or light — is still a guess. Ask one question with your best-guess answer attached before routing, rather than defaulting to the safe-sounding tier. |

---

## THE LIFECYCLE

```
discovery (if unfamiliar) → spec (WHAT) → design (HOW, auto-detects stack) → implement (code +
inline unit tests) → test (coverage beyond that inline loop, when needed) → review (auto-detects
CODE | SDS mode) → operate (deploy, observe, respond)
```

`architecture` and `research` aren't steps in this chain — each is consulted from whichever phase
needs it: a `/design` decision needing a framework comparison calls `/research`; an unfamiliar
system needing full documentation, a new system needing its topology/domain-model/communication
style decided, or an existing one needing a fit re-check all call `/architecture`.

---

## THE IMPLEMENTATION READINESS GATE

`spec`, `design`, and `implement` are chained by a shared gate that each writes into its own
output document, and the next skill in the chain must check before proceeding:

| Gate | Meaning | What the next skill must do |
|---|---|---|
| `READY` | No unresolved `[OPEN QUESTION]` (spec's own blocking label) or `[NEEDS SPEC CLARIFICATION]` (design's label for a business question it hit) on anything in scope | Proceed normally |
| `PARTIALLY_READY` | Some sections blocked, others clear | Proceed only on the ready scope; state what's deferred and why |
| `BLOCKED` | An unresolved item sits on the primary flow, core data model, or a cross-cutting concern | **Stop.** Report the unresolved blocking question(s); do not guess an answer in code |

This gate exists so an unresolved business or design question gets surfaced as a labeled question
in a document, not silently resolved by whoever implements it next guessing an answer. When
orchestrating a multi-phase (Architectural-tier) request, `/brainstorming` should state the
current gate status before handing off to the next phase — never assume `READY` because the
previous phase "seemed done."

---

## ENGINEERING PRINCIPLES FOR THIS LIBRARY

Only relevant when *editing* a skill in this repo, not for ordinary routing — load
`references/engineering-principles.md` for that case (labeling discipline, stack-detection over
hardcoding, gates aren't suggestions, evidence before assertions).

---

## RELATIONSHIP TO OTHER SKILLS

`/brainstorming` is the only skill here allowed to name *another* skill as its output without
doing that skill's work. Every other skill either does its own phase's work directly or, like
`/review`, routes within a single phase (code vs. SDS vs. architecture) — never across the whole
lifecycle.
