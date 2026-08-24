# Known Patterns — Check Before You Invent One

> Loaded during Phase 1-2, before writing up a new finding. This skill covers many stacks and
> has no business hardcoding a fixed list of "known bugs" for all of them — that list would
> either be too shallow to be useful or would go stale the moment a stack's ecosystem moves on.
> Instead, check these sources of prior art first; only write a new insight for what they don't
> already cover.

---

## 1. This repo's own per-stack references (check first)

These are actively maintained and far more detailed than anything this skill could duplicate:

| Source | Covers |
|--------|--------|
| `review`'s (CODE mode) per-stack criteria | 11 review criteria across all 12 `design` stacks — correctness, security, performance, distributed/async correctness, data integrity, operations readiness, etc. |
| `implement`'s `references/*-checklist.md` | Per-stack implementation traps (Spring Boot, NestJS, Next.js+Prisma, FastAPI, Rust, Angular, React, Android, iOS, Flutter) |
| `architecture`'s SELECT-mode references (`backend-script-patterns.md`, `frontend-patterns.md`, `mobile-patterns.md`) | Per-stack idioms and folder-layout conventions |

If a finding just restates something already written there, don't save it as a new memory file —
note in the summary report that the session confirmed an existing documented pitfall instead.

## 2. Existing memory (`MEMORY.md` in the current project's memory directory)

Before writing a new insight, search `MEMORY.md` for the same `stack` + a similar `pattern` slug
(see `references/taxonomy.md`). If a matching entry exists:
- Same root cause → this is a recurrence, bump its `sessions` count instead of creating a new file (see `references/consolidation-rules.md`)
- Different root cause, same symptom → cross-reference with `[[slug]]`, keep as a separate file

## 3. What's actually worth writing up

A new memory file earns its place when it's specific to *this* project's code, config, or
history in a way the sources above can't capture — e.g. "this repo's auth middleware silently
swallows a specific header casing" or "this service's Prisma client must be instantiated once at
module scope, not per-request, because of connection-pool exhaustion under our load profile."
Generic language/framework advice belongs in the sources above, not in a session-derived memory
file.
