---
name: insights
description: >
  Use when analyzing past session transcripts in batch to build a knowledge base — extracting
  bug-fix, architecture-decision, performance-optimization, and best-practice insights from
  historical sessions across any stack: Python pipeline/script, Go+Fiber, Next.js+Prisma, Spring
  Boot, NestJS, FastAPI, or Rust for backend/full-stack features; Angular, React, Android, iOS,
  or Flutter for a frontend/mobile UI feature. Use for: "phân tích session", "xây dựng knowledge
  base", "trích xuất insight từ lịch sử", "tổng hợp bài học", "học từ session cũ", "đúc kết kinh
  nghiệm", "tổng kết best practices". Do NOT use for analyzing a single current session — this
  skill is for batch historical analysis across many sessions.
---

## OVERVIEW

Extract reusable long-term knowledge from Claude Code session transcripts (JSONL), for a project
built on any of this repo's supported stacks — Python pipeline/script, Go+Fiber, Next.js+Prisma,
Spring Boot, NestJS, FastAPI, Rust, Angular, React, Android, iOS, or Flutter. Focus on 4 insight
types: bug fixes, architecture decisions, performance optimizations, and best practices/lessons
learned. Merge similar findings, remove outdated info, save as cross-referenced memory files.

**Core rules:**
- Only save insights with clear root cause — symptom-only findings are not reusable
- Tag every insight with the stack it came from (see `references/taxonomy.md`) — a memory file
  useful for a NestJS backend is not automatically useful for a Flutter app, even if the surface
  symptom (e.g. "race condition") looks similar
- Consolidate similar patterns: target ≤30 memory files from 50 sessions
- Cross-reference related memories with `[[slug]]` links
- Mark outdated info as `status: superseded` — never delete memory files
- Don't reinvent what's already documented: check `review`'s (CODE mode) per-stack criteria and
  `implement`'s per-stack checklist (`references/*-checklist.md`) before writing a new insight —
  an insight only earns its place if it's something those didn't already cover

<HARD-GATE>
Do NOT save any memory file until:
1. `analyze_sessions.py` has run and produced a JSON output (dry-run first)
2. Findings verified — confidence ≥ 0.7 or manually validated by reading transcript excerpts
3. Consolidation complete — similar findings merged, duplicates removed, outdated detected
4. User has approved the proposed memory files via AskUserQuestion

Do NOT claim completion until:
5. All approved memory files written with correct frontmatter
6. MEMORY.md index updated to reflect new/changed files
7. Summary report exists at `docs/05-knowledge/session-insights-YYYY-MM-DD.md`
</HARD-GATE>

**Violating any gate = violating the spirit of the skill.** Common rationalizations:

| Rationalization | Reality |
|----------------|---------|
| "This finding is obvious, I'll save it directly" | Even obvious findings need classification and consolidation check. Skip the workflow → duplicate memory files. |
| "50 sessions is too many, I'll just scan 10" | Smaller sample misses systemic patterns. 50 sessions is the minimum for statistical significance. |
| "I'll skip the dry-run, the script always works" | Dry-run catches path/config issues in 5 seconds vs debugging a failed 50-session run. |
| "The confidence score is low but I'm sure it's correct" | Low-confidence = keyword heuristic couldn't validate. Read the transcript excerpt to confirm before saving. |
| "This pattern only appeared once but it's important" | Single occurrences are notes, not patterns. Save only if root cause + solution + prevention are clear. |
| "The stack tag doesn't matter, it's all the same fix" | A fix that's stack-specific (e.g. a Prisma migration quirk) is useless noise injected into an unrelated Flutter session. Tag accurately. |

**Red Flags — STOP and verify before proceeding:**

- Skipping the 5-session dry-run before the full 50-session analysis
- Creating >30 memory files from 50 sessions (insufficient consolidation)
- Saving a finding without a root cause (symptom-only)
- Overwriting an existing memory file without conflict resolution
- "The script output is fine, I don't need to read any transcripts"
- Memory files with empty or generic descriptions (unfindable by injection system)
- Tagging every finding with the same stack without checking which stack the session actually touched

---

## WORKFLOW

### Phase 1: COLLECT — Parse session transcripts

> **Full workflow:** Read `references/workflow-details.md`
>
> **Summary:** Run `analyze_sessions.py --num-sessions 5 --dry-run` first to verify. Then run with `--num-sessions 50`. Script auto-detects bug/perf sessions via keyword matching and the affected stack via manifest-file/import signals (same detection style `architecture`/`design` use), outputting structured JSON to `reports/session_analysis_<timestamp>.json`.
>
> **Critical:** Always dry-run first. Script path: `.claude/skills/insights/scripts/analyze_sessions.py`.

### Phase 2: EXTRACT — Validate and enrich

> **Full workflow:** Read `references/workflow-details.md`
>
> **Summary:** For findings with confidence < 0.7, read transcript excerpts to verify. Enrich with git context (commits near session date, file modification history). Validate symptom accuracy and root cause clarity.
>
> **Critical:** Low-confidence findings (< 0.4) must be manually verified or discarded.

### Phase 3: CLASSIFY — Tag each finding

> **Full taxonomy:** Read `references/taxonomy.md`
>
> **Summary:** Assign type (bug_fix/perf_optimization/best_practice/lesson_learned/arch_decision), stack (python-pipeline/go-fiber/nextjs-prisma/spring-boot/nestjs/fastapi/rust/angular/react/android/ios/flutter/shared-infra/database/other), a short free-form pattern slug, and severity (critical/major/minor). `arch_decision`, `best_practice`, and `lesson_learned` are rarely auto-detectable from keywords alone — classify these by reading the session, not by trusting the script's `type` field.

### Phase 4: CONSOLIDATE — Merge and deduplicate

> **Full rules:** Read `references/consolidation-rules.md`
>
> **Summary:** Group by (stack, pattern) → merge same root cause → detect outdated → remove duplicates → identify systemic issues (≥3 occurrences). Cross-check for cross-pattern links within the same stack.
>
> **Critical:** 1 finding = single file, 2 with same root cause = merge, ≥3 = systemic meta-insight.

### Phase 5: SAVE — Write memory files + update index

> **Full workflow:** Read `references/workflow-details.md` | **Memory format:** Read `references/memory-format.md`
>
> **Summary:** Write each insight as a memory file with YAML frontmatter (name, description, metadata), structured body (Problem → Root Cause → Solution → Prevention → Reusable Pattern → Related). Update MEMORY.md index. Generate summary report.

---

## TAXONOMY (compact)

| Field | Values |
|-------|--------|
| **Type** | `bug_fix` — code crash/wrong output | `perf_optimization` — speed/memory | `best_practice` — proven rule | `lesson_learned` — failure lesson | `arch_decision` — key architectural choice |
| **Stack** | `python-pipeline` \| `go-fiber` \| `nextjs-prisma` \| `spring-boot` \| `nestjs` \| `fastapi` \| `rust` \| `angular` \| `react` \| `android` \| `ios` \| `flutter` \| `shared-infra` \| `database` \| `other` |
| **Severity** | `critical` — crash, data loss/corruption | `major` — wrong results, silent failure | `minor` — code quality, warnings |

> **Full taxonomy** (stack detection signals, pattern examples per stack family, priority order): Read `references/taxonomy.md`
> **Where to find prior art before inventing a "known pattern"**: Read `references/known-patterns.md`

---

## FORBIDDEN

- ❌ Save insight without root cause — symptom-only findings have no reuse value
- ❌ Save trivia — typo fixes, format changes, simple variable renames
- ❌ Save sensitive info — API keys, credentials, internal URLs
- ❌ Overwrite existing memory without conflict resolution (AskUserQuestion)
- ❌ Delete memory files — mark `status: superseded` instead
- ❌ Create >30 memory files from 50 sessions — consolidate harder
- ❌ Skip confidence verification — findings < 0.5 must be manually verified
- ❌ Run script on all historical sessions at once — start with 50, scale up if needed
- ❌ Modify production code — this skill only reads transcripts and writes memory files
- ❌ Hardcode a fact about one project's stack into a memory file's `description` without the `stack` tag — future sessions on a different stack will match on keywords alone and get injected irrelevant context

---

## REFERENCE

| File | Content | Load when |
|------|---------|-----------|
| `references/workflow-details.md` | Phase 1-5 full steps: commands, JSON schema, checklists, git enrichment | Executing any phase |
| `references/taxonomy.md` | Full type/stack/pattern/severity tables + stack-detection signals + priority order | Phase 3 CLASSIFY |
| `references/consolidation-rules.md` | Merge rules, outdated detection, systemic issues, target metrics | Phase 4 CONSOLIDATE |
| `references/known-patterns.md` | Where to check for already-documented pitfalls before writing a new insight (`review`, `implement` checklists, existing memory) | Phase 1-2 to avoid duplicating known material |
| `references/memory-format.md` | Full claude-mem format spec: frontmatter, body, naming, cross-references | Phase 5 SAVE |
| `scripts/analyze_sessions.py` | Python script to parse JSONL transcripts → structured findings (stack + type + pattern) | Phase 1 COLLECT |
