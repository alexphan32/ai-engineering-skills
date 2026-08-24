# Iterative Deep Mode Workflow

> Reference for `research` skill. Load when using `iterative_deep` mode.

Iterative mode runs 2-3 rounds, each round building on top of the previous one. Purpose: broad coverage first, depth second, resolve conflicts last.

## Round 1 — Broad Coverage

```
DEFINE_QUERIES_R1
  → 5-7 queries covering: overview, technical depth, problems, best practices, community
  → Goal: map the landscape, without going too deep on any single angle
        ↓
SEARCH_AND_TRIAGE_R1
  → WebSearch all queries
  → Choose the 5-7 highest-quality URLs (mix of tiers)
        ↓
DEEP_READ_R1
  → Fetch and extract from the chosen URLs
        ↓
CLAIM_EXTRACTION_R1
  → Extract falsifiable claims from each source (see CLAIM_EXTRACTION above)
  → Tag evidence type: data > anecdote > opinion > assertion
        ↓
SYNTHESIZE_R1
  → Merge claims, dedup URLs, identify consensus & contested points
  → Assign a preliminary confidence rating to claims (see CONFIDENCE TIERS)
  → Flag contested claims
        ↓
SELF_EVALUATE_R1
  Run the self-evaluation checklist:
  ┌─────────────────────────────────────────────────────┐
  │ Coverage check:                                     │
  │   □ Technical depth (implementation, architecture)  │
  │   □ Problems / pitfalls                             │
  │   □ Alternatives / competitors                      │
  │   □ Community / real-world experience               │
  │   □ Recent developments (< 6 months if fast-moving) │
  │                                                     │
  │ Quality check:                                      │
  │   □ Is there a Tier 1 source?                       │
  │   □ Are important claims confirmed by ≥2 sources?   │
  │   □ Are there official docs yet?                    │
  │                                                     │
  │ Gap identification:                                 │
  │   → List explicitly: "Not yet researched: [X], [Y], [Z]" │
  │   → List contested: "Conflict: [A] vs [B]"          │
  └─────────────────────────────────────────────────────┘
  
  Decide what's next:
  - If gaps < 2 and contested = 0 → skip Round 2, go straight to OUTPUT
  - If gaps ≥ 2 or contested ≥ 1 → continue to Round 2
```

## Round 2 — Fill Gaps

```
DEFINE_QUERIES_R2
  → Create targeted queries ONLY for gaps and contested points found in Round 1
  → Do not re-search what was already covered well in Round 1
  → 3-5 queries, each query addressing 1 specific gap
        ↓
SEARCH_AND_TRIAGE_R2 → DEEP_READ_R2
  → WebSearch + WebFetch for the targeted queries
  → Prioritize sources different from Round 1 to avoid an echo chamber
        ↓
SYNTHESIZE_R2
  → Merge with R1 findings
  → Update contested points: were they resolved?
        ↓
SELF_EVALUATE_R2
  ┌─────────────────────────────────────────────────────┐
  │ Gap resolution check:                               │
  │   → For each gap from R1: Filled? Partially? Still open? │
  │                                                     │
  │ Contested resolution check:                         │
  │   → For each contested point: Resolved? Still contested? │
  │   → Severity: High / Med / Low for each contested point │
  └─────────────────────────────────────────────────────┘
  
  Decide what's next:
  - If no high-severity contested points remain → go to OUTPUT
  - If ≥2 high-severity contested points remain → continue to Round 3
```

## Round 3 — Resolve Conflicts (conditional)

[Only runs if ≥2 high-severity contested points remain after Round 2]

```
DEFINE_QUERIES_R3
  → Extremely targeted queries: each query aims at 1 specific contested claim
  → Look for: primary sources, case studies, benchmarks, post-mortems
  → Maximum 3 queries
        ↓
DEEP_READ_R3
  → Prioritize Tier 1 sources to resolve conflicts
  → Approach: active refutation — try to FIND EVIDENCE TO REFUTE each contested claim,
    not just supporting evidence. If it can't be refuted → the claim gets stronger.
  → If a genuine conflict remains after R3: present BOTH views with evidence for each side,
    assign confidence ⚡ Contested, don't decide on the user's behalf
        ↓
FINAL_ADVERSARIAL_VERIFICATION
  → For all CRITICAL claims (from R1+R2+R3): run ADVERSARIAL_VERIFICATION
  → Assign a final confidence rating (✅ ⚡ ⚠ ⚡ ❌) to each critical claim
  → Drop ❌ Refuted claims
        ↓
FINAL_CRITIQUE_LOOP
  → Look back over the entire research (R1 + R2 + R3):
    1. "What assumption have I still not challenged?"
    2. "Is there any bias? (e.g., too many sources from 1 vendor?)"
    3. "What would the user ask that this report hasn't answered?"
    4. "Is there a claim tagged ✅ Verified that actually only has 1 perspective?"
  → Note in Gaps & Limitations if issues remain
        ↓
OUTPUT
```
