# Output Format Templates

> Reference for `research` skill. Load when preparing final output.

## Quick mode (inline)

Answer directly in 1-2 paragraphs, cite the source briefly: `([Source](url))`.

## Standard / Deep mode (file or inline report)

```markdown
# Research: <Topic>

**Date:** YYYY-MM-DD
**Mode:** standard | deep | iterative_deep
**Rounds completed:** N
**Queries:** <list>
**Sources read:** N (Round 1: X | Round 2: Y | Round 3: Z)

---

## Executive Summary

> 3-5 sentences: key findings, consensus, biggest uncertainty.

---

## Claims Confidence Summary

> Overview of the confidence of the critical claims in this research.

| # | Claim | Confidence | Sources | Evidence type |
|---|-------|-----------|---------|---------------|
| 1 | <summarized claim> | ✅ Verified | 3 | data |
| 2 | <summarized claim> | ⚡ Likely | 1 | anecdote |
| 3 | <summarized claim> | ⚠ Single-source | 1 | opinion |

---

## Key Findings

### <Category 1>
<Content + inline confidence badge + citations like `✅ ([Source](url))` or `⚡ ([Source](url))`>

### <Category 2>
...

---

## Refuted Claims

> Claims that were refuted during adversarial verification.
> Recorded to avoid repeating research on the same wrong claim.

| Claim | Original source | Refuted by | Refuting evidence |
|-------|---------------|-------------|-----------------|
| ...   | ...           | ...         | ...             |

---

## Tradeoffs & Contested Points

| Aspect | View A | View B | Confidence | Source | Status |
|--------|--------|--------|------------|--------|--------|
| ...    | ...    | ...    | ⚡ Contested | ...    | Resolved R2 / Still contested |

---

## Recommended Approach

> Only write this if there's consensus. If contested → leave blank and explain in Contested Points.

1. **<Approach>**: <Reasoning, when to use it>

---

## Research Journey (iterative_deep mode only)

> Record the process: where gaps were found, which round filled them.

**Round 1 gaps identified:** <list>
**Round 2 filled:** <list>
**Round 3 resolved:** <list>
**Still unresolved:** <list>

---

## Sources

| URL | Tier | Round | What it covers |
|-----|------|-------|----------------|
| ... | 1    | 1     | ...            |

---

## Gaps & Limitations

> What this research hasn't covered, or needs further verification.
> If < 2 sources were accessed: flag explicitly.
```
