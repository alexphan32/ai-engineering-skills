---
name: discovery
description: >
  Use as the first pass on an unfamiliar codebase or ambiguous request, before /spec, /design, or
  /implement — "tôi mới vào dự án này", "tìm hiểu hệ thống trước khi làm feature X", "context nào
  đã có sẵn", or any request touching an existing system/module/feature you don't yet know enough
  about. Auto-detects the stack (frontend, mobile, backend, scripts). Also use when it's unclear
  whether a capability already exists before building it again. Do NOT use once the area is
  already understood, or for whole-system documentation (`/architecture`) or detailed requirements
  gathering (`/spec`).
---

## OVERVIEW

A fast, bounded context-gathering pass — not a deliverable. Every downstream skill (`spec`,
`design`, `architecture`, `implement`, `test`, `operate`) assumes the agent already knows the
target system's shape. Skip straight to one of them when that's false, and you get confident
answers built on wrong assumptions: an SRS re-specifying behavior that already exists
differently, a design ignoring an existing convention, code duplicating a helper three files away.

**Core principle:** discovery answers "what already exists and what's still unknown" — never
"what should exist" (`/spec`), "how should it be built" (`/design`), or "how does every module
fit together" (`/architecture`, exhaustive by design). A pass that outlasts the task it's
unblocking has failed at being lightweight.

**Output:** a short Discovery Brief — in chat for a small request, saved to
`docs/01-discovery/<topic>-YYYY-MM-DD.md` only when the finding is substantial enough that the next
skill (or a teammate) would otherwise re-derive it. Never a required artifact on its own.

---

## WHEN TO USE

```
Request touches an existing system/module/feature
           ↓
  Can you already state: its purpose, current behavior, and where its docs/tests live?
           ↓ NO                                    ↓ YES
     Run discovery                          Skip straight to spec/design/architecture/implement
           ↓
  SCAN → LOCATE → ASSESS → ROUTE
```

**Do NOT use discovery when:**
- The target is a brand-new module/service with no prior art to reconcile with — go straight to `/spec`.
- The ask is "document the whole system" — that's `/architecture`'s mandatory 5-step flow, not a discovery pass.
- Requirements are the actual gap, not context — that's `/spec`'s GATHER step.
- You already ran discovery on this exact area earlier in the session — don't re-run it.

---

<HARD-GATE>
Do NOT hand off to another skill until:
1. You've identified the project's stack/type (or confirmed "greenfield, no prior art")
2. You've checked for existing docs covering the target area — CLAUDE.md, `docs/`, README,
   any SRS/SDS/architecture doc that already mentions it
3. You've stated what's still unknown, not just what you found
4. You've named the specific next skill (not "continue investigating")

Do NOT claim "codebase understood" from filenames alone — open and read the files that look
relevant before asserting what they do.
</HARD-GATE>

**Violating any gate = violating the spirit of the skill.** Common rationalizations:

| Rationalization | Reality |
|----------------|---------|
| "The file names make it obvious what this does" | Names lie or go stale. Read the actual code before asserting behavior. |
| "I'll just start implementing and figure it out as I go" | That's how duplicate helpers and re-specified behavior happen. Ten minutes of discovery is cheaper than a rewrite. |
| "This is a small request, discovery is overkill" | Scope it to match — a 2-minute scan beats zero. Skipping ≠ scoping down (and spending more time on discovery than the task itself means you scoped it wrong too). |
| "I already know this codebase from an earlier session" | Code drifts between sessions — re-verify the specific area, don't rely on memory. |
| "There's no existing doc, so nothing exists to find" | Absence of docs isn't absence of code — grep/glob the actual source before concluding "greenfield," and don't treat a stale doc as ground truth either. |
| "I'll route to the next skill now, the unknowns are implicit" | State what's still unknown explicitly — the next skill acts on what you wrote, not what you meant. |

---

## WORKFLOW (4 STEPS)

### 1. SCAN — Orient on the project

- Glob for manifest/config files at root for the stack signal (table below) → language,
  framework, stack
- Read `CLAUDE.md` if present — it usually states project purpose, module architecture, and
  where things live; trust it over guessing
- No `CLAUDE.md`? Don't guess project purpose from directory names — check `README.md`, the
  manifest's own description field (`package.json` `"description"`, `pyproject.toml` `[project]
  description`), or a `docs/` index instead
- No manifest, no prior code touching the request's area → state "greenfield," stop here, route
  straight to `/spec`

**Stack signals** — match the first row whose signal file(s) are present; full per-stack detail
(entry point, folder conventions, what to read next) is in `references/stack-signatures.md`,
load it once the stack is identified:

| Signal | Stack |
|---|---|
| `angular.json` | Angular (frontend) |
| `package.json` with `react`/`react-dom` but no `next` and no `angular.json` | React (frontend, SPA/CRA/Vite) |
| `package.json` with `next` | Next.js (frontend/full-stack — see `design`'s MODE C) |
| `pubspec.yaml` with a `flutter:` section | Flutter (mobile) |
| `build.gradle`/`build.gradle.kts` + `AndroidManifest.xml` | Android (mobile, native) |
| `*.xcodeproj`/`*.xcworkspace`, `Podfile`, or `Package.swift` + `.swift`/`.m` sources | iOS (mobile, native) |
| `pyproject.toml`/`requirements.txt` with `fastapi` | Python backend — FastAPI |
| `package.json` with `@nestjs/core`, or a `nest-cli.json` at root | NestJS backend |
| `Cargo.toml` with `axum`/`actix-web`/`rocket`/`warp` in dependencies | Rust backend |
| `go.mod` | Go backend |
| `pom.xml`/`build.gradle` with `spring-boot-starter*` (JVM, no Android manifest) | Spring Boot / JVM backend |
| Loose `*.sh`/`*.ps1`/`*.py` files, no framework manifest, often cron/scheduler-driven | Script-based system |
| `pyproject.toml`/`requirements.txt` with no web framework and a "Module Architecture" section in CLAUDE.md | Python data pipeline |

If two signals match (e.g. a monorepo with both a `frontend/` Angular app and a `backend/`
FastAPI service), scan each subtree separately — state which stack applies to which path rather
than picking one for the whole repo.

### 2. LOCATE — Find existing context for the specific area

- Glob `docs/**/*.md` for SRS/SDS/architecture docs mentioning the feature/module by name
- Grep the codebase for the feature/module name or its closest synonym — confirm whether it
  already exists, partially exists, or doesn't
- Checking whether a capability already exists, not locating a named one? Search by
  concept/behavior, not just the exact name — an equivalent often exists under different
  terminology (an English name vs. the user's Vietnamese description, an older/abandoned
  attempt, a differently-named helper). Grep related keywords and scan sibling modules before
  concluding "doesn't exist yet."
- Check for existing tests covering the area — tests document actual behavior better than
  comments do
- Note doc/code mismatches explicitly — don't silently trust whichever one you read first

### 3. ASSESS — State what's known vs. unknown

Write (in chat, or the Discovery Brief if saved) exactly two short lists:
- **Known:** purpose, current behavior, relevant files/docs, existing conventions to follow
- **Unknown / open:** anything the next skill will need that you couldn't find — flag
  `[OPEN QUESTION]` for a business question (`/spec`'s own blocking label, see its GATE step) or
  `[NEEDS DESIGN]` for a technical-mechanics question (the label `/spec` uses to hand mechanics to
  `/design`), matching the labels the next skill already writes so the handoff needs no
  translation. Flag it, don't resolve it: guessing at business intent here is the exact
  re-specification risk `/spec`'s GATHER step exists to replace with a real answer.

### 4. ROUTE — Name the next skill

| Situation | Route to |
|---|---|
| Business behavior/requirements unclear or missing | `/spec` |
| Requirements clear, technical approach/design unclear | `/design` |
| Need exhaustive, navigable docs of the whole system | `/architecture` |
| Everything above is already clear, just need code | `/implement` |
| Existing behavior's test coverage is the actual gap (not requirements or design) | `/test` |
| Code/design already exists and needs a quality/security check before merge | `/review` |
| System already built; question is deployment, observability, or incident response | `/operate` |
| Need to evaluate an external library/technology before deciding | `/research` |
| Genuinely unsure which of the above fits | `/brainstorming` |

State the route and the specific unknowns the next skill should treat as open — don't just say
"use /spec," say what /spec still needs to gather.
