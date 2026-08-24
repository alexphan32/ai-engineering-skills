---
name: research
description: >
  Use when researching any topic from the internet — fact-checking claims, evaluating
  technologies, comparing solutions, finding best practices, checking pricing or changelogs,
  or validating assumptions with data beyond the codebase. Use when an agent needs structured
  web-sourced data. Triggers: "research X", "tìm hiểu về Y", "so sánh Z", "best practices W",
  "check project status", or any request for external information.
---

## GOAL

Good research is multi-angled (official docs, community, critics, alternatives), selective (read
deeply, skip noise), structured (decision-ready output), and self-critical (re-check coverage
each round, fill gaps) — not "search and paste."

> **Environment:** Uses `WebSearch`/`WebFetch` (Claude Code web tools). If unavailable, tell the user.

---

<HARD-GATE>
Do NOT output the final report until ALL of these are true:
1. CLAIM_EXTRACTION has run — falsifiable claims extracted from each source (standard/deep/iterative_deep)
2. ADVERSARIAL_VERIFICATION has run for all CRITICAL claims (deep/iterative_deep modes)
3. Every critical claim has an assigned confidence tier (✅ ⚡ ⚠ ⚡ ❌)
4. CRITIQUE_LOOP checklist has fully run (standard/deep/iterative_deep modes)
5. ≥3 sources read (standard/deep) or ≥1 source (quick)
6. No fabricated citations — every URL fetched successfully or explicitly marked "could not access"
7. ❌ Refuted claims removed from Key Findings
8. Sources table complete: URL + Tier + Round + Claims + Summary
</HARD-GATE>

**Violating any gate = violating the spirit of the skill.** Agents are smart and will find loopholes under pressure. These are the most common rationalizations — and why they're wrong:

| Rationalization | Reality |
|---|---|
| "This claim is obviously true, no need adversarial check" | Obvious claims are the most dangerous — they're unexamined assumptions. Verify anyway. |
| "I already read this in another source" | Memory is unreliable. Extract the claim, cite the source, verify independently. |
| "Quick mode doesn't need claim extraction" | Quick mode still needs falsifiable claims. If a claim is critical, it needs an evidence type. |
| "The source is Tier 1, I can trust it" | Even official docs have errors, bias, or outdated info. Cross-check critical claims. |
| "I'll flag the gap and let the user decide" | Flagging gaps ≠ filling them. Try at least 1 targeted query before giving up. |
| "Too many sources, I'll synthesize from memory" | Without claim extraction, synthesis is just paraphrasing from memory. Extract first. |
| "This is just a quick search" | Quick mode still needs ≥2 sources for any important claim; escalate to standard if the topic proves more complex. |
| "I already know this topic" | Anchoring bias. Existing knowledge may be outdated — still search to verify assumptions. |
| "One good source is enough" | Single-source = single point of failure. Critical claims always need ≥2 independent sources. |
| "More sources = better research" | Quality over quantity. 5-7 URLs/round is the sweet spot — too many leads to shallow reading. |
| "I'll just paste what the page says" | Violates the "no copy-paste" constraint. Always extract, paraphrase, and cite. |
| "All sources agree, so it must be right" | Echo chamber — you might be missing dissenting views. Ask: "Who disagrees, and why?" |

**Red Flags — STOP and run the missing gate:**

- Outputting without extracting falsifiable claims from each source
- Citing a claim as fact without checking if another source disagrees
- Skipping adversarial verification because "all sources agree"
- Writing "obviously" or "clearly" without evidence
- A critical claim with only 1 source, left unflagged ⚠
- No counter-perspective sought for the main recommendation

---

## RESEARCH MODES

Choose the mode that fits the request:

| Mode | When to use | Queries | Sources | Rounds | Output |
|------|--------------|---------|---------|--------|--------|
| `quick` | Fact check, version check, single question | 1 | 1-2 | 1 | 1 paragraph |
| `standard` | Feature research, technology evaluation | 3 | 3-4 | 1 | Full report |
| `deep` | Architecture decision, comparative analysis | 5+ | 5-7 | 1 | Full report + tradeoffs |
| `iterative_deep` | Complex topics, conflicting sources, strategic decisions | 5+ per round | 5-7 per round | 2-3 | Full report + gap analysis |

**Auto-escalation rules:**
- Default: `standard`
- Automatically drop to `quick` if the user asks a simple question
- Escalate to `deep` if the user requests it or the topic is complex with conflicting sources
- Escalate to `iterative_deep` if: (a) the user requests deep iterative research, (b) after Round 1 there are ≥3 gaps or ≥2 high-severity contested points, or (c) it's being called by the `multi-researcher-agent` agent

---

## PRE-FLIGHT CHECKLIST

Run before starting the search. Any item fails → fix it before continuing.

- [ ] **Scope narrow enough?** If the topic reads >2 ways → AskUserQuestion to narrow it. 1 research = 1 decision; split a topic that serves >1 decision.
- [ ] **Mode chosen correctly?** Recheck the auto-escalation rules — no deep mode for a simple fact check, no quick mode for comparative analysis.
- [ ] **Angles identified?** Pick ≥2 angles from the QUERY DESIGN table that fit the research goal.
- [ ] **Prior research exists?** Read it first and build on it — don't duplicate.

## WORKFLOW

### Scope Gate (before SEARCH_AND_TRIAGE)

**Do NOT write queries until the PRE-FLIGHT CHECKLIST passes** — scope narrow, mode correct, angles chosen. Never self-narrow without user approval; if ambiguous, AskUserQuestion instead of guessing.

### Standard / Deep Mode (single-pass)

```
DEFINE_QUERIES
  → Create queries from the topic + mode using QUERY DESIGN angles below
  → quick: 1 query, standard: 3 queries, deep: 5+ queries
        ↓
SEARCH_AND_TRIAGE
  → WebSearch each query
  → Read snippets, pick the highest-quality URLs to fetch
  → Prioritize: official docs > technical blogs > Stack Overflow > general articles
  → Exclude: marketing pages, duplicates, thin AI-generated content
        ↓
DEEP_READ
  → WebFetch the selected URLs
  → Page > 3000 words? Extract the relevant sections, don't read it all
  → Note source URL, tier, date if visible
  → [Error handling: see ERROR HANDLING below]
        ↓
CLAIM_EXTRACTION  ← [required for standard/deep/iterative_deep]
  → Extract explicit, falsifiable claims from each source:
    - Format: "{statement} — {source URL} — {evidence type}"
    - Evidence types: `data` (benchmark/experiment) > `anecdote` (case study) > `opinion` (expert view) > `assertion` (unsupported)
  → Tag each claim `falsifiable` (verifiable/refutable), `opinion` (not easily verifiable), or `fact` (uncontested, e.g. version/release date)
  → Synthesis priority: falsifiable claims > facts > opinions
  → Most important step against "shallow research" — a source you can't extract falsifiable claims from may be thin content
        ↓
SYNTHESIZE
  → Merge claims that say the same thing across sources
  → Distinguish consensus vs. contested points by claim overlap
  → Flag conflicts: claim A (source X) # claim B (source Y)
  → Same-domain URL dedup: cite 1, note "also: [url2]"
  → Remove duplicate claims and unsupported assertions with no evidence type
        ↓
ADVERSARIAL_VERIFICATION  ← [deep & iterative_deep modes only]
  → Per CRITICAL claim (directly affects the decision/recommendation):
    1. Ask: "If this claim is WRONG, what would the refuting evidence look like?"
    2. Find ≥1 source/perspective that could refute it
    3. No refutation found → claim gets stronger
    4. Refutation found → evaluate the counter-evidence's strength
  → Assign a confidence tier (✅/⚡/⚠/❌, see CONFIDENCE TIERS below)
  → Drop ❌ Refuted claims from Key Findings; flag Contested ones in Tradeoffs & Contested Points
  → (pattern borrowed from deep-research's 3-vote adversarial verification, adapted for single-agent use)
        ↓
CRITIQUE_LOOP  ← [required for standard/deep/iterative_deep]
  → 5 mandatory critique questions:
    1. "What haven't I researched?" — list explicit gaps
    2. "What assumption haven't I challenged?"
    3. "Which source needs further verification?"
    4. "Is there an angle I've missed? (security? cost? operational?)"
    5. "Are >50% of sources from the same domain/vendor?" → add a query for alternative perspectives
  → Critical gaps → 1-2 targeted queries before outputting; minor gaps → note in Gaps & Limitations
  → **[Deep mode] Incremental validation** — after each Key Findings category, ask "enough evidence?"; if not, run a targeted follow-up query before the next category (pattern borrowed from brainstorming: approve each section before continuing)
        ↓
OUTPUT
  → Choose the output format based on context (see OUTPUT FORMAT)
```

---

### Iterative Deep Mode (multi-round)

> **Full workflow:** Read `references/iterative-deep-workflow.md`
>
> Summary: 3 rounds. R1 maps landscape (5-7 queries, claim extraction, self-evaluate). R2 fills gaps found in R1 (3-5 targeted queries). R3 resolves remaining high-severity contested points (active refutation + adversarial verification). Each round's self-evaluation determines whether to continue or output.

---

## ERROR HANDLING

Handle failures instead of just flagging them:

| Failure type | Action |
|--------------|--------|
| WebSearch → 0 results | Retry with a broader query. If still 0 → note "limited public info on this topic" |
| WebFetch timeout / 5xx | Try another URL from the search results. Note "could not access [url]" |
| HTTP 403 / paywall | Look for: preprint (arXiv), cached version, author's personal page, HN/Reddit discussion |
| CAPTCHA / bot detect | Skip the URL, choose an alternative. Note in the Sources table |
| Content too long | Read the intro + summary/conclusion sections. Use WebSearch to find a substitute summary article |
| Rate limit (429) | Wait and retry once. If it still fails → skip, note in the report |

**Minimum viable research:** If after all fallbacks fewer than 2 sources are accessible → clearly tell the user the research may be incomplete.

---

## QUERY DESIGN

For each topic, choose angles that fit the mode and the research goal:

| Angle | Query pattern | Use when |
|-------|---------------|----------|
| **Overview** | `"<topic> explained"`, `"what is <topic>"` | Unfamiliar topic |
| **Technical depth** | `"<topic> implementation architecture"` | Need implementation details |
| **Tradeoffs** | `"<topic> vs <alternative> comparison"` | Decision making |
| **Problems** | `"<topic> issues limitations pitfalls"` | Risk assessment |
| **Best practices** | `"<topic> best practices production"` | Implementation guidance |
| **Community** | `"<topic> site:news.ycombinator.com OR site:reddit.com"` | Real-world sentiment |
| **Recent** | `"<topic> after:YYYY-MM-DD"` | Fast-moving technology |
| **Case studies** | `"<topic> case study post-mortem lessons learned"` | Resolve contested points (R3) |
| **Benchmarks** | `"<topic> benchmark performance comparison 2024"` | Resolve quantitative conflicts (R3) |

Use the actual date from `currentDate` instead of hardcoding a year.

---

## SOURCE QUALITY TIERS

**Tier 1 — High priority:**
- Official documentation (docs.*, *.readthedocs.io, official GitHub repos)
- Academic papers (arxiv.org, IEEE, ACM — check date)
- Engineering blogs from practitioners with clear backgrounds (Netflix, Google, Cloudflare tech blogs)

**Tier 2 — Selective:**
- Stack Overflow answers (score > 10, accepted answer preferred)
- GitHub Issues/Discussions with technical depth
- Well-attributed blog posts from known engineers

**Tier 3 — Verify before trusting:**
- Tutorial sites (accuracy varies)
- Vendor blogs (potential bias — check claims independently)
- Wikipedia (good for overview, verify claims with Tier 1 sources)

**Avoid:**
- AI-generated content (signals: no author, generic phrasing, no specific examples, published post-2023 on low-authority sites)
- Content > 2 years old for fast-moving tech (AI/ML libs, JS frameworks, cloud APIs)

**Freshness:** fast-moving libs (AI/ML, JS frameworks) → prioritize < 6 months old; fundamentals/algorithms → up to 5 years acceptable.

---

## CONFIDENCE TIERS

Each claim, after ADVERSARIAL_VERIFICATION, is assigned one of 5 levels (borrowed from the
`deep-research` skill's 3-vote adversarial verification, adapted for a single-agent context):

| Tier | Tag | Condition | Meaning for the decision |
|------|-----|-----------|---------------------|
| **Verified** | `✅` | ≥2 independent sources confirm + 0 refute after adversarial check | Can be used as a basis for the decision |
| **Likely** | `⚡` | ≥1 source confirms + 0 refute, but evidence isn't strong (opinion/anecdote) | Consider it, needs more validation |
| **Single-source** | `⚠` | Only 1 source, no further confirmation yet | Don't use for a critical decision — needs verification |
| **Contested** | `⚡` | Sources conflict, evidence on both sides | Needs a spike/experiment to resolve before deciding |
| **Refuted** | `❌` | Claim refuted by stronger evidence | Remove from Key Findings, note in Gaps |

**Rules:**
- Critical claims must reach ✅ Verified or ⚡ Likely — otherwise flag as a limitation
- ⚠ Single-source claims are allowed in the report but must be clearly flagged
- ❌ Refuted claims: remove from Key Findings, never used to make a recommendation
- The confidence tier must be noted in Key Findings (inline badge) and the Sources table

---

## AGENT INTERFACE

> **Full schema:** Read `references/agent-interface.md`
>
> When called by another agent: receives `topic`, `research_angle`, `depth`, `output_mode`. Returns structured JSON with `top_insights` (with confidence tier), `consensus_points`, `contested_points`, `refuted_claims`, `sources`.

---

## OUTPUT FORMAT

> **Full template:** Read `references/output-format.md`
>
> **Quick mode:** 1-2 paragraphs inline + `([Source](url))`.
> **Standard/Deep mode:** Structured report with Executive Summary → Claims Confidence Summary → Key Findings (with confidence badges) → Refuted Claims → Tradeoffs & Contested Points → Recommended Approach → Research Journey (iterative only) → Sources → Gaps & Limitations.

---

## PRE-OUTPUT CHECKLIST

Run before outputting the final report. All items must pass — if not, go back and fix them.

- [ ] **CLAIM_EXTRACTION run?** Every source's claims extracted and tagged with evidence type (data/anecdote/opinion/assertion).
- [ ] **ADVERSARIAL_VERIFICATION run?** Every CRITICAL claim tested for refutation, ≥1 counter-perspective sought for each.
- [ ] **Confidence tiers assigned?** Every critical claim has a badge (✅ ⚡ ⚠ ⚡ ❌) + evidence type; refuted claims removed.
- [ ] **CRITIQUE_LOOP run?** All 5 critique questions asked (gaps, assumptions, sources needing verification, missed angles, source diversity).
- [ ] **Critical claims have ≥2 sources?** Every important claim confirmed by ≥2 independent sources; single-source claims flagged `⚠`.
- [ ] **Conflicts flagged clearly?** Sources that disagree → `⚡ Contested` in the Tradeoffs & Contested Points table. Don't decide on the user's behalf.
- [ ] **Refuted claims recorded?** Listed in the Refuted Claims section so the research isn't repeated.
- [ ] **Sources table complete?** Each source has URL, Tier, Round, Claims extracted, What it covers — no placeholder or fabricated URLs.
- [ ] **Gaps recorded?** What wasn't covered is listed in Gaps & Limitations; <2 accessible sources → flag explicitly.
- [ ] **No copy-paste?** All content is extracted + paraphrased, never pasted verbatim from the source.

---

## CONSTRAINTS

- Read at least 3 sources (standard/deep) or 1 source (quick) before concluding
- Do not fabricate citations — note "could not access" if a fetch fails
- Do not copy-paste entire page content — extract and paraphrase
- When findings are contradictory: present both viewpoints with evidence
- Topic too broad → narrow the scope with AskUserQuestion before searching
- Iterative mode: max 5-7 URLs per round — depth over breadth, avoid running indefinitely
- Round 3 only triggers when ≥2 high-severity contested points exist — doesn't run by default
- Self-evaluating after each round is mandatory in iterative mode — don't skip it
</content>
