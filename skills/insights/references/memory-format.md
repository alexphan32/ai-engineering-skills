# Memory File Format Reference

This reference documents the claude-mem format used by the `insights` skill. Memory files live
in the *current project's own* memory directory — `C:\Users\<user>\.claude\projects\<project-slug>\memory\`
(the same auto-memory system every Claude Code session uses) — and are indexed in that
directory's `MEMORY.md`. Don't hardcode a path to a different project's memory directory; resolve
it the same way `analyze_sessions.py` resolves its transcript directory (from `CLAUDE_CONFIG_DIR`
+ the current working directory's project slug).

---

## Directory Structure

```
memory/
├── MEMORY.md                          # Index file — one line per memory entry
├── bug-nestjs-unhandled-promise-rejection.md
├── perf-react-unbounded-rerender.md
├── best-nextjs-prisma-connection-pooling.md
└── ...
```

---

## File Format

Each memory file is a Markdown file with YAML frontmatter.

### Frontmatter Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | ✅ | string (kebab-case) | Unique identifier slug. Used for cross-referencing with `[[name]]` links. Must match filename (without `.md`). |
| `description` | ✅ | string | One-line summary. Used by the memory injection system to decide relevance when loading context. Keep under 150 chars. |
| `metadata.type` | ✅ | enum | `user`, `feedback`, `project`, or `reference`. Insights use `reference`. |
| `metadata.pattern` | Recommended | enum | `bug_fix`, `perf_optimization`, `best_practice`, `lesson_learned`, `arch_decision` |
| `metadata.stack` | Recommended | string | `python-pipeline` \| `go-fiber` \| `nextjs-prisma` \| `spring-boot` \| `nestjs` \| `fastapi` \| `rust` \| `angular` \| `react` \| `android` \| `ios` \| `flutter` \| `shared-infra` \| `database` \| `other` — see `references/taxonomy.md` |
| `metadata.severity` | Recommended | enum | `critical`, `major`, `minor` |
| `metadata.sessions` | Optional | integer | Number of sessions where this pattern was observed |
| `metadata.last_seen` | Optional | ISO date | Date of most recent occurrence |
| `metadata.status` | Optional | enum | `active` (still relevant), `superseded` (replaced by newer insight) |

### Frontmatter Example

```yaml
---
name: bug-nestjs-unhandled-promise-rejection
description: NestJS request handler swallows a rejected promise from an un-awaited service call — crashes the process on the next unrelated request
metadata:
  type: reference
  pattern: bug_fix
  stack: nestjs
  severity: critical
  sessions: 3
  last_seen: 2026-06-05
  status: active
---
```

---

## Body Structure

The body should follow a consistent template for reusability:

```markdown
# <Descriptive title — imperative, actionable>

## Problem
<Symptom — error message, unexpected behavior, metric regression>
<Include exact error messages in code blocks where possible>

## Root Cause
<Why it happened — the underlying issue, not the symptom>
<Explain the mechanism, not just "X was wrong">

## Solution
<How to fix it — specific code changes, config changes, commands to run>
<Use code blocks for exact changes>

## Prevention
<How to prevent recurrence — tests, checks, conventions, lint rules>
<Actionable checklist format preferred>

## Reusable Pattern
<If reusable: verification procedure, checklist, code snippet>
<This is the most valuable section for knowledge reuse>

## Related
[[other-memory-slug-1]]
[[other-memory-slug-2]]
```

---

## Naming Conventions

### File naming
```
<type-prefix>-<stack>-<short-slug>.md

Type prefixes:
  bug-     Bug fix insights
  perf-    Performance optimization insights
  best-    Best practice insights
  lesson-  Lesson learned insights
  arch-    Architecture decision insights

Examples:
  bug-nestjs-unhandled-promise-rejection.md
  perf-react-unbounded-rerender.md
  best-nextjs-prisma-connection-pooling.md
  lesson-flutter-provider-rebuild-storm.md
  arch-go-fiber-middleware-order.md
```

### Slug rules
- Lowercase kebab-case
- Max 5 words
- Descriptive enough to understand without opening the file
- No special characters except hyphens
- English preferred (for consistency with cross-references)

### `name` field vs filename
The `name` frontmatter field should match the filename (without `.md`). This is what `[[name]]` cross-references use.

---

## Cross-Referencing

Use `[[name]]` syntax in the body to link related memories:

```markdown
## Related
[[bug-nextjs-prisma-double-connection]]
[[best-nextjs-prisma-connection-pooling]]
```

The `name` doesn't need to exist yet — linking to a non-existent name creates a "wanted" reference that can be filled later.

---

## MEMORY.md Index Format

`MEMORY.md` is a flat index with one line per memory entry:

```markdown
# Memory Index

- [Bug: NestJS swallows a rejected promise](bug-nestjs-unhandled-promise-rejection.md) — crashes the process on the next unrelated request
- [Perf: React unbounded re-render loop](perf-react-unbounded-rerender.md) — missing dependency array caused a state update on every render
- [Best Practice: Prisma client as a module-scope singleton](best-nextjs-prisma-connection-pooling.md) — per-request instantiation exhausted the connection pool under load
```

Format per line:
```
- [<Category>: <Short Title>](<filename>.md) — <One-line reason this is relevant>
```

---

## Quality Guidelines

### What to save
- Issues with clear root cause AND reproducible solution
- Patterns that recurred across multiple sessions
- Critical or major severity issues
- Counter-intuitive behaviors (e.g., "the retry wrapper masked the real timeout")
- Hard-won configuration knowledge specific to this project (e.g., "this service's connection pool must stay under 10 or the DB's max_connections is exceeded under our load profile")

### What NOT to save
- Trivia: typo fixes, variable renames, formatting changes
- One-off environment issues (path wrong on specific machine)
- Session-specific context (user said X, then Y)
- Information already documented in CLAUDE.md, skill files, or `review`/`implement`'s per-stack references (see `references/known-patterns.md`)
- API keys, credentials, or sensitive URLs

### Target metrics
- Aim for ≤ 30 memory files from 50 sessions
- Each memory file should be independently useful
- Each memory file should be findable by its `description` field alone
- No two memory files should describe the same pattern for the same stack

---

## Memory Injection Behavior

claude-mem injects relevant memories into future sessions based on:
1. **The `description` field** — used for semantic relevance matching
2. **Cross-references** — `[[linked-memory]]` may cause linked memories to also be injected
3. **Recency** — more recent memories are weighted higher

Write descriptions that contain enough keywords for the injection system to match them against
future queries — and name the stack, since a description with no stack signal can get injected
into an unrelated session just because a generic word (e.g. "race condition") matches. For example:
- Good: "NestJS request handler swallows a rejected promise from an un-awaited service call — crashes the process on the next unrelated request"
- Bad: "backend bug"
