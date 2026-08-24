# Ambiguity Detection & Assumption Management

> Reference for `spec` skill — load during ANALYZE and before FINALIZE.

Requirements text is where vague language does the most damage: once a vague word survives
into an SRS, every downstream reader (design, implementation, test) resolves it differently,
and each resolution looks locally reasonable. The fix isn't a style rule — it's forcing every
vague word into either a number, a `[DECISION]`, or an `[OPEN QUESTION]` before the SRS is
considered done.

## 1. Dangerous words — scan for these before DRAFT and again before FINALIZE

If any of these appear in a requirement, business rule, or NFR, it is not draftable as-is.
Either the user already gave you the concrete value elsewhere in the conversation (use it),
or it becomes an `[OPEN QUESTION]` — never silently resolved by picking a "reasonable" number.

| Vietnamese | English | Resolve to |
|---|---|---|
| fast, real-time, almost instant | fast, real-time, instant | measurable latency (e.g. "P95 < 200ms") |
| large, many, some | large, many, some | a number or range |
| usually, typically | usually, typically | the actual rule for the exception case |
| may/can | may/can (ambiguous permission or optionality) | MUST / MUST NOT, or explicit optional with default |
| appropriate, ensure, reasonable | appropriate, ensure, reasonable | the specific condition being guaranteed |
| handle appropriately | handle gracefully | the exact behavior, status code, or state transition |

**Example:**
> "The API must respond fast." → not draftable.
> Ask: "Does 'fast' mean P95 < 200ms, or is there a different threshold?" → becomes NFR-01 with a number, or `[OPEN QUESTION]` if the user doesn't know yet.

This list isn't exhaustive — the pattern is what matters: any adjective/adverb describing
magnitude, speed, or correctness without a number or explicit rule behind it is a red flag.

## 2. Assumption labels

Every non-trivial statement in the SRS traces to exactly one of these. Mixing them up is the
single biggest way an SRS silently turns an AI's guess into a business requirement.

| Label | Meaning | Who said it |
|---|---|---|
| `[REQUIRED]` | User explicitly stated this | User, verbatim or close paraphrase |
| `[CONFIRMED]` | User/stakeholder confirmed when asked | User, in response to a clarifying question |
| `[ASSUMPTION]` | Not stated, but needed to make the spec concrete — carries real risk if wrong | You (the drafter) |
| `[OPEN QUESTION]` | Missing information the user hasn't provided | Nobody yet — tracked in the Open Questions table |
| `[DECISION]` | An explicit design/scope choice made to break a tie, with a stated reason | You, with rationale, when the user said "you decide" or the choice is genuinely inconsequential |
| `[NEEDS DESIGN]` | A **technical-mechanics** question, not a business one — how something is built rather than what must be true. Not yours to decide here; hand it to `/design` instead of guessing a mechanism. | You, at the moment you catch yourself specifying HOW instead of WHAT |

`[NEEDS DESIGN]` is the mirror image of `/design`'s `[NEEDS SPEC CLARIFICATION]`
(`.claude/skills/design/references/decision-records.md` §1) — that one flags a business question
design hit that only `/spec` can answer; this one flags a mechanics question spec hit that only
`/design` should answer. Both exist so the boundary between the two skills holds in both
directions: neither skill silently decides a question that belongs to the other.

**Why this matters more than it looks:** `[ASSUMPTION]` and `[DECISION]` look similar in prose
but carry different risk. A `[DECISION]` is fine to ship — the user delegated it or it doesn't
matter which way it goes. An `[ASSUMPTION]` is a guess about *business* behavior that could be
wrong in a way that costs real rework (e.g., "assuming a Maker cannot approve their own
transaction" — if wrong, that's a security-relevant behavior change, not a style tweak).
`[ASSUMPTION]`s on anything touching authorization, money movement, or state transitions should
usually be escalated to `[OPEN QUESTION]` instead of shipped silently — see the Escalation rule
below.

**Escalation rule:** an `[ASSUMPTION]` about authorization, financial amounts, or irreversible
state transitions must not go straight to FINALIZE — convert it to an `[OPEN QUESTION]` and ask,
even if that means the SRS ships as `PARTIALLY_READY`. An `[ASSUMPTION]` about presentation,
wording, or anything easily changed later can ship as-is with the label kept visible so a
reviewer can spot it.

## 3. Requirement Conflict Detection

Before FINALIZE, check pairwise across NFRs, business rules, and stated constraints for
contradictions — most conflicts hide in NFR ↔ dependency pairs, not within a single section.

**Common conflict shapes:**
- A latency/timeout NFR that's shorter than a stated downstream dependency's own response time
  (e.g., "API timeout = 3s" + "Core Banking may take up to 30s" — the API cannot both wait for
  Core Banking and enforce its own 3s timeout; something must give, usually async processing).
- "Must be synchronous" + a dependency documented as unreliable/slow/rate-limited.
- Two business rules that can both apply to the same case with different outcomes (e.g., "Maker
  cannot approve own transaction" + "single-user tenants must be able to self-approve").
- A stated NFR number that contradicts a number given earlier in the same conversation.

When found, do not silently pick one — write it explicitly:

```
CONFLICT:
NFR-01 (API timeout = 3s) and DEP-02 (Core Banking response up to 30s) cannot both hold if
the flow is synchronous. Resolve by: (a) making this async (202 + polling/webhook), or
(b) raising the timeout, or (c) confirming Core Banking's actual P99. Which?
```

This becomes a blocking `[OPEN QUESTION]` — it cannot be resolved by assumption because the
resolution changes the API contract shape (sync vs async), which downstream design depends on.
