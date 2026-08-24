# 5-Phase Workflow — Detailed Steps

> Loaded when executing any phase. SKILL.md has workflow summaries — this file has the full commands, checklists, and output formats.

---

## Phase 1: COLLECT — Parse session transcripts

**Run script (test first, then full):**
```bash
# Dry-run: 5 sessions to verify script works
python .claude/skills/insights/scripts/analyze_sessions.py --num-sessions 5 --dry-run

# Full run: 50 sessions
python .claude/skills/insights/scripts/analyze_sessions.py --num-sessions 50
```

**Script output:** `reports/session_analysis_<timestamp>.json`

**Script output schema:**
```json
{
  "analysis_metadata": {
    "analyzed_at": "2026-06-06T12:00:00",
    "num_sessions_scanned": 50,
    "num_sessions_with_findings": 35,
    "date_range": {"earliest": "2026-05-01", "latest": "2026-06-06"},
    "type_breakdown": {"bug_fix": 15, "perf_optimization": 10, ...},
    "stack_breakdown": {"nestjs": 12, "react": 8, ...},
    "pattern_breakdown": {"race-condition": 5, ...},
    "confidence_distribution": {"high (>0.7)": 20, "medium (0.4-0.7)": 10, "low (0.3-0.4)": 5}
  },
  "findings": [
    {
      "session_id": "uuid-here",
      "timestamp": "2026-06-05T10:30:00",
      "type": "bug_fix",
      "subtype": "race-condition",
      "stack": "nestjs",
      "summary": "User prompt about a request handler crashing intermittently...",
      "symptoms": ["UnhandledPromiseRejection in orders.service.ts:88"],
      "files_modified": ["src/orders/orders.service.ts"],
      "file_references": ["src/orders/orders.service.ts", "..."],
      "solution_hints": ["Modified: src/orders/orders.service.ts"],
      "confidence": 0.9
    }
  ]
}
```

**Auto-detection logic (script):**
- **Bug fixing**: keywords (fix, bug, error, crash, exception, traceback/stack trace, plus common language-specific error names) + tool patterns (Edit/Write after error)
- **Performance**: keywords (slow, optimize, perf, bottleneck, memory, timeout, OOM)
- **Stack**: manifest-file and import signals per `references/taxonomy.md` (same idea as `architecture`/`design`'s stack auto-detection) — not keyword scoring, since a stack is either present in the files touched or it isn't
- `arch_decision`, `best_practice`, and `lesson_learned` are not auto-scored by the script — the script only distinguishes `bug_fix` / `perf_optimization` / `general`; assign the other three types during Phase 3 by reading the session

---

## Phase 2: EXTRACT — Validate and enrich findings

**Locate latest output:**
```bash
python -c "import glob,json; f=sorted(glob.glob('reports/session_analysis_*.json'))[-1]; d=json.load(open(f,'r',encoding='utf-8')); print(f'Found {len(d[\"findings\"])} findings in {f}')"
```

**Verification checklist per finding:**
- [ ] Symptom description accurate (read transcript excerpt if confidence < 0.7)
- [ ] Root cause identified (not just symptom)
- [ ] Solution verified (commit exists, files changed match)
- [ ] Stack correctly identified (check `references/known-patterns.md` for prior art on this stack before writing a new insight)

**Git enrichment:**
```bash
# Find commits near the session date (ISO format, ±3 days)
git log --after="<session_date_YYYY-MM-DD>" --before="<session_date+3d>" --oneline --all

# Check if fix is still valid (file changed after session?)
git log --oneline -- <file_path>
```

---

## Phase 3: CLASSIFY — Tag each finding

Apply taxonomy from `references/taxonomy.md`:
- **Type**: `bug_fix`, `perf_optimization`, `best_practice`, `lesson_learned`, `arch_decision`
- **Stack**: `python-pipeline`, `go-fiber`, `nextjs-prisma`, `spring-boot`, `nestjs`, `fastapi`, `rust`, `angular`, `react`, `android`, `ios`, `flutter`, `shared-infra`, `database`, `other`
- **Pattern**: short free-form kebab-case slug naming the mechanism (e.g. `race-condition`, `n-plus-one-query`, `null-reference`, `stale-cache`, `unbounded-rerender`, `auth-bypass`, `config-drift`, `memory-leak`) — reuse an existing slug from `MEMORY.md` whenever the mechanism matches, even across stacks
- **Severity**: `critical` (crash, data loss/corruption), `major` (wrong results, silent failure), `minor` (code quality, warnings)

---

## Phase 4: CONSOLIDATE — Merge and deduplicate

Full rules in `references/consolidation-rules.md`.

**Quick reference:**
1. Group by (`stack`, `subtype`/pattern) fields
2. 1 finding per group → single memory file
3. 2 findings, same root cause → merge into 1 file with `sessions: 2`
4. ≥3 findings → systemic issue — create meta-insight + link individual files
5. Cross-check for cross-pattern links within the same stack

**Outdated detection:**
```bash
git log --oneline --after="<finding_date>" -- <file_path>
# If later commits modify the same file with related message → potentially outdated
```

---

## Phase 5: SAVE — Write memory files + update index

**Memory directory:** the *current project's* memory directory — `C:\Users\<user>\.claude\projects\<project-slug>\memory\`, the same one `analyze_sessions.py` resolves its transcript dir against (`CLAUDE_CONFIG_DIR` + cwd's project slug). Never hardcode another project's path here.

**File naming:** `<type-prefix>-<stack>-<short-slug>.md`
- Type prefixes: `bug-`, `perf-`, `best-`, `lesson-`, `arch-`
- Examples: `bug-nestjs-unhandled-promise-rejection.md`, `best-nextjs-prisma-connection-pooling.md`

**Memory file template:**
```markdown
---
name: <kebab-case-slug>
description: <one-line — used for relevance matching during memory injection>
metadata:
  type: reference
  pattern: <bug_fix | perf_optimization | best_practice | lesson_learned | arch_decision>
  stack: <python-pipeline | go-fiber | nextjs-prisma | spring-boot | nestjs | fastapi | rust | angular | react | android | ios | flutter | shared-infra | database | other>
  severity: <critical | major | minor>
  sessions: <count>
  last_seen: <ISO date>
  status: <active | superseded>
---

# <Title>

## Problem
<Symptoms — error messages, unexpected behavior, metric regression>

## Root Cause
<Why it happened — the mechanism, not just "X was wrong">

## Solution
<Specific fix — code changes, config changes, commands>

## Prevention
<How to prevent recurrence — tests, checks, conventions>

## Reusable Pattern
<Checklist, code snippet, or diagnostic procedure for future use>

## Related
[[other-slug-1]] [[other-slug-2]]
```

**Update MEMORY.md index after writing:**
```markdown
- [<Category>: <Short Title>](<filename>.md) — <One-line reason this is relevant>
```

**Generate summary report:**
```bash
mkdir -p docs/05-knowledge
# Write report to docs/05-knowledge/session-insights-YYYY-MM-DD.md:
# - Executive summary (N findings → M insights)
# - Breakdown by type/module/severity
# - Top systemic issues
# - List of memory files created
```

Full memory format reference → `references/memory-format.md`.
