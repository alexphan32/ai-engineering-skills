# AI Engineering Skills

A library of [Claude Code Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) covering the full software engineering lifecycle — from discovery through spec, design, implementation, testing, review, and operations. Stack-agnostic: each skill auto-detects the target project's language and framework instead of assuming one.

## Table of Contents

- [How it works](#how-it-works)
- [Installation](#installation)
- [The Lifecycle](#the-lifecycle)
- [What's Inside](#whats-inside)
- [Agents](#agents)
- [Design Conventions](#design-conventions)
- [Contributing](#contributing)
- [License](#license)

## How it works

Most "vibe coding" failures come from an agent jumping straight to code before anyone has agreed on the requirements, the design, or even what "done" looks like. This library breaks that into discrete, auto-triggering skills that mirror how a disciplined engineering team actually moves work forward:

- **discovery** grounds the agent in what already exists before it assumes anything.
- **spec** turns a request into a labeled Software Requirements Specification, tagging every line as required, confirmed, assumed, or an open question — so nothing solid gets confused with a guess. Business requirements are stack-agnostic, so this step doesn't need to know yet whether the feature ends up backend, frontend, or mobile.
- **architecture** decides (or documents) how the system is put together: monolith vs. microservices, DDD vs. plain CRUD, sync vs. event-driven.
- **design** turns the SRS into a Software Design Specification, auto-detecting the stack from the target project's own manifest files — 12 modes across a **REST/full-stack API** family (Python pipeline/script, Go+Fiber, Next.js+Prisma, Spring Boot, NestJS, FastAPI, Rust) and a **Client UI** family (Angular, React, Android, iOS, Flutter).
- **implement** turns the SDS into tested code, one task at a time, with an inline red/green loop per function, using per-stack checklists for each of those 12 stacks' actual traps.
- **test** covers everything beyond that inline loop — integration, contract, e2e, performance, and failure testing.
- **review** routes to the right specialized reviewer — code (11 criteria, across all 12 `design` stacks) or design docs (12 criteria) — instead of reviewing everything the same way.
- **operate** picks up once code has passed review: deployment strategy, observability, reliability, incident response, disaster recovery.

`spec`, `design`, and `implement` are chained by a shared **Implementation Readiness gate** (`READY` / `PARTIALLY_READY` / `BLOCKED`). Each skill writes that verdict into its own output document, and the next skill in the chain has to check it before proceeding — so a blocked spec can't silently become a design, and an unclear design can't silently become code.

`research` and `brainstorming` sit outside that linear chain and are callable from any phase — `research` for web-sourced fact-finding, `brainstorming` as the dispatcher that sizes a request into a ceremony tier (Spike / Bounded / Architectural) and routes it to whichever skill(s) apply.

Because each skill's frontmatter `description` is written as a list of concrete trigger phrases — including Vietnamese phrasing alongside English — skills fire automatically when your request matches, without needing to remember exact names or slash commands.

## Installation

There's no plugin marketplace or package manager here — a skill is just a `SKILL.md` file (plus an optional `references/` folder), and Claude Code discovers skills by directory. Deploy what you need into the target project's `.claude/skills/`.

**Whole library:**

```bash
git clone https://github.com/<your-username>/ai-engineering-skills.git
cp -r ai-engineering-skills/skills/* /path/to/your-project/.claude/skills/
```

**Single skill:**

```bash
cp -r ai-engineering-skills/skills/spec /path/to/your-project/.claude/skills/spec
```

**Keep it in sync with a symlink** instead of a one-time copy:

```bash
ln -s /path/to/ai-engineering-skills/skills /path/to/your-project/.claude/skills
```

Once a skill is in place, it triggers on its own — ask for what you want ("viết SRS cho module X", "review this SDS", "chuẩn bị rollback plan") and the matching skill loads. Nothing to configure per-project beyond having the files present.

## The Lifecycle

```
discovery → spec → design → implement → test → review → operate
                              (review auto-detects CODE | SDS mode; defers to architecture-UPGRADE
                               for whole-system/topology requests naming no single file or SDS)

architecture and research are cross-cutting — callable from any phase
brainstorming is the dispatcher — routes ambiguous or multi-phase requests to the skill(s) above
```

## What's Inside

**Core chain**
- **discovery** — fast, bounded context-gathering pass on an unfamiliar codebase or request, before routing to any other skill.
- **spec** — writes a Software Requirements Specification. Auto-detects a Python data-pipeline/script module vs. any backend, frontend, or mobile feature from the target project.
- **design** — writes a Software Design Specification from an SRS. Auto-detects the stack from the project's own manifest files — Python pipeline/script, Go+Fiber, Next.js+Prisma, Spring Boot, NestJS, FastAPI, or Rust for backend/full-stack features; Angular, React, Android, iOS, or Flutter for a frontend/mobile UI feature.
- **implement** — turns an SDS or plan into tested code, one task at a time, with an inline TDD loop per function and a per-stack checklist for each of those 12 stacks.
- **test** — integration, contract, e2e, performance, and concurrency/failure test strategy and authoring, plus coverage-gap audits.
- **review** — auto-detects what's being reviewed and runs the matching mode in place.
  - **CODE mode** — 11-criteria code review (algorithm, bugs, performance, security, maintainability, documentation, testing, compliance, distributed/async correctness, data integrity, operations readiness) across all 12 `design` stacks: Python/FastAPI, Go/Fiber, Next.js/TypeScript, Spring Boot, NestJS, Rust, Angular, React, Android/Kotlin, iOS/Swift, and Flutter/Dart. For a frontend/mobile file, the distributed/data-integrity/ops-readiness criteria are usually N/A, stated explicitly rather than skipped.
  - **SDS mode** — 12-criteria design-doc review (completeness, clarity, consistency, feasibility, testability, interface, traceability, security & data protection, performance design, distributed/async design, data integrity, operations readiness).
- **operate** — deployment strategy, observability, reliability, incident response, and disaster recovery for code already in (or headed to) production.

**Cross-cutting**
- **architecture** — three modes: **EXPLORE** (generate/refresh architecture docs for any codebase), **SELECT** (choose deployment topology, domain modeling, and communication style for a new system or component, with stack-specific structure for Angular, React, Android, iOS, Flutter, Rust, and FastAPI), **UPGRADE** (re-evaluate an existing architecture and plan an incremental migration).
- **research** — multi-source web research for technology evaluation, fact-checking, and comparing libraries or frameworks.
- **brainstorming** — classifies an ambiguous or multi-phase request into a ceremony tier and routes it to the right skill(s); also documents the lifecycle map and the Implementation Readiness gate contract shared by `spec`/`design`/`implement`.

## Agents

`agents/` holds one Claude Code subagent per top-level skill in `skills/` — `discovery-agent`,
`spec-agent`, `design-agent`, `implement-agent`, `test-agent`, `review-agent`, `operate-agent`,
`architecture-agent`, `research-agent`, `brainstorming-agent`, `insights-agent`. Each agent is an
**executor** for its skill: the `SKILL.md` owns the workflow (steps, templates, checklists), the
agent adds what the skill deliberately doesn't own — tool scope (which tools it's allowed to call)
and approval gates (when to stop and ask instead of guessing). `review-agent` and
`brainstorming-agent` are **routers** instead — they detect and delegate rather than doing the
work themselves, the same way their skills do.

Deploy agents the same way as skills — copy or symlink `agents/*.md` into the target project's own
agent directory. See `agents/CLAUDE.md` for the full SKILL-vs-AGENT responsibility split and the
agent inventory table.

## Design Conventions

- **Labeling discipline** — every non-trivial statement in an SRS or SDS is tagged `[REQUIRED]`, `[CONFIRMED]`, `[ASSUMPTION]`, `[OPEN QUESTION]`, or `[DECISION]`, so a document is never ambiguous about what's solid versus a guess.
- **Stack-agnostic by default** — skills detect the target project's stack from its own files (manifests, existing CLAUDE.md) rather than assuming one. A skill hardcoded to one specific project's layout doesn't belong in `skills/`.
- **Load on demand** — each `SKILL.md` stays lean; detail the main workflow doesn't need on every invocation (checklists, per-mode templates, output formats) lives in `references/*.md` and is loaded only when that step needs it.
- **One skill per folder, nested only when it routes** — a folder only gains sub-skill folders when it genuinely routes between more than one specialized skill (today, just `review/`).

## Contributing

1. Fork the repository and create a branch for your work.
2. Follow the conventions above — required frontmatter (`name`, `description` written as concrete trigger phrases), the `references/` pattern for on-demand detail, and the labeling discipline for any spec/design output.
3. "Testing" a skill means walking its workflow against a real task in a real project, or using the `skill-creator` skill's eval tooling if you have it available.
4. Open a PR describing what changed and why.

This library pairs well with [Superpowers](https://github.com/obra/superpowers) for the surrounding process skills (TDD enforcement, subagent-driven execution, git worktree isolation) — several skills here reference Superpowers' `subagent-driven-development` and `executing-plans` for orchestrating multi-task plans, though none of it is a hard dependency.

## License

MIT License — see [LICENSE](LICENSE) for details.
