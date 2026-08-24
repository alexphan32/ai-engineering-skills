---
name: design
description: >
  Use when the user says "/design", "tạo SDS", "thiết kế module", or has an SRS and needs a
  technical design before implementation. Auto-detects the stack — backend/full-stack (Python
  pipeline, Go/Fiber, Next.js+Prisma, Spring Boot, NestJS, FastAPI, Rust) or frontend/mobile UI
  (Angular, React, Android, iOS, Flutter). PREREQUISITE: `/spec` first — if no SRS exists, suggest
  that instead.
---

# Design (SDS)

## Overview

Design a technical solution from an SRS → produce a Software Design Specification. The second step in the pipeline: spec → design → implement.

**Core principle:** SPEC defines WHAT; SDS defines HOW. A *business* question the SRS left open
is `[NEEDS SPEC CLARIFICATION]` (`references/decision-records.md` §1) — not a technical call to
make quietly.

**12 modes — auto-detected:**
- **MODE A**: Python data pipeline or script/automation module (CLAUDE.md "Module Architecture" detected)
- **MODE B**: Go/Fiber REST API (Clean Architecture, MongoDB)
- **MODE C**: Next.js + Prisma full-stack (App Router, Server Components/Actions)
- **MODE D**: Spring Boot REST API (Java, layered architecture + JPA)
- **MODE E**: NestJS REST API (TypeScript, Nest modules + TypeORM/Prisma)
- **MODE F**: FastAPI REST API (Python, Pydantic schemas + SQLAlchemy)
- **MODE G**: Rust REST API (Axum/Actix-web, Hexagonal/Ports-and-Adapters)
- **MODE H**: Angular frontend feature (standalone components, RxJS/signals)
- **MODE I**: React SPA frontend feature (CSR — a Next.js App Router project is MODE C instead)
- **MODE J**: Android mobile feature (Kotlin, MVVM + Compose/View)
- **MODE K**: iOS mobile feature (Swift, MVVM + SwiftUI/UIKit)
- **MODE L**: Flutter mobile feature (Dart, layered + BLoC/Riverpod/Provider)

MODE B/C/D/E/F/G are "REST/full-stack API" siblings — same inside-out discipline (domain model →
data access → service logic → transport layer), different stack conventions. MODE H/I/J/K/L are
"Client UI" siblings — same inside-out discipline adapted to a client app (data/API layer → state
management → screen/component composition → navigation), instead of a server's request/response
cycle. Don't let familiarity skip the discipline, and don't let the discipline blur stack-specific
idioms — each mode's template is what's idiomatic for that framework, not a generic translation of
another. `architecture/references/backend-script-patterns.md` (Rust, FastAPI, scripts),
`frontend-patterns.md` (Angular, React), and `mobile-patterns.md` (Android, iOS, Flutter) are the
stack-truth source for each new mode's folder layout and idioms — this skill's job is turning an
SRS into a design that lands correctly inside that layout, not re-deciding the layout itself.

## When to Use

```
SRS exists (docs/03-srs/ — shared by MODE A and MODE B..L)
           ↓
  CLAUDE.md has "Module Architecture" → MODE A
  User says "Go", "Fiber" → MODE B          | go.mod present
  User says "Next.js", "App Router", "Server Action", "Prisma" → MODE C | package.json has "next"
  User says "Spring Boot", "Spring", "Java REST" → MODE D               | pom.xml/build.gradle has spring-boot-starter
  User says "NestJS", "Nest" → MODE E                                   | package.json has "@nestjs/core"
  User says "FastAPI", "Pydantic" → MODE F                              | pyproject.toml/requirements.txt has fastapi
  User says "Rust", "Axum", "Actix" → MODE G                            | Cargo.toml present
  User says "Angular" → MODE H                                         | angular.json present
  User says "React", "SPA" (not Next.js) → MODE I                       | package.json has "react" but not "next"
  User says "Android", "Kotlin", "Compose" → MODE J                     | build.gradle(.kts) with com.android.application
  User says "iOS", "Swift", "SwiftUI" → MODE K                          | *.xcodeproj/Podfile/Package.swift present
  User says "Flutter" → MODE L                                          | pubspec.yaml present
           ↓
  DETECT → PREREQ → CHECK_EXISTING → ANALYZE → DESIGN → DRAFT → VALIDATE → GATE → FINALIZE
           ↓
  Next: /review → /implement
```

**Do NOT use `/design` when:**
- No SRS exists → suggest `/spec` first
- Reviewing an existing SDS → use `/review`
- Writing code → use `/implement`
- Writing requirements → use `/spec`

## Reference Templates

Load on demand when drafting:

| Topic | File | When |
|-------|------|------|
| System scale & architecture fit checklist | `.claude/skills/architecture/references/system-scale-checklist.md` | **Load first**, in ANALYZE, before any other checklist below — classifies Tier 1 (MVP)/Tier 2 (async/growing)/Tier 3 (enterprise/distributed), which sets how much of the Security/Performance/Distributed/Data-Integrity/Operations-Readiness checklists apply. Every SDS states this classification |
| Template A (pipeline) | `.claude/skills/design/references/sds-template-python-pipeline.md` | Drafting MODE A SDS |
| Template B (Go/Fiber API) | `.claude/skills/design/references/sds-template-go-fiber-api.md` | Drafting MODE B SDS |
| Template C (Next.js + Prisma) | `.claude/skills/design/references/sds-template-nextjs-prisma.md` | Drafting MODE C SDS |
| Template D (Spring Boot) | `.claude/skills/design/references/sds-template-spring-boot-api.md` | Drafting MODE D SDS |
| Template E (NestJS) | `.claude/skills/design/references/sds-template-nestjs-api.md` | Drafting MODE E SDS |
| Template F (FastAPI) | `.claude/skills/design/references/sds-template-fastapi-api.md` | Drafting MODE F SDS |
| Template G (Rust) | `.claude/skills/design/references/sds-template-rust-api.md` | Drafting MODE G SDS |
| Template H (Angular) | `.claude/skills/design/references/sds-template-angular-frontend.md` | Drafting MODE H SDS |
| Template I (React SPA) | `.claude/skills/design/references/sds-template-react-frontend.md` | Drafting MODE I SDS |
| Template J (Android) | `.claude/skills/design/references/sds-template-android-mobile.md` | Drafting MODE J SDS |
| Template K (iOS) | `.claude/skills/design/references/sds-template-ios-mobile.md` | Drafting MODE K SDS |
| Template L (Flutter) | `.claude/skills/design/references/sds-template-flutter-mobile.md` | Drafting MODE L SDS |
| API design checklist (all modes) | `.claude/skills/design/references/api-design.md` | Drafting Section 4/API Specification in DRAFT for MODE B/C/D/E/F/G; ANALYZE, before shaping any endpoint/Server Action |
| Database design checklist (all modes) | `.claude/skills/design/references/database-design.md` | DESIGN, when shaping the schema/data-model layer (Entity/Prisma model/JPA entity/collection); any module introducing/modifying persistent schema — complements `data-integrity-checklist.md`'s invariant focus with indexing/migration/schema-fit |
| Security checklist (all modes) | `.claude/skills/design/references/security-checklist.md` | Threat-modeling in ANALYZE; drafting Section 7 (Security Design) in DRAFT; every MODE B/C/D/E/F/G SDS, and MODE A when the pipeline touches secrets/external input/PII; MODE H/I/J/K/L for the client-relevant subset only (token storage, XSS/deep-link/intent validation, cert pinning) — the server-side subset (SQL injection, rate limiting) is stated N/A there |
| Performance checklist (all modes) | `.claude/skills/design/references/performance-checklist.md` | Capturing the performance baseline in ANALYZE; drafting Section 9 (Performance Design) in DRAFT; every MODE B/C/D/E/F/G SDS, and MODE A when complexity/memory is non-trivial; MODE H/I/J/K/L for the client-relevant subset (list virtualization, bundle/app size, image loading, startup/render time) instead of server load/RPS |
| Distributed systems & async checklist | `.claude/skills/design/references/distributed-systems-checklist.md` | When the feature crosses a service boundary, publishes/consumes a message (Kafka/queue), runs async work, or calls an external system (Core Banking, payment gateway) — Section 10 (Distributed & Async Design) in DRAFT for MODE B/C/D/E/F/G; MODE A only for checkpointed-batch concerns; MODE H/I/J/K/L only when the app does offline-first local persistence with background sync (then §10 covers conflict resolution/replay), otherwise N/A |
| Data integrity checklist | `.claude/skills/design/references/data-integrity-checklist.md` | Any module that owns persistent state — DB constraints/invariants, referential integrity, duplicate prevention, atomicity, lost-update, audit-trail shape, reconciliation. Drafted into Processing Logic/Output Specifications, not a new numbered section. MODE H/I/J/K/L: N/A unless the app owns local persistent state (IndexedDB/Room/Core Data/drift/hive) it must keep consistent with the server |
| Operations readiness checklist | `.claude/skills/design/references/operations-readiness-checklist.md` | Any module deployed as its own service/process — observability, health checks, graceful shutdown, config vs secret vs feature-flag, dependency-chain depth, resource bounds, and (only when the SRS states a target) availability/DR and data lifecycle. Appended as an "Operations Readiness" section, same place as Design Decisions. MODE H/I/J/K/L: N/A — a client app isn't a deployed service; note crash reporting/release-monitoring wiring instead if the SRS mentions it |
| Decision records, alternatives, risks, implementation mapping | `.claude/skills/design/references/decision-records.md` | DESIGN, when a costly-to-reverse decision comes up; DRAFT, for the Design Decisions/Risks/Implementation Mapping sections every mode appends |

## Workflow (9 Steps)

### 0. DETECT — Project mode

- CLAUDE.md has "Module Architecture" or "Data Pipeline" section → MODE A
- User specifies "Go", "Fiber" (or `go.mod` present) → MODE B
- User specifies "Next.js", "App Router", "Server Action", "Prisma"; or `package.json` has `next` + `prisma`/`@prisma/client` → MODE C
- User specifies "Spring Boot", "Spring", "Java REST"; or `pom.xml`/`build.gradle` has `spring-boot-starter` → MODE D
- User specifies "NestJS", "Nest"; or `package.json` has `@nestjs/core` → MODE E
- User specifies "FastAPI", "Pydantic"; or `pyproject.toml`/`requirements.txt` has `fastapi` → MODE F
- User specifies "Rust", "Axum", "Actix"; or `Cargo.toml` present → MODE G
- User specifies "Angular"; or `angular.json` present → MODE H
- User specifies "React", "SPA" and the project is NOT Next.js; or `package.json` has `react` but not `next` → MODE I
- User specifies "Android", "Kotlin", "Jetpack Compose"; or `build.gradle`/`build.gradle.kts` has `com.android.application` → MODE J
- User specifies "iOS", "Swift", "SwiftUI"; or `*.xcodeproj`/`Podfile`/`Package.swift` present → MODE K
- User specifies "Flutter"; or `pubspec.yaml` present → MODE L
- Ambiguous (e.g. generic "REST API" with no stack cue, or "frontend" with no framework cue)? AskUserQuestion once — don't guess between siblings within a family from a generic phrase alone
- **Feature spans more than one deployable stack/process** (e.g. a backend API plus a separate
  worker/consumer, or a backend plus a distinct frontend app)? Don't force it into one mode's
  template — run DETECT once per stack and produce one SDS per stack (`M-XX-api`, `M-XX-worker`),
  each following its own mode's template, cross-referencing the others in Dependencies rather than
  merging distinct architectures into a single document

### 1. PREREQ — Verify SRS exists and is usable

- **MODE A**: Glob `docs/03-srs/*.md` (excluding `F-*.md`) → read section for this module
- **MODE B..L**: Glob `docs/03-srs/F-XX*.md` → read feature SRS. A submodule-split feature returns
  a thin `F-XX-*.md` parent plus `F-XX.1-*.md`, `F-XX.2-*.md`... children — read the parent for
  shared actors/invariants, then only the child(ren) this module actually implements; design one
  `M-XX.N` per `F-XX.N` submodule, not one giant SDS covering all of them
- **Not found? STOP**: "SRS doesn't exist yet. Run `/spec` first."
- **Check its readiness gate** (present in newer SRS docs, may be absent in legacy ones):
  - `BLOCKED` → **STOP** and report the unresolved blocking questions.
  - `PARTIALLY_READY` → design only what the SRS marked ready; state what's deferred. A shared
    invariant (e.g. "no double-execution") still constrains the ready scope even though the
    blocked side's own mechanics aren't designed here.
  - `READY` / no gate present → proceed, but any business question you hit along the way is
    `[NEEDS SPEC CLARIFICATION]` (`references/decision-records.md` §1), not yours to decide.

### 2. CHECK_EXISTING — Avoid overwrites

- Glob `docs/04-sds/M-{XX}-*.md` (MODE A and MODE B..L share this folder)
- If exists → AskUserQuestion: "Update specific sections or create new version?"
- If update: only modify specified sections

### 3. ANALYZE — Extract from SRS

- **Scale Tier (all modes) — first thing in ANALYZE**: **[TOOL ACTION]** Check the SRS's
  Dependencies table ("Team Controls It?") and NFR-04 (Compliance & Availability) first —
  `/spec` already captured these as business facts — before re-asking the user. Answer the 5
  classification questions in `.claude/skills/architecture/references/system-scale-checklist.md` §0
  and state the resulting tier (Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed)
  plus a one-line reason. This sets how much of the Security/Performance/Distributed/Data-
  Integrity/Operations-Readiness checklists below get walked in full vs. their baseline subset
  (§4's Applicability Matrix) — don't walk the full distributed-systems checklist for a feature
  that answered "no" to all 5 questions, and don't wave through a Tier 3 signal (external
  critical-system integration, multi-team ownership, a stated compliance requirement) just
  because the rest of the system looks small.
- **Architecture Context (all modes)**: Glob for existing services/modules adjacent to this
  feature (e.g. `NotificationService`, a shared `AuditLog` table). Classify every touched
  component **Existing** / **Modified** / **New** (justify why nothing existing fits) /
  **External**. A new component duplicating an existing one's responsibility is an architecture
  conflict, not a free choice — it needs a stated reason.
- **Module scope check (all modes) — before DESIGN**: mirrors `/spec`'s submodule check. If the
  Implementation Mapping this module is heading toward (`references/decision-records.md` §4) would
  span more sub-domains than one SDS can hold clearly — each with its own entities/use
  cases/interfaces, but all still one bounded context sharing the same actors and data ownership —
  split into `M-XX.1-sub-name.md`, `M-XX.2-sub-name.md`... with `M-XX` itself left as a thin
  parent: shared Architecture Context, cross-submodule Data Integrity/Distributed concerns, and a
  table pointing to each submodule file. A genuinely independent capability doesn't belong here —
  that's `/spec`'s own capability split, landing as its own top-level `M-XX`, not a submodule of
  this one.
- **MODE A**: **[TOOL ACTION]** Glob upstream SDS files → read exact output column names → use those names (never invent)
- Input schema, output schema, config keys, processing pipeline, dependencies
- **[TOOL ACTION]** Answer the threat-modeling questions in `references/security-checklist.md` (assets, trust boundaries, auth mechanism, authorization model, sensitive data, attack surface, external dependencies, failure/abuse scenarios) before DESIGN — Section 7 is drafted from this, not bolted on after the endpoints are shaped
- **[TOOL ACTION]** Capture the performance baseline from `references/performance-checklist.md` §0 (RPS/QPS, concurrent users, peak multiplier, payload size, P95/P99 latency target, error-rate target) — if the SRS doesn't state one, mark `[PERF TARGET NEEDED — SRS §X.Y or user input]` rather than inventing a number; Section 9's pagination sizes, cache TTLs, connection pool sizes, and concurrency bounds are all sized against this baseline
- **[TOOL ACTION]** If the feature crosses a service boundary, publishes/consumes a message, runs anything asynchronously, or calls an external system (Core Banking, payment gateway, another microservice): answer the 8 questions in `references/distributed-systems-checklist.md` §0 (source of truth, data owner, consistency requirement, sync vs. async, duplicate/lost-message behavior, crash-mid-transaction behavior, downstream-unavailable behavior) before DESIGN — don't pick a message broker before answering these
- **[TOOL ACTION]** If the feature exposes an API endpoint or Server Action (MODE B/C/D/E/F/G): walk `references/api-design.md` — resource naming, status codes, response envelope, pagination/versioning — before DESIGN, so DRAFT's Section 4 isn't reinventing conventions per endpoint
- **[TOOL ACTION]** MODE H/I/J/K/L: identify every backend endpoint this feature calls (glob for an existing API client/service layer first — never invent an endpoint contract; if the backend SDS doesn't exist yet, mark `[NEEDS BACKEND SDS]` rather than guessing its shape) and every screen-level state (loading/empty/error/success) it must render
- **[TOOL ACTION]** If the feature introduces/modifies persistent schema (new/changed table, collection, or durable output another system reads as fact): walk `references/database-design.md` — indexing derived from the actual query access pattern, migration safety for changes to a populated table, schema fit — before `references/data-integrity-checklist.md`, which asks whether that shape holds under concurrent/adversarial callers
- **[TOOL ACTION]** If the feature owns persistent state (new/changed table, collection, or durable output): walk `references/data-integrity-checklist.md` — which invariants need a DB constraint (not just app validation), delete/update behavior per FK, audit-trail shape for any action `security-checklist.md` §11 already requires logging
- **[TOOL ACTION]** If the feature deploys as its own service/process: walk `references/operations-readiness-checklist.md` — what readiness/liveness check, shutdown sequence for any consumer/worker, which new thresholds are Configuration (operator-tunable) vs. Code (compile-time), depth of the synchronous call chain on the critical path. Capture an SRS-stated availability/RTO/RPO target here; if none, mark `[AVAILABILITY TARGET NEEDED]` and move on
- **MODE B**: Entities, repository interfaces, service interfaces, use cases, API endpoints
- **MODE C**: **[TOOL ACTION]** Glob `prisma/schema.prisma` → read existing models before designing new ones or adding fields (never invent field names/types on a model another feature owns). Then: Prisma models touched, which fields this feature owns vs. reads-only, data-access reads needed (`lib/*.ts`), Server Action writes needed, routes/pages, auth/session requirements
- **MODE D**: **[TOOL ACTION]** Glob existing `**/domain/*.java` or `**/entity/*.java` → read existing JPA entities before adding fields/relations another module owns. Then: entities, repository query methods, service boundaries (`@Transactional` scope), controller endpoints, `@PreAuthorize`/Security config requirements
- **MODE E**: **[TOOL ACTION]** Detect ORM first — Glob `package.json` for `@nestjs/typeorm` vs `@prisma/client`, and if Prisma, read `prisma/schema.prisma` for existing models (same never-invent rule as MODE C). Then: entities/models, DTOs (request/response split), service methods, Guards/Roles needed, module wiring
- **MODE F**: **[TOOL ACTION]** Glob existing `app/features/*/repository.py` → read existing SQLAlchemy models before adding fields/relations another feature owns. Then: SQLAlchemy models touched, repository methods, service orchestration (what's injected via `Depends()`), Pydantic request/response schemas, router endpoints, async-vs-sync boundary (is the DB driver/HTTP client actually async-capable, or does this route need `run_in_threadpool`)
- **MODE G**: **[TOOL ACTION]** Glob existing `domain/*.rs` → read existing structs/port traits before adding fields another module owns. Then: domain structs/enums + port traits, application-layer use cases (functions/structs taking `&dyn Trait`), infrastructure adapters (axum/actix handlers, sqlx/diesel repo impls), typed error enum for this feature's failure modes
- **MODE H**: **[TOOL ACTION]** Glob existing `features/*/services/*.ts` → read existing state services before duplicating one. Then: which backend endpoint(s) this feature calls, the state service's shape (`BehaviorSubject`/signal fields), smart-container vs. presentational component split, route(s) and lazy-loading boundary, `async` pipe / `takeUntilDestroyed()` usage points
- **MODE I**: **[TOOL ACTION]** Glob existing `features/*/api/*.ts` and `features/*/hooks/*.ts` → read existing data-fetching hooks before duplicating one. Then: API call functions, data-fetching hook (React Query/SWR — cache key, staleness, invalidation trigger), local vs. lifted vs. Context state, component composition, route(s)
- **MODE J**: **[TOOL ACTION]** Glob existing `data/repository/*.kt` → read existing Repository implementations before duplicating one. Then: Repository (single source of truth, Room + Retrofit/Ktor sources), optional domain use case, ViewModel (`StateFlow`/`LiveData` fields, no `Context`/`View` reference), Composable/View, navigation destination
- **MODE K**: **[TOOL ACTION]** Glob existing repository/service types → read them before duplicating one. Then: Repository/Service protocol (networking via `URLSession`, persistence via Core Data/SwiftData), ViewModel (`ObservableObject` published state), View/ViewController, navigation flow, whether this screen's domain complexity justifies Clean/VIPER over plain MVVM (`architecture/references/mobile-patterns.md` §2)
- **MODE L**: **[TOOL ACTION]** Glob existing `lib/features/*/domain/` → read existing entities/repository interfaces before duplicating one. Then: domain entities + repository interface (no Flutter/dio imports), data-layer repository implementation (remote `dio`/`http` + local `drift`/`hive`), state-management choice (BLoC event/state pair, or Riverpod provider) per Axis 2's domain-complexity answer, widget tree

### 4. DESIGN — Layer by layer

- **MODE A**: Input validation → Processing steps → Output schema → Config/thresholds → Error handling
- **MODE B**: Entity → Repository → Service → UseCase → Handler/DTO → Infrastructure (inside-out)
- **MODE C**: Prisma model (schema) → Data-access read functions (`lib/*.ts`) → Server Action write functions → Route/Page (Server/Client Component split) — inside-out, same discipline as MODE B, adapted to Next.js's colocated frontend/backend
- **MODE D**: JPA Entity → Repository → Service (with explicit `@Transactional` boundaries) → Controller/DTO → Security/exception config — inside-out, adapted to Spring's layered convention
- **MODE E**: Entity/Prisma model → Service (repository or `PrismaService` injected) → DTO (request/response, class-validator) → Controller → Module wiring — inside-out, adapted to Nest's module system
- **MODE F**: SQLAlchemy model → Repository → Service (`Depends()`-injected) → Pydantic schema (request/response) → Router (HTTP concern only) — inside-out, adapted to FastAPI's dependency-injection convention
- **MODE G**: Domain struct/enum + port trait → Application use case (`&dyn Trait`-typed) → Infrastructure adapter (axum/actix handler, sqlx/diesel repo impl) — inside-out, Rust's trait system as the port/adapter boundary
- **MODE H**: Backend API contract (what this feature calls) → State service (`BehaviorSubject`/signal) → Smart container component → Presentational components → Route/lazy-load boundary — inside-out, data layer first, screen last
- **MODE I**: API call functions → Data-fetching hook (React Query/SWR) → Local/lifted/Context state → Component composition → Route — inside-out, same order as MODE H adapted to hooks
- **MODE J**: Repository (Room + Retrofit/Ktor) → optional domain use case → ViewModel (`StateFlow`) → Composable/View → Navigation destination — inside-out, Google's recommended app architecture
- **MODE K**: Repository/Service protocol → ViewModel (`ObservableObject`) → View/ViewController → Navigation flow — inside-out, MVVM (or Clean/VIPER when domain complexity justifies it)
- **MODE L**: Domain entity + repository interface → Data-layer repository impl (`dio`/`http` + `drift`/`hive`) → State management (BLoC/Riverpod) → Widget tree → Navigation — inside-out, layered Clean Architecture
- **MODE H/I/J/K/L — accessibility pass** (design alongside the widget/component/screen layer, not after): every interactive element has an accessible name/role (`aria-label`/semantic HTML, `contentDescription`, `accessibilityLabel`, Widget `Semantics`), focus/traversal order matches visual order, color contrast meets WCAG AA, and any dynamic state change (loading/error/toast) is announced to assistive tech (`aria-live` or equivalent) — not just visually rendered

### 5. DRAFT — Write SDS

If the Module scope check (Step 3) triggered, write one file per submodule using
`docs/04-sds/M-XX.1-sub-name.md`, `docs/04-sds/M-XX.2-sub-name.md`... (same template as the mode
below, one per submodule) in place of the single file each MODE row names, plus a thin `M-XX`
parent file per the Step 3 note.

- **MODE A**: Load `references/sds-template-python-pipeline.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE B**: Load `references/sds-template-go-fiber-api.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE C**: Load `references/sds-template-nextjs-prisma.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE D**: Load `references/sds-template-spring-boot-api.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE E**: Load `references/sds-template-nestjs-api.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE F**: Load `references/sds-template-fastapi-api.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE G**: Load `references/sds-template-rust-api.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE H**: Load `references/sds-template-angular-frontend.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE I**: Load `references/sds-template-react-frontend.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE J**: Load `references/sds-template-android-mobile.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE K**: Load `references/sds-template-ios-mobile.md`, write `docs/04-sds/M-XX-module-name.md`
- **MODE L**: Load `references/sds-template-flutter-mobile.md`, write `docs/04-sds/M-XX-module-name.md`
- **All modes**: state the Scale Tier and its reason (from ANALYZE) in Architecture Context or a
  "Scale & Architecture Fit" note near the top of the SDS, before the mode-specific sections.
- **All modes**: append Design Decisions & Alternatives, Risks & Trade-offs, and Implementation
  Mapping per `references/decision-records.md`, plus (when applicable) a Data Integrity section per
  `references/data-integrity-checklist.md` and an Operations Readiness section per
  `references/operations-readiness-checklist.md` — after the mode-specific sections, before Test
  Plan. Same rule as Design Decisions §5: state "N/A — reason" rather than omitting a thin section.

### 6. VALIDATE — Quality gates

- **Challenge each costly-to-reverse decision** (`references/decision-records.md` §2) before GATE:
  state the strongest reason it could be wrong — a missed alternative, a Scale Tier signal it
  under- or over-weighs, an edge case it doesn't hold under — then say whether that reason
  actually survives scrutiny. A decision that's never been argued against reads as confidence,
  not as correctness; recording the challenge (even a one-line "considered X, rejected because Y")
  costs far less than finding out in `/review` or production that nobody stress-tested it.
- Scale Tier is stated with a one-line reason, and the depth of Sections 7/9/10 plus the Data
  Integrity/Operations Readiness sections matches `.claude/skills/architecture/references/system-scale-checklist.md`
  §4's Applicability Matrix for that tier — a Tier 1 SDS with a full Saga/circuit-breaker design,
  or a Tier 3 system with those sections silently N/A, is itself a finding
- Every output column has formula/logic with SRS source annotation
- Config keys have defaults + enums file path
- Upstream column names verified against upstream SDS (not invented)
- Every applicable `[MUST]` item in `references/security-checklist.md` is satisfied in Section 7 or marked `[SECURITY EXCEPTION — reason]` in Open Questions — no silent skips (MODE H/I/J/K/L: the client-relevant subset only — token storage, XSS/deep-link/intent validation)
- Every applicable `[MUST]` item in `references/performance-checklist.md` is satisfied in Section 9 or marked `[PERF EXCEPTION — reason]` in Open Questions — no silent skips (MODE H/I/J/K/L: the client-relevant subset only — list virtualization, bundle/app size, image loading)
- If the feature exposes an endpoint/Server Action: every applicable `[MUST]` item in `references/api-design.md` is satisfied in Section 4 or marked `[API DESIGN EXCEPTION — reason]` — no silent skips
- If the feature introduces/modifies persistent schema: every applicable `[MUST]` item in `references/database-design.md` is satisfied or marked `[DATABASE DESIGN EXCEPTION — reason]` — no silent skips
- If the feature is distributed/async (crosses services, uses messaging, calls an external system): every `[MUST]` item in `references/distributed-systems-checklist.md` is satisfied in Section 10 or marked `[DISTRIBUTED EXCEPTION — reason]` — data ownership, idempotency, state machine validation, and unknown-result handling are the ones most often skipped, never silently
- If the feature owns persistent state: every applicable `[MUST]` item in `references/data-integrity-checklist.md` is satisfied in Processing Logic/Output Specifications/Data Integrity or marked `[DATA INTEGRITY EXCEPTION — reason]` — no silent skips
- If the feature deploys as its own service/process: every applicable `[MUST]` item in `references/operations-readiness-checklist.md` is satisfied in the Operations Readiness section or marked `[OPS EXCEPTION — reason]` — a missing availability/RTO/RPO target is marked `[AVAILABILITY TARGET NEEDED]`, never invented
- MODE B: Every FR traced in SRS traceability table (§11.3), every endpoint has auth spec
- MODE C: Every FR traced in SRS traceability table; Prisma field write-ownership stated when a model is shared; every Server Action's return contract (`{success, data|error, fieldErrors?}`) specified; every DB-backed page's rendering mode (`force-dynamic`/revalidation) specified
- MODE D: Every FR traced in SRS traceability table; every endpoint's `@PreAuthorize`/security matcher spec'd; every Response DTO stated separate from the JPA entity (never the entity serialized directly); read-only vs. read-write `@Transactional` boundaries stated per service method; javax vs. jakarta namespace confirmed against the actual Spring Boot major version
- MODE E: Every FR traced in SRS traceability table; every DTO's class-validator rules spec'd (not left implicit); every endpoint's Guard/Roles spec'd; ORM (TypeORM vs Prisma) confirmed from `package.json` before drafting Section 2; global `ValidationPipe` assumption (`whitelist`/`forbidNonWhitelisted`) stated explicitly, since DTO validation is this stack's actual trust boundary
- MODE F: Every FR traced in SRS traceability table; every endpoint has an auth spec; every Pydantic response schema stated separate from the SQLAlchemy model (never the ORM model returned directly); async-vs-sync boundary stated for every route (which calls are genuinely non-blocking)
- MODE G: Every FR traced in SRS traceability table; every port trait's method signatures spec'd before the application-layer use case that consumes it; typed error enum spec'd per feature (no bare `anyhow`/`Box<dyn Error>` crossing the domain/application boundary); every `unwrap()`/`panic!` candidate in the design instead modeled as a typed `Result` variant
- MODE H: Every FR traced in SRS traceability table; every backend endpoint this feature calls is named with its request/response shape (never invented); every screen state (loading/empty/error/success) has a spec'd rendering; state-service subscription cleanup (`async` pipe/`takeUntilDestroyed()`) stated, not left to "Angular handles it"
- MODE I: Every FR traced in SRS traceability table; every backend endpoint this feature calls is named with its request/response shape; data-fetching hook's cache key, staleness, and invalidation trigger spec'd; server state vs. client state explicitly separated (never hand-rolled fetch-and-cache inside Context/Redux)
- MODE J: Every FR traced in SRS traceability table; ViewModel spec confirms no `Context`/`View`/`Activity`/`Fragment` reference; Repository stated as the single source of truth (ViewModel never calls Retrofit/Room directly); state flow direction (ViewModel → UI, events UI → ViewModel) spec'd per screen
- MODE K: Every FR traced in SRS traceability table; ViewModel/Repository split spec'd (ViewModel depends on a protocol, not a concrete networking type); no force-unwrap (`!`) in the design for a case that's actually a normal failure mode; MVVM-vs-Clean/VIPER choice justified against Axis 2 domain-complexity, not assumed
- MODE L: Every FR traced in SRS traceability table; domain layer confirmed to have no Flutter/dio imports; BLoC-vs-Riverpod choice justified per feature against domain-complexity, not a single app-wide default; widget `build()` methods confirmed to contain no business logic in the design
- MODE H/I/J/K/L: every interactive element has a spec'd accessible name/role, focus order is spec'd where it isn't the obvious visual default, color contrast target is stated as WCAG AA, and every dynamic state change has a spec'd assistive-tech announcement — or the whole pass is marked `[A11Y EXCEPTION — reason]` in Open Questions, never silently absent
- No numeric threshold without source → mark `[FORMULA NEEDED]`
- Every non-SRS-sourced technical statement is labeled `[DESIGN DECISION]` or `[ASSUMPTION]`
  (`references/decision-records.md` §1) — unlabeled, it reads as a requirement to the next reader
- Any change to an existing API/DB schema/event with consumers states compatibility mode and
  version/coexistence strategy (`references/distributed-systems-checklist.md` §36)
- Every published event states its envelope (`eventId`/`eventType`/`eventVersion`/
  `correlationId`/`causationId` — §35 of the same checklist)
- Every New component is justified against Architecture Context (step 3)

### 7. GATE — Implementation Readiness

Classify the SDS with the same three states `/spec` uses, so both gates read the same way:

- **READY**: no `[NEEDS SPEC CLARIFICATION]` items remain; every applicable `[MUST]` checklist
  item is satisfied or explicitly excepted with a reason.
- **PARTIALLY_READY**: some sections are blocked on `[NEEDS SPEC CLARIFICATION]`/`[PERF TARGET
  NEEDED]`/`[SECURITY EXCEPTION]`, but others don't depend on them — state what `/implement`
  can start on now.
- **BLOCKED**: a `[NEEDS SPEC CLARIFICATION]` sits on the primary flow, core data model, or a
  security/consistency-critical path — nothing goes to `/implement` yet.

State this as an "Implementation Readiness" section in the SDS, not just in chat.

### 8. FINALIZE — Save & handoff

- Report: columns/APIs/steps count, SRS coverage %, readiness status
- **Next step**: `Run /review <file> then /implement <module>` (scoped to whatever the
  readiness gate allows — say so explicitly if `PARTIALLY_READY`/`BLOCKED`)

## Rules

**Formula Integrity (anti-hallucination):**
```
✅ composite_score = trend * 0.40 + momentum * 0.30 + volume * 0.30  # SRS §3.2
❌ composite_score = trend * 0.40 + momentum * 0.35 + volume * 0.25  # (no source — invented)
```
If SRS doesn't specify formula/weight → mark `[FORMULA NEEDED — SRS §X.Y or user input]` → list in Open Questions.

**Prohibited:**
- ❌ Design without reading SRS (stop if SRS missing)
- ❌ Design past a `BLOCKED` SRS readiness gate, or past an SRS section the SRS itself marked
  not-ready
- ❌ Decide a business question the SRS left open (self-approval rules, limit tables, what
  "expired" means) instead of raising `[NEEDS SPEC CLARIFICATION]` — not a technical decision to
  make quietly
- ❌ Write production code in SDS (pseudo-code only)
- ❌ Invent numeric weights/thresholds without SRS source
- ❌ Propose a new service/module/table when an existing one owns that responsibility, without a
  stated reason (Architecture Context, step 3)
- ❌ Make a costly-to-reverse technical choice (messaging tech, concurrency mechanism, consistency
  model) without recording it as a `references/decision-records.md` § 2 decision with alternatives
- ❌ Change an existing API/schema/event with active consumers without stating backward
  compatibility (`references/distributed-systems-checklist.md` § 36)
- ❌ Publish an event with a bare payload and no envelope (`eventId`/`eventType`/`eventVersion`/
  correlation) — § 35 of the same checklist
- ❌ Mark an SDS `READY` while a `[NEEDS SPEC CLARIFICATION]` sits on the primary flow or a
  security/consistency-critical path
- ❌ MODE B: Domain entity importing MongoDB/Fiber/Redis packages
- ❌ MODE B: Expose password/secret fields in Response DTOs
- ❌ MODE B: Skip auth spec for any endpoint
- ❌ MODE C: Design a Server Component/page that queries Prisma directly with no shared data-access module boundary (`lib/*.ts`) — same repository discipline as MODE B, just colocated
- ❌ MODE C: Design a Server Action that throws for expected validation/business errors instead of returning a `{success, data|error}` result union (breaks "preserve form input on failure")
- ❌ MODE C: Design a shared Prisma model with no stated per-field ownership when more than one feature writes to it
- ❌ MODE C: Assume the Next.js/Prisma API shape from prior knowledge — verify against `node_modules/next/dist/docs/` and the installed Prisma major version's docs first (both have had breaking changes across majors: middleware→proxy rename, generator/datasource config location, mandatory driver adapters)
- ❌ MODE D: Domain/JPA entity importing Spring MVC (`@RestController`, `HttpServletRequest`) or service-layer packages
- ❌ MODE D: Return a JPA entity directly as an HTTP response instead of mapping to a Response DTO (leaks lazy-proxy fields, breaks serialization outside the persistence context)
- ❌ MODE D: Skip stating javax vs. jakarta namespace — Spring Boot 3 moved the whole tree; assuming the wrong one produces dead-on-arrival code
- ❌ MODE D: Skip auth spec (`@PreAuthorize`/security matcher) for any endpoint
- ❌ MODE E: Skip stating which ORM (TypeORM vs Prisma) the project uses before drafting Section 2 — check `package.json`/`prisma/` first, the entity shape differs completely
- ❌ MODE E: Put business logic (uniqueness checks, ownership checks, mutation) in the Controller instead of the Service
- ❌ MODE E: Return a raw entity/Prisma model from a controller instead of mapping through a Response DTO (`plainToInstance` + `ClassSerializerInterceptor`, or equivalent)
- ❌ MODE E: Design DTOs without specifying class-validator rules, assuming "Nest validates it" — the rules themselves are the spec, the pipe just enforces whatever was designed
- ❌ MODE F: Return a SQLAlchemy model directly from a router instead of mapping to a Pydantic response schema
- ❌ MODE F: Design a blocking call (sync DB driver, `requests`, a CPU-heavy loop) inside an `async def` route without flagging it — it stalls the whole event loop, not just that request
- ❌ MODE F: Skip stating the `Depends()` injection point for the repository/service, leaving tests unable to override it with a fake
- ❌ MODE G: Let a web-framework type (`axum::extract::State`, `actix_web::HttpRequest`) appear in a domain struct
- ❌ MODE G: Design with `.unwrap()`/`panic!` on a fallible operation that's a normal, expected case (missing row, malformed request) rather than a genuine bug
- ❌ MODE G: Use `anyhow`/`Box<dyn Error>` across the domain/application boundary instead of a typed error enum callers can match on
- ❌ MODE H: Design a component that calls the backend HTTP client directly instead of through a state/data service
- ❌ MODE H: Design manual `.subscribe()` without a stated unsubscribe path — the most common Angular memory leak
- ❌ MODE I: Hand-roll fetch-and-cache logic inside Context/Redux instead of naming a data-fetching library — conflating server state with client state
- ❌ MODE I: Design prop-drilling through more than 2–3 levels instead of composition or a scoped Context
- ❌ MODE J: Design a ViewModel holding an Android `Context`/`View`/`Activity`/`Fragment` reference
- ❌ MODE J: Design a ViewModel calling Retrofit/Room directly instead of through a Repository
- ❌ MODE K: Design a `UIViewController`/View containing networking calls and business rules directly, with no ViewModel
- ❌ MODE K: Use a singleton (`Manager.shared`) as an implicit global state bus instead of an injected dependency
- ❌ MODE L: Design business logic inside a widget's `build()` method
- ❌ MODE L: Design a widget calling `dio`/`http` directly instead of through a repository interface
- ❌ MODE H/I/J/K/L: Invent a backend endpoint's request/response shape instead of reading the actual backend SDS/API client — mark `[NEEDS BACKEND SDS]` if it doesn't exist yet
- ❌ MODE H/I/J/K/L: Design an interactive element with no accessible name/role, or a dynamic state change (error/loading/toast) with no assistive-tech announcement — visual-only feedback isn't a complete design for these modes
- ❌ Skip error handling design
- ❌ Design an authorization check that stops at "is authenticated" — every protected action needs Auth → Role → Permission → Resource ownership → Action, not just a login check (`references/security-checklist.md` §2)
- ❌ Skip rate-limit design for auth/OTP/password-reset/payment/search/upload endpoints
- ❌ Skip idempotency design for a state-changing financial/transfer operation, or skip naming the concurrency-control mechanism (optimistic/pessimistic lock, distributed lock, state machine) for a resource multiple requests can race on
- ❌ Skip audit-log design for LOGIN/CREATE/UPDATE/DELETE/APPROVE/REJECT/TRANSFER/CHANGE_PERMISSION/CHANGE_PASSWORD actions
- ❌ Design a client-facing error shape that could leak stack trace, SQL, file path, internal hostname, or framework version
- ❌ Leave CORS/CSRF posture implicit — state whether the feature is Bearer-token or cookie-based auth and design the corresponding protection
- ❌ Design a processing step with a query/call inside a loop (O(N) DB calls) instead of a batch-fetch + in-memory map
- ❌ Design a list/export endpoint with no pagination, no max page size, or unbounded response size
- ❌ Design a DB transaction that spans an external HTTP call, a blocking Kafka publish, a large computation, or a sleep/retry — keep transactions short, deterministic, and database-only
- ❌ Design an external call with no stated timeout, or a retry with no bound/backoff/jitter
- ❌ Design an unbounded connection pool or thread/goroutine concurrency for a potentially-unbounded workload
- ❌ Design a cache with no stated TTL/invalidation path, or a hot cache key with no stampede protection
- ❌ Skip the performance baseline (§0 of the performance checklist) for a performance-critical API — no RPS/latency target or workload assumption at all
- ❌ Design a service writing directly to another service's owned database/table — cross-service access goes through an API, event, or command
- ❌ Design a distributed transaction as shared-DB ACID across two services instead of Saga/Outbox/Idempotency/Compensation
- ❌ Design a business-critical async operation on a non-durable mechanism (bare `@Async`/`go func()`) instead of a durable queue or persisted job
- ❌ Design a Kafka consumer (or any at-least-once message consumer) without an idempotency mechanism
- ❌ Design a state/status field that a consumer can set directly, without going through a validated state-machine transition
- ❌ Design a flow where a timeout on an external call (Core Banking, payment gateway) is treated as business failure — the correct intermediate state is UNKNOWN, resolved via status inquiry or reconciliation
- ❌ Skip a reconciliation mechanism for a financial/critical distributed workflow
- ❌ Design a Saga step with no compensation, or a distributed lock with no lease timeout
- ❌ Design a business invariant ("amount > 0", "COMPLETED cannot revert to DRAFT") as prose only, with no DB constraint or app-level enforcement point named
- ❌ Design duplicate prevention as an app-level check-then-insert with no backing uniqueness constraint
- ❌ Design a delete operation with no stated behavior for rows that reference the deleted row (cascade/restrict/set-null left to ORM defaults)
- ❌ Design an audit-logged action that only says "log it" without stating the actor/before/after/correlation shape
- ❌ Represent a monetary amount as a floating-point type
- ❌ Add a `NOT NULL` column to a populated table/collection in a single migration step with no add → backfill → constrain sequence (`references/database-design.md` §4)
- ❌ Add a foreign key column with no supporting index, or add an index with no stated query in this SDS that uses it (`references/database-design.md` §2)
- ❌ Design an endpoint's success/error response in an ad hoc shape instead of the project's one response envelope, or leave its status codes unstated (`references/api-design.md` §2–3)
- ❌ Design a list endpoint whose filter/sort fields aren't also accounted for in the schema's indexing strategy (`references/api-design.md` §5, `references/database-design.md` §2)
- ❌ Design a liveness probe that checks downstream dependencies, or a readiness probe that always returns healthy
- ❌ Design a consumer/worker with no graceful-shutdown sequence for `SIGTERM`
- ❌ Hardcode an operator-tunable threshold (retry count, rate limit, feature threshold) as a compile-time constant when an operator would need to change it without a redeploy
- ❌ Invent an availability target, RTO, or RPO without an SRS source or explicit user input
- ❌ Design an approval/maker-checker workflow whose authorization check doesn't explicitly forbid the maker approving their own resource
- ❌ Spawn a per-request/per-message resource (goroutine, thread, connection, timer) with no stated bound
- ❌ Design Tier 3 machinery (Saga, circuit breaker, formal RTO/RPO, cross-service data ownership) for a feature whose Scale Tier classification (`.claude/skills/architecture/references/system-scale-checklist.md` §0) answered "no" to all 5 questions, without a stated reason
- ❌ Classify a feature as Tier 1 when a decision question clearly answers Tier 3 (external critical-system integration, multi-team independent deployment, a stated compliance requirement) — consequence severity outweighs current traffic for that call
- ❌ Skip stating a graduation trigger for a Tier 1/2 SDS — "we're small now" with no stated condition for revisiting it is how a system quietly outgrows its architecture unnoticed

**Required:**
- ✅ Classify the Scale Tier (`.claude/skills/architecture/references/system-scale-checklist.md` §0) before choosing an architecture pattern or walking the Security/Performance/Distributed/Data-Integrity/Operations-Readiness checklists at full depth
- ✅ State the Scale Tier, its one-line reason, and (for Tier 1/2) the graduation trigger near the top of the SDS
- ✅ Detect project mode before design
- ✅ Read SRS before design, and check its Implementation Readiness gate before designing past it
- ✅ Classify every touched component as Existing/Modified/New/External before designing it further
- ✅ Label every non-SRS-sourced technical statement `[DESIGN DECISION]` or `[ASSUMPTION]`
- ✅ Record alternatives for costly-to-reverse decisions per `references/decision-records.md` § 2
- ✅ Challenge each costly-to-reverse decision with its strongest counter-argument before GATE —
  record why it survives (or revise it if it doesn't)
- ✅ State the Implementation Readiness gate (READY/PARTIALLY_READY/BLOCKED) before handoff
- ✅ MODE A: Spec all output columns in Section 3
- ✅ MODE A: Spec config keys + defaults + enums file in Section 5
- ✅ MODE A: Use exact column names from upstream SDS (verify via Glob+Read)
- ✅ MODE B: Trace every FR in Section 11.3
- ✅ MODE B: `created_at`, `updated_at` on every MongoDB entity
- ✅ MODE C: Trace every FR in the SRS traceability section
- ✅ MODE C: Spec every DB-backed route's rendering mode (`force-dynamic` vs. cacheable) — Next.js prerenders any route with no dynamic segment and no other opt-in, silently freezing its data
- ✅ MODE C: Spec query-layer filtering for any read that must never leak unpublished/draft/soft-deleted rows (filter in the data-access function, not in the component)
- ✅ MODE C: Spec auth/session refresh in both places it's needed — route guard (proxy/middleware) AND every mutating Server Action — since either alone leaves a gap
- ✅ MODE D: Trace every FR in the SRS traceability section
- ✅ MODE D: `createdAt`, `updatedAt` on every JPA entity (via `@PrePersist`/`@PreUpdate` or JPA Auditing — state which)
- ✅ MODE D: Spec read-only vs. read-write `@Transactional` boundaries per service method
- ✅ MODE D: Spec a Response DTO separate from the entity for every endpoint that returns data
- ✅ MODE E: Trace every FR in the SRS traceability section
- ✅ MODE E: Confirm TypeORM vs Prisma before drafting the data model section
- ✅ MODE E: Spec class-validator rules per DTO field, and state the global `ValidationPipe` config this SDS assumes
- ✅ MODE E: Spec Guard/Roles per endpoint, not just "protected"
- ✅ MODE F: Trace every FR in the SRS traceability section
- ✅ MODE F: Spec a Pydantic response schema separate from the SQLAlchemy model for every endpoint that returns data
- ✅ MODE F: State the `Depends()` injection point for every repository/service used by a router
- ✅ MODE G: Trace every FR in the SRS traceability section
- ✅ MODE G: Spec a typed error enum for the feature, with each application-layer failure mode mapped to it
- ✅ MODE G: Confirm no domain/application-layer type imports `axum`/`actix-web`/`sqlx`/`diesel` directly
- ✅ MODE H: Trace every FR in the SRS traceability section
- ✅ MODE H: Name every backend endpoint this feature calls with its request/response shape (from the actual backend SDS, never invented)
- ✅ MODE H: Spec every screen state (loading/empty/error/success) and the subscription-cleanup mechanism for each state service
- ✅ MODE I: Trace every FR in the SRS traceability section
- ✅ MODE I: Name every backend endpoint this feature calls with its request/response shape
- ✅ MODE I: Spec the data-fetching hook's cache key, staleness, and invalidation trigger; separate server state from client state explicitly
- ✅ MODE J: Trace every FR in the SRS traceability section
- ✅ MODE J: Confirm the ViewModel spec holds no `Context`/`View`/`Activity`/`Fragment` reference
- ✅ MODE J: Spec the Repository as the single source of truth (ViewModel never calls Retrofit/Room directly)
- ✅ MODE K: Trace every FR in the SRS traceability section
- ✅ MODE K: Spec the ViewModel depending on a Repository/Service protocol, not a concrete networking type
- ✅ MODE K: State the MVVM-vs-Clean/VIPER choice with a one-line domain-complexity reason
- ✅ MODE L: Trace every FR in the SRS traceability section
- ✅ MODE L: Confirm the domain layer spec has no Flutter/dio imports
- ✅ MODE L: State the BLoC-vs-Riverpod/Provider choice per feature with a one-line domain-complexity reason
- ✅ MODE H/I/J/K/L: Spec accessible names/roles, focus order, WCAG AA contrast, and assistive-tech announcements for dynamic state — or mark `[A11Y EXCEPTION — reason]`
- ✅ For any feature exposing an endpoint/Server Action: resource naming, status codes, response envelope, and pagination/versioning are specified per `references/api-design.md`
- ✅ For any module introducing/modifying persistent schema: indexing strategy is derived from a stated query access pattern, and any schema change to a populated table states its add/backfill/constrain migration steps (`references/database-design.md`)
- ✅ Test plan covers happy path + errors + edge cases
- ✅ Threat-modeling questions answered before DESIGN (`references/security-checklist.md`)
- ✅ Test plan includes the mandatory security cases that apply: unauthenticated, unauthorized/IDOR, expired/invalid token, replay, rate-limit exceeded, oversized request, malformed payload, cross-tenant (if multi-tenant)
- ✅ Performance baseline captured before DESIGN (`references/performance-checklist.md` §0), or marked `[PERF TARGET NEEDED]`
- ✅ Every DB transaction boundary stated as short/deterministic/DB-only — no external call, blocking queue publish, or large computation inside it
- ✅ Every list endpoint states default + max page size; every external call states connect/read/overall timeout
- ✅ For a distributed/async feature: data ownership, consistency classification (strong vs. eventual), idempotency mechanism, state-machine transitions, and unknown-result handling are all stated in Section 10, or the feature is explicitly noted as N/A (single-service, synchronous, no external call)
- ✅ Test plan for a distributed/async feature includes the mandatory failure scenarios that apply: duplicate message, message lost, consumer/producer crash, external API timeout with response lost, retry exhaustion/DLQ, replay
- ✅ For a module owning persistent state: every stated business invariant names its enforcement point (DB constraint and/or app validation), every FK's delete/update behavior is stated, and any audit-logged action states the actor/before/after/correlation shape (`references/data-integrity-checklist.md`)
- ✅ For a module deployed as its own service/process: readiness/liveness are distinguished, a shutdown sequence is stated for any consumer/worker, and every new operator-tunable value is labeled Configuration (not a compile-time constant) (`references/operations-readiness-checklist.md`)

## Mistakes & Rationalizations — Go back to ANALYZE or DESIGN

| Mistake / tempting thought | Fix |
|---|---|
| Skipping the upstream SDS check, or assuming "column names are probably the same as module X" | Glob + Read the upstream SDS — never invent or assume column names |
| MODE A: designing implementation before the I/O schema | I/O schema first, processing second |
| MODE B: designing the API before the domain | Entity first, API last (inside-out) |
| Inventing weights/thresholds without an SRS source ("this weight seems reasonable") | Mark `[FORMULA NEEDED]`, add to open questions |
| Over-engineering config keys | Only add keys the SRS actually requires — YAGNI |
| Writing real code (Go, Python, etc.) in the SDS | Pseudo-code and algorithm specs only |
| Forgetting error handling, or "it's obvious, skip this section" | Every processing step states its error behavior explicitly |
| Assuming the project mode from a hunch ("probably MODE A since it's Python") | DETECT via CLAUDE.md/manifest files, don't assume |
| Trusting "I already read the SRS" instead of re-verifying | Trace every requirement back to its SRS section |
| MODE C: designing the page/route before the data model | Prisma model → data-access reads → Server Action writes → page, in that order |
| MODE C: a Server Action that throws on bad input | Design a result union (`{success, data|error, fieldErrors?}`) so the form can re-render with input intact |
| MODE C: no ownership note on a shared Prisma model | State per-field write-ownership when 2+ features touch the same model |
| MODE C: assuming `order`/position fields are contiguous | Design for gaps if rows can be hard-deleted — nearest neighbor, never `±1` |
| MODE C: "the Server Component can query Prisma directly, saves a layer," or assuming an older Next.js/Prisma API shape | Design the data-access boundary anyway (same discipline as MODE B's repository); verify current API shape against installed docs — both have had breaking major-version changes |
| MODE D: designing the Controller before the entity | JPA Entity → Repository → Service → Controller/DTO, in that order |
| MODE D: returning the entity straight from the controller, or assuming javax over jakarta (or vice versa) | Always map to a Response DTO; check `pom.xml`/`build.gradle` for the actual Spring Boot major version first |
| MODE E: guessing TypeORM when the project uses Prisma (or vice versa) | Check `package.json`/`prisma/` before drafting Section 2 — the shapes don't translate 1:1 |
| MODE E: business logic designed into the Controller | Keep the Controller a thin transport boundary — validation/uniqueness/ownership logic belongs in the Service |
| MODE E: leaving DTO validation "implicit" because Nest validates automatically | The validation rules are still a design decision — spec them per field |
| MODE F: designing the router before the repository/service, or returning the SQLAlchemy model straight from a route | SQLAlchemy model → Repository → Service → Pydantic schema → Router, in that order; always map to a response schema |
| MODE F: assuming a sync driver call inside `async def` is "probably fine" | Flag every blocking call explicitly — it stalls the whole event loop, not just its own request |
| MODE G: reaching for `anyhow`/`.unwrap()` because "it's just a prototype" | Typed error enum at the domain/application boundary; `.unwrap()` only for genuine bugs, never expected failure cases |
| MODE G: letting an axum/actix type slip into a domain struct "just this once" | Domain compiles without the web framework — keep the port trait as the only boundary |
| MODE H/I: designing the component before naming the backend endpoint it calls | Name the endpoint's request/response shape first (from the real backend SDS) — the component renders states derived from it, not the other way around |
| MODE H: manual `.subscribe()` with "I'll unsubscribe in `ngOnDestroy`" | Design with the `async` pipe or `takeUntilDestroyed()` instead — manual unsubscribe is the most common leak source to forget |
| MODE I: hand-rolling fetch+cache in Context "since we already have Context for other things" | Name a data-fetching library (React Query/SWR) for server state — Context is for client state only |
| MODE J: designing the ViewModel to hold an Activity/Fragment reference "for convenience" | Anything Android-framework-specific stays in the UI layer; the ViewModel takes an abstraction |
| MODE K: force-unwrapping in the design because "this will never be nil in practice" | Model the failure explicitly (optional handling, typed error) — "never in practice" is exactly where it eventually is |
| MODE L: putting a `dio` call in a widget's `build()` "just to get it working first" | Business/network logic goes in the repository/state-management layer from the first draft — widgets render and forward events only |
| MODE H/I/J/K/L: "accessibility can be a follow-up pass after the design is done" | Spec accessible names/roles and dynamic-state announcements alongside the component/widget layer — retrofitting it after screens are built means re-touching every one |
| Stopping authorization design at "user is logged in" | Design the full chain: Auth → Role → Permission → Resource ownership → Action (`references/security-checklist.md` §2) |
| Treating threat modeling (Section 7) as an afterthought, or "this feature's too small for it" | Answer the questions during ANALYZE, before endpoints are shaped — or explicitly mark N/A, never skip silently |
| Skipping rate limiting/idempotency because "MVP doesn't need it," or "it can be added later" | Financial/auth-adjacent endpoints need it designed even for MVP — retrofitting after an incident costs far more |
| Designing a query without stating its access pattern ("this runs rarely, don't worry about N+1") | State filter/sort columns so the index can be designed against them — "rare" doesn't survive the first workload growth |
| Letting an external call sit inside a DB transaction "because it's convenient" | Redesign as validate → prepare → short DB transaction → commit → external/async step |
| Treating pagination as an implementation detail to add later | Default + max page size is part of the contract from the first draft |
| Picking Kafka/Redis/a broker before answering the ownership/consistency questions | Answer `references/distributed-systems-checklist.md` §0 first — the technology falls out of the answers |
| Treating a timeout from an external system as FAILED, or "retry later" | Model it as UNKNOWN and design a status-inquiry/reconciliation path — the remote side may have already succeeded |
| Letting a consumer set a status field directly, or "the message is only processed once, no need for idempotency" | Design the state machine's allowed transitions explicitly; assume at-least-once delivery always |
| Trusting app-level validation alone for a uniqueness/amount invariant ("writing it in prose is enough") | Back it with a DB constraint (`UNIQUE`/`CHECK`) — app logic is one bypassed code path away from a corrupted row |
| Treating application logs as the audit trail | Design a dedicated audit entry (actor/before/after/correlation) — logs aren't what an auditor queries |
| Designing a readiness probe that always returns 200 | State the real dependency it checks — an always-healthy probe protects nobody |
| Hardcoding a retry count/threshold "because the default is fine" | If an operator would ever need to change it without a redeploy, it's Configuration, not a constant |
| Skipping the availability/RTO/RPO or performance-target section because the SRS/user is silent | Mark `[AVAILABILITY TARGET NEEDED]`/`[PERF TARGET NEEDED]` — don't let silence read as "not needed" |
| Reaching for microservices/Kafka/Saga "because that's how real systems are built," or "to be safe" for future scaling | Check the Scale Tier first — designing for a hypothetical scale that hasn't been signaled is over-engineering, not foresight |
| Treating a small user base as proof the system is Tier 1 forever, or "this feature is small, no need to check carefully" | A single "yes" on external-critical-system-integration or multi-team ownership means Tier 3 regardless of traffic — check all 5 questions |
| Leaving the Scale Tier unstated "because it's obvious from context" | State it anyway with a one-line reason |
| Querying another service's DB directly because "it only reads, doesn't write" | Route it through that service's API/event stream — a direct cross-service read is the same ownership violation as a write |
| Treating distributed transactions as "too complex" and using a shared DB transaction instead | That's the anti-pattern, not a shortcut — design Saga/Outbox/Idempotency/Compensation |
| Assuming a component "isn't enough" justifies a new one | Check Architecture Context first — extending what exists is usually cheaper, and a new component needs a stated reason |
| Not writing down the reason for an obvious-seeming technical choice (Kafka, a lock strategy) | Record it with alternatives anyway — if it's wrong, it's costly to reverse without that record |
| "This decision is obviously right, no need to argue against it" | Write the strongest counter-argument anyway before GATE — a decision that's never been challenged is unexamined, not confirmed |
| Assuming a schema/event/API change is additive and "won't break anyone" | Check actual consumers before claiming backward compatibility |
| Treating a `BLOCKED` gate as bypassable because "the part I need seems unrelated" | Verify carefully — the unrelated-looking part may depend on an unconfirmed invariant |

**PREREQUISITE:** `/spec` must complete first, and its readiness gate must not be `BLOCKED`.
**NEXT STEP:** `/review` then `/implement` (scoped to whatever the readiness gate allows).
