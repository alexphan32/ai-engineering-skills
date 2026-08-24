# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A library of Claude Code **Agent Skills** (`SKILL.md` files) — no application code, no build,
no package manager, no test runner. Each top-level directory under `skills/` is one
self-contained, project-agnostic skill: a `SKILL.md` (YAML frontmatter + Markdown workflow)
plus an optional `references/` folder of detail docs loaded on demand.

`skills/` is organized by **software engineering lifecycle phase**: `discovery`, `spec`,
`architecture`, `design`, `implement`, `test`, `review`, `operate` form the core chain (plus
`research` and `brainstorming` as cross-cutting phases — see `brainstorming/SKILL.md` for the
full lifecycle map, ceremony-tier triage, and routing table). Each top-level folder is itself one
skill (its own `SKILL.md` at its root) — no folder nests sub-skill folders; a skill that covers
several variants (e.g. `design`'s 12 stack modes, `review`'s CODE/SDS modes) handles that as
internal mode-detection within its own `SKILL.md`, the same way regardless of how many modes it
has.

Skills here are meant to be deployed into a consuming project (typically copied/symlinked to
that project's `.claude/skills/`) and invoked from there — this repo is the source of truth,
not the runtime location. There is nothing to install, lint, or test at the repo level; "testing"
a change means walking the skill's own workflow against a real task, or using
`skill-creator:skill-creator`'s eval tooling.

If a skill under `skills/` is ever written for one specific external target rather than staying
stack-agnostic, keep it out of `skills/` (e.g. under a separate `examples/` directory) rather than
mixing project-hardcoded facts into the generic lifecycle skills — none exists in this repo today.

## The generic SDLC lifecycle

```
discovery → spec → design → implement → test → review → operate
                              (review auto-detects CODE | SDS mode; defers to architecture-UPGRADE
                               for whole-system/topology requests naming no single file or SDS)
architecture and research are cross-cutting — callable from any phase, not steps in the chain
```

- `discovery` — fast, bounded context-gathering pass on an unfamiliar codebase/request before
  routing to any other skill. Not a deliverable-producing skill; it exists to avoid specifying,
  designing, or coding against wrong assumptions about what already exists.
- `spec` — writes an SRS (Software Requirements Specification). Auto-detects **MODE A**
  (Python data-pipeline or script/automation module, from the target project's own CLAUDE.md) vs
  **MODE B** (any backend, frontend, or mobile feature — business requirements are the same shape
  regardless of which of `design`'s 12 stack modes eventually implements it).
- `architecture` — three modes: **EXPLORE** generates/refreshes exhaustive architecture
  documentation for any codebase; **SELECT** chooses an architecture (deployment topology —
  monolith/modular monolith/microservices; domain modeling — plain CRUD/DDD; communication style
  — sync/event-driven) for a new system or component, including stack-specific structure for
  Angular, React, Android, iOS, Flutter, Rust, and FastAPI; **UPGRADE** re-evaluates an existing
  architecture's fit and plans an incremental migration. Not tied to any one target project.
  Callable ad hoc from any phase, most often from `discovery` (EXPLORE) or `design` (SELECT, when
  the Scale Tier/topology isn't decided yet).
- `design` — writes an SDS (Software Design Specification) from an SRS. Auto-detects the stack from
  the target project's manifest files (`go.mod`, `package.json`, `pom.xml`, `Cargo.toml`,
  `pyproject.toml`, `pubspec.yaml`, `angular.json`, `*.xcodeproj`, etc.), not from what the user
  says. 12 modes in two families: **REST/full-stack API** — **A** (Python pipeline/script) /
  **B** (Go+Fiber) / **C** (Next.js+Prisma) / **D** (Spring Boot) / **E** (NestJS) / **F** (FastAPI)
  / **G** (Rust) — and **Client UI** — **H** (Angular) / **I** (React SPA) / **J** (Android) /
  **K** (iOS) / **L** (Flutter). The REST family shares an inside-out discipline (domain model →
  data access → service logic → transport layer); the Client UI family shares its own inside-out
  discipline adapted to a client app (API/data layer → state management → screen/component
  composition → navigation) instead of a server's request/response cycle. The `architecture`
  skill's SELECT-mode reference docs (`backend-script-patterns.md`, `frontend-patterns.md`,
  `mobile-patterns.md`) are the stack-truth source for each mode's folder layout and idioms —
  `design` turns an SRS into a design that lands correctly inside that layout, not a second place
  that redecides it.
- `implement` — turns an SDS/plan into tested code. Stack-agnostic across all 12 `design` stacks;
  reads the target project's own CLAUDE.md for where constants/tests/tooling live, plus a
  per-stack checklist reference (`references/*-checklist.md` — Spring Boot, NestJS, Next.js+Prisma,
  FastAPI, Rust, Angular, React, Android, iOS, Flutter) for that stack's specific traps. Its own
  TEST step covers the inline unit RED→GREEN loop per function. Scoped to one task at a time; for
  a plan with several independent tasks it defers orchestration (dispatch, task review, fix loop)
  to Superpowers' `subagent-driven-development` or `executing-plans` skills rather than absorbing
  that loop itself.
- `test` — dedicated test strategy/authoring skill for coverage beyond that inline loop:
  integration, contract, e2e, performance, and concurrency/failure tests, plus coverage-gap
  audits after review flags weak tests.
- `review` — auto-detects what's being reviewed and runs the matching mode in place: **CODE**
  (11 criteria — covers all 12 `design` stacks: Python/FastAPI, Go/Fiber, Next.js/TypeScript,
  Spring Boot, NestJS, Rust, Angular, React, Android/Kotlin, iOS/Swift, Flutter/Dart) or **SDS**
  (12 criteria). For a whole module/system's architecture or topology rather than one file or
  SDS, it defers instead to `architecture`'s UPGRADE mode, which stays a separate top-level skill.
  For a frontend/mobile file, CODE mode's Distributed & Async Correctness / Data Integrity /
  Operations Readiness criteria are usually N/A (stated explicitly, not skipped) since a client
  app rarely owns a queue, a database, or a deployed service process.
- `operate` — deployment strategy, observability, reliability, incident response, and disaster
  recovery for code that has passed `review` and is running (or about to run) in production.

`spec`, `design`, and `implement` are chained by a shared **Implementation Readiness gate**
(`READY` / `PARTIALLY_READY` / `BLOCKED`) that each skill writes into its own output document
and the next skill in the chain must check before proceeding — `design` must stop if `spec`'s
gate is `BLOCKED`, `implement` must stop (or scope down) if `design`'s gate isn't clear. See
`brainstorming/SKILL.md` for the full gate contract and the lifecycle routing table. When editing
any skill in this chain, preserve that gate contract; breaking it breaks the handoff between
skills that don't otherwise share state.

Two more skills sit outside the linear chain entirely, callable from any phase:

- `research` — general web research workflow (multi-source, not codebase-bound) — technology
  evaluation, fact-checking, comparing libraries/frameworks.
- `brainstorming` — the dispatcher: classifies a request into one of three ceremony tiers (Spike /
  Bounded / Architectural) and routes it to the skill(s) that apply, for an ambiguous or
  multi-phase request; also the canonical place the lifecycle map and gate contract are documented
  (this CLAUDE.md section is the human-facing summary of the same contract). Named after — but
  scoped much narrower than — superpowers' `brainstorming`: it classifies and routes, it doesn't
  explore ideas or add its own approval gate.

## SKILL.md conventions

- **Frontmatter**: `name` and `description` are required. `description` is what the model
  matches against to decide whether to auto-invoke the skill — write it as a list of concrete
  trigger phrases/situations (including Vietnamese phrasing where the target users use it), not
  a one-line summary. Add `disable-model-invocation: true` when a skill should only run via an
  explicit slash command (none in `skills/` currently sets this).
- **references/**: put detail the main workflow doesn't need on every invocation (checklists,
  per-mode templates, output-format specs) into `references/*.md` and link to it with a "when
  to load" note in a table, rather than inlining it into `SKILL.md`. Keeps the main file the
  thing that's read every time; references are loaded on demand.
- **Reference paths**: most skills link references relatively (`references/foo.md`, resolved
  from the skill's own directory). `design/SKILL.md`'s "Reference Templates" table instead
  spells out the full deployed path (`.claude/skills/design/references/foo.md`) because it's
  cross-referenced by `implement/SKILL.md` from a different skill directory. Match whichever
  convention the surrounding table already uses when adding a new row.
- **Labeling discipline** (`spec`, `design`, and their reviewers): every non-trivial statement
  in a produced document is tagged — `[REQUIRED]`/`[CONFIRMED]`/`[ASSUMPTION]`/`[OPEN QUESTION]`/
  `[DECISION]` in SRS/SDS content — so a document is never ambiguous about what's solid vs. a
  guess. Don't add prose to these skills that would produce an untagged claim.
- Every `skills/<name>/CLAUDE.md` you may see (e.g. under `spec/`, `design/`, `implement/`,
  `review/`) is an auto-generated `claude-mem` context stub (session activity log), not authored
  documentation — don't treat it as a spec for the skill.
