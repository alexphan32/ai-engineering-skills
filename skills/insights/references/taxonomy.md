# Full Taxonomy — Classification System

> Loaded during Phase 3 CLASSIFY. All type, stack, pattern, and severity definitions.

---

## Type (insight type)

| Type | Description | Example |
|------|-------|-------|
| `bug_fix` | Code fix for crashes, wrong logic, or wrong output | Off-by-one pagination bug, unhandled null, race condition on shared state |
| `perf_optimization` | Improving speed or resource usage | Fixing an N+1 query, memoizing an expensive re-render, batching writes |
| `best_practice` | Rules/methods proven to be effective on this project | Always run migrations before seeding, always validate DTOs at the controller boundary |
| `lesson_learned` | Lessons from failures or mistakes | Don't share a Prisma client across serverless invocations without pooling, don't mutate Redux state directly |
| `arch_decision` | Important architectural choice and why it was made | Chose event-driven over sync REST for order fulfillment, split a monolith route module by bounded context |

`arch_decision`, `best_practice`, and `lesson_learned` are almost never reliably auto-detectable
from a keyword scan — `analyze_sessions.py` only scores `bug_fix` vs `perf_optimization` vs
`general`. Assign the other three types by actually reading the session in Phase 2/3.

---

## Stack (which part of the system the insight applies to)

Mirrors the stack families this repo's `design`/`review`/`implement` skills already use —
tag every finding so a future session on a *different* stack doesn't get an irrelevant memory
injected just because the symptom name matches.

| Tag | Stack | Family |
|-----|-------|--------|
| `python-pipeline` | Python data pipeline / script / automation module | REST/full-stack — Mode A |
| `go-fiber` | Go + Fiber REST API | REST/full-stack — Mode B |
| `nextjs-prisma` | Next.js + Prisma full-stack app | REST/full-stack — Mode C |
| `spring-boot` | Spring Boot REST API (Java) | REST/full-stack — Mode D |
| `nestjs` | NestJS REST API | REST/full-stack — Mode E |
| `fastapi` | FastAPI REST API | REST/full-stack — Mode F |
| `rust` | Rust service | REST/full-stack — Mode G |
| `angular` | Angular frontend | Client UI — Mode H |
| `react` | React SPA | Client UI — Mode I |
| `android` | Android app (Kotlin) | Client UI — Mode J |
| `ios` | iOS app (Swift) | Client UI — Mode K |
| `flutter` | Flutter app (Dart) | Client UI — Mode L |
| `shared-infra` | CI/CD, containers, deployment config, observability | Cross-cutting |
| `database` | Schema, migrations, query design (when not owned by one app's stack) | Cross-cutting |
| `other` | Doesn't fit any of the above — say why in the finding | Fallback only |

### Stack-detection signals (what `analyze_sessions.py` looks for)

Same idea as `architecture`/`design`'s manifest-based auto-detection — look at file paths and
tool inputs referenced in the session, not what the user calls the project:

| Stack | Signals |
|-------|---------|
| `python-pipeline` | `.py` files, `pyproject.toml`, `requirements.txt` — and none of the `fastapi` signals below |
| `fastapi` | `fastapi`, `pydantic`, `uvicorn` keywords/imports |
| `go-fiber` | `.go` files, `go.mod`, `gofiber`/`fiber.New` |
| `rust` | `.rs` files, `Cargo.toml`, `actix`/`axum`/`tokio` |
| `nextjs-prisma` | `next.config.*`, `prisma/schema.prisma`, `.tsx`/`.ts` + `next` |
| `spring-boot` | `.java` files, `pom.xml` or `build.gradle` + `springframework` |
| `nestjs` | `@nestjs/`, `nest-cli.json` |
| `angular` | `angular.json`, `@angular/` |
| `react` | `.jsx`/`.tsx` + `react` import, without `next`/`@angular`/`@nestjs` signals |
| `android` | `AndroidManifest.xml`, `.kt` files, `build.gradle` without `springframework` |
| `ios` | `.swift` files, `.xcodeproj`, `Podfile` |
| `flutter` | `pubspec.yaml`, `.dart` files |
| `database` | `.sql` files, `migrations/`, `schema.prisma` referenced on its own |
| `shared-infra` | `Dockerfile`, `docker-compose`, `.github/workflows/`, Terraform/K8s manifests |

If two stacks' signals both fire (e.g. a Next.js+Prisma repo touching a `migrations/` folder),
tag by what the *fix* actually targeted, not just what files were touched in passing.

---

## Pattern (short free-form slug — used for grouping during consolidation)

Unlike `type`/`stack`/`severity`, pattern is **not a fixed enum** — an exhaustive list can't
cover every stack. Write a short kebab-case slug that names the mechanism, e.g. `n-plus-one-query`,
`race-condition`, `null-reference`, `stale-cache`, `unbounded-rerender`, `auth-bypass`,
`config-drift`, `dependency-conflict`, `deadlock`, `memory-leak`, `state-mutation`,
`build-config-error`. Reuse an existing slug from `MEMORY.md`/prior findings whenever the
mechanism is the same, even across different stacks — that's what makes consolidation
(`references/consolidation-rules.md`) possible.

---

## Severity (severity level)

| Severity | Criteria |
|----------|----------|
| `critical` | Causes a crash, outage, or data corruption/loss |
| `major` | Causes wrong results or a silent failure without crashing |
| `minor` | Code quality, warning, non-critical edge case |

---

## Priority Order (when saving memory)

1. **Critical + systemic** — save first, most important
2. **Critical + isolated** — save due to large impact despite being rare
3. **Major + recurring** — save because it occurs frequently
4. **Best practices / lessons learned** — save for reference
5. **Minor issues** — save only if there's a distinctive pattern
