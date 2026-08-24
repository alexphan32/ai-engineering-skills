# Consolidation Rules — Merge, Deduplicate, Detect Outdated

> Loaded during Phase 4 CONSOLIDATE.

---

## Merge Rules

**When to merge findings:**
- Same `pattern` tag AND same `root_cause` → merge into 1 insight
- Same `stack` AND same `symptom` → merge (likely recurrence)
- Same `files_modified` AND similar fix content → merge

**When NOT to merge:**
- Different root causes with similar symptoms → separate insights with cross-references
- Same pattern but different stacks → separate, add cross-stack note (the mechanism may be the same, e.g. `race-condition`, but the fix rarely transfers verbatim between a Go service and a React component)

---

## Grouping by Count

| Findings per group | Action |
|--------------------|--------|
| **1 finding** | Create single memory file from that finding |
| **2 findings** | If same root cause → merge into 1 file with `sessions: 2`. Otherwise → 2 separate files |
| **≥ 3 findings** | Systemic issue — create 1 meta-insight listing all occurrences + link individual files if any are critical enough to stand alone |

**After grouping:** Cross-check all merged groups for cross-pattern links within the same stack. Example: an `n-plus-one-query` finding often co-occurs with a `stale-cache` finding in the same service.

---

## Outdated Detection

**Mark as `status: superseded` when:**
- File was modified by a later commit with message containing "fix", "revert", "refactor"
- Constants have changed (check current value in source code vs value in finding)
- Bug was fixed and tests pass in subsequent runs

**Detection command:**
```bash
git log --oneline --after="<finding_date>" -- <file_path>
# If later commits modify the same file with related message → potentially outdated
```

**Rule:** Never delete a memory file. Mark `status: superseded` and keep in MEMORY.md with a note.

---

## Systemic Issue Criteria

Create a systemic issue meta-insight when:
- Pattern appears ≥ 3 times across different sessions
- Pattern appears ≥ 2 times AND caused ≥ 1 critical bug
- Same root cause but different symptoms → systemic

---

## Duplicate Removal

Priority order when duplicates found (same session + same file + same error):
1. Keep the finding with highest confidence score
2. If equal confidence → keep the more recent one

---

## Target Metrics

- **≤ 30 memory files** from 50 sessions (consolidate harder if exceeding)
- Each memory file must be independently useful
- Each must be findable by its `description` field alone
- No two memory files should describe the same pattern
