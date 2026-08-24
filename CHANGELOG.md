# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.0.1] - 2026-08-25

### Added

- Initial release of the AI Engineering Skills library: 11 stack-agnostic Claude Code
  Agent Skills covering the full software engineering lifecycle —
  `discovery`, `spec`, `architecture`, `design`, `implement`, `test`, `review`, `operate`,
  plus the cross-cutting `research`, `brainstorming`, and `insights` skills.
- `design` and `implement` support 12 stacks across two families: REST/full-stack API
  (Python pipeline/script, Go+Fiber, Next.js+Prisma, Spring Boot, NestJS, FastAPI, Rust)
  and Client UI (Angular, React, Android, iOS, Flutter).
- `review` auto-detects CODE mode (11 criteria) vs. SDS mode (12 criteria); defers to
  `architecture`'s UPGRADE mode for whole-system/topology review requests.
- Shared Implementation Readiness gate (`READY` / `PARTIALLY_READY` / `BLOCKED`) chaining
  `spec` → `design` → `implement`.
- `agents/` — one Claude Code subagent per top-level skill, documenting each agent's tool
  scope and approval gates alongside its skill's workflow.
- Project documentation: `README.md`, `CLAUDE.md`, `LICENSE` (MIT).

[0.0.1]: https://github.com/alexphan32/ai-engineering-skills/releases/tag/v0.0.1
