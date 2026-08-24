---
name: implement
description: >
  Use when writing code for a planned feature, bug fix, or module, after a plan/SDS/spec exists —
  "implement X", "viết code cho Y", "fix bug V". Do NOT use before a design exists. This is HOW to
  write the code, not WHAT to build.
---

## OVERVIEW

Turn a plan into working, tested, verified code. Three steps, no shortcuts.

**Prerequisites:** Plan/SDS/spec must exist — if not, stop and suggest creating one first.
Respect its Implementation Readiness gate if present (`/design`/`/spec` write
READY/PARTIALLY_READY/BLOCKED): `BLOCKED` → stop, say why; `PARTIALLY_READY` → implement only the
ready scope.
**Project conventions:** Constants locations, test patterns, tooling — check the project's CLAUDE.md before starting.

**Multi-task plans:** This skill defines how ONE task gets implemented, tested, and verified —
not how a multi-task plan gets executed end to end. If the plan has more than a couple of
largely independent tasks, running them all in one long pass degrades quality as context fills
and mistakes compound unreviewed. Use `superpowers:subagent-driven-development` (same session:
fresh subagent per task, task review after each, fix loop, final whole-branch review) or
`superpowers:executing-plans` (separate session with human checkpoints) to drive that loop. Either
way, the IMPLEMENT → TEST → VERIFY workflow and checklists below are what each task — whether you
run it directly or as a dispatched implementer subagent — actually follows.

<HARD-GATE>
Do NOT write implementation code until:
1. A plan/SDS/spec exists (what to build is decided) and its readiness gate, if any, isn't `BLOCKED` for the part you're implementing
2. You have read the target files you'll modify
3. You know where constants/config belong in this project (check CLAUDE.md)

Do NOT complete without:
4. All tests passing
5. Every changed file passes syntax check
6. No hardcoded magic numbers outside designated constants files
</HARD-GATE>

**Violating any gate = violating the spirit of the skill.** Each row below is both the
tempting thought and the red flag it produces — stop and fix rather than rationalize past it:

| Rationalization | Reality |
|----------------|---------|
| "I remember this file's pattern, I can skip reading it" | Memory drifts between sessions. Read the actual file before touching it. |
| "This is simple, I can skip the test" | Simple code breaks silently. A 30-second test catches it now or costs hours later. |
| "I'll add constants later, let me just get it working" | "Later" never comes. Move the number to enums now. |
| "The plan is clear enough in my head" | Unwritten assumptions = bugs. If it's not in the plan, clarify before coding. |
| "I'll run tests after I finish all the changes" | Batch testing = debugging blind. Test after each logical change. |
| "It's a small change, syntax check can wait" | Small changes break silently too. Run it now, not at the end. |
| "This file already has magic numbers, one more won't hurt" | Don't make existing debt worse. New code sets the standard. |
| "The blocked part is basically the same code, I'll just build all of it" | It wasn't designed because a business question is still open — implementing it means guessing that answer in code instead of in the SDS, the exact failure `/spec`/`/design` exist to prevent. |
| "I'll add a queue/circuit-breaker/lock now, it's more robust" | Undesigned scope creep dressed up as diligence — a Tier 1 feature doesn't need Tier 3 machinery, and adding it unasked implements an architecture decision nobody made. |
| "It's GREEN, I'm done" | GREEN means it works, not that it's left in a shape the next reader can follow. Re-read the diff for structural smells before moving on. |
| "The test just started failing, let me tweak it until it passes again" | That's guessing, not root-causing. State what changed and why before touching the test or the code. |

---

## WORKFLOW

```
IMPLEMENT → TEST → VERIFY
```

### Step 1: IMPLEMENT — Write minimal, correct code

**Before writing:** Read the files you'll modify. Know the existing patterns.

**While writing:**
- **Constants in the right place.** Every threshold/weight/multiplier goes in the project's designated constants/enums/config file (check CLAUDE.md for where) — never inline magic numbers.
- **Follow existing patterns.** Match the surrounding code's style, naming, and structure — don't introduce new patterns in old files.
- **Type hints** on all public functions. Docstrings on functions with non-obvious logic.
- **Handle edge cases** as you write — empty inputs, None, boundary values.
- **Fail fast.** Validate inputs at entry points. Raise specific errors, not generic Exception.
- **One concern per change.** Don't fix unrelated issues you notice. Note them, stay focused.
- **Match the SDS's stated Scale Tier — don't gold-plate or cut corners.** Building a message queue, circuit breaker, or distributed lock the SDS didn't ask for (Tier 1 per `.claude/skills/architecture/references/system-scale-checklist.md`) is scope creep, not diligence — real time spent solving a problem the system doesn't have. If the SDS is silent on tier, or the code shows a Tier 2/3 signal it missed (a new external critical-system call, a new cross-service data dependency), flag it — don't silently build either the heavyweight or the naive version.
- **Treat all external input as untrusted.** HTTP body/query/path/headers/cookies, JWT claims, uploaded files, MQ messages, webhooks — validate and normalize at the boundary even if a framework pipe/decorator partly does it. Implement the SDS's auth/authorization/rate-limit/idempotency design exactly — don't loosen it because "it's simpler." See `references/security-implementation-checklist.md` whenever the code touches auth, payments/state transitions, file uploads, or secrets.
- **Check complexity and resource bounds before writing a loop.** A query/repository call inside a loop is O(N) DB calls waiting to become a production incident — batch-fetch instead. Never load an unbounded dataset into memory (`findAll()`/`SELECT *` with no limit), never let a DB transaction span an external call, never call an external service with no timeout. See `references/performance-implementation-checklist.md` whenever the code has a loop over a query, a list/export endpoint, a DB transaction, an external call, a cache, or a queue consumer.
- **Treat distributed state as unreliable by construction.** A message can be delivered twice, a response can be lost while the remote side actually succeeded, and a process can crash mid-flow — code that assumes otherwise (fire-and-forget async, a non-idempotent consumer, a timeout treated as failure) is how duplicate transfers and stuck states happen in production. See `references/distributed-systems-implementation-checklist.md` whenever the code publishes/consumes a message, calls another service or an external system (Core Banking, payment gateway), or manages an entity with a status/lifecycle field.
- **Back every business invariant with a real constraint, not just app logic.** A uniqueness/amount/state-transition rule that only lives in application code is one bypassed code path away from a corrupted row. See `references/data-integrity-implementation-checklist.md` whenever the code writes to a table/collection this service owns — verify the migration actually has the `CHECK`/`UNIQUE`/`FK` the design named, that a `NOT NULL` column added to a populated table followed add → backfill → constrain rather than one step, never represent money as a float, and write audit entries with actual before/after state, not a bare message string.
- **Make every endpoint's contract shape match the rest of the system, not just this one feature.** A response envelope, status code, or pagination shape that's "close enough" for this endpoint is a client integration bug waiting to happen the day someone writes generic handling against it. See `references/api-implementation-checklist.md` whenever the code exposes an HTTP endpoint or Server Action — envelope consistency, 401/403/409/422 discipline, `Idempotency-Key` wiring on state-changing POSTs, and filter/sort allowlisting.
- **Wire up what makes the service operable, not just correct.** A correct service that can't signal "not ready yet," can't shut down without dropping in-flight work, or bakes an operator-tunable value into a compiled constant is still an incident waiting to happen. See `references/operations-readiness-implementation-checklist.md` whenever the code is a deployed service/worker/consumer — readiness vs. liveness, graceful shutdown, config externalization, and bounded per-request resource spawning.

**After each file:** Run syntax/type check immediately (adapt for project language — check CLAUDE.md):
```bash
python -m py_compile <file_path>   # Python / FastAPI
npx tsc --noEmit                   # TypeScript / Next.js / NestJS / Angular / React
go build ./...                     # Go / Fiber
mvn -q compile                     # Spring Boot (Maven) — or: ./gradlew compileJava
cargo check                        # Rust
./gradlew compileDebugKotlin       # Android (Kotlin) — or: ktlint check
xcodebuild -scheme <Scheme> build  # iOS (Swift)
flutter analyze                    # Flutter (Dart)
```

### Step 2: TEST — Prove it works

**Write tests that fail first, then make them pass (RED → GREEN):**

```bash
# 1. Write the test following the project's test conventions
# 2. Run to confirm it fails (RED)
<project_test_runner> <test_file>::<test_name>

# 3. Implement until it passes (GREEN)
<project_test_runner> <test_file>::<test_name>

# 4. Run full suite to catch regressions
<project_test_runner>
```

**What to test:**
- Happy path (expected input → expected output)
- Edge cases (empty, None, boundary values)
- Error conditions (invalid input raises proper error)

**This loop covers only the function you're touching right now.** Concurrency, a cross-service
call, an async/queue path, a security-critical flow, or a reviewer-flagged coverage gap needs
integration, contract, e2e, performance, or concurrency/failure tests — a step back from this
inline loop. Use `/test` for that; don't try to stretch this per-function loop to cover it.

**After GREEN, before moving on — simplify what you just wrote:** re-read the diff for the
structural smells that make code harder to follow than it needs to be (deep nesting, a boolean
flag parameter, a repeated conditional) and apply the matching cleanup — but only for code you
understand the purpose of (Chesterton's Fence: if you can't say why it's there, that's a question
to raise, not a green light to delete it) and only within the lines you just touched, not a
broader refactor of the surrounding file.

**If existing tests break:**
- Root-cause the failure before continuing — state what actually changed and why, don't
  guess-and-check by poking at the code until it passes; for anything non-obvious, apply
  systematic root-cause tracing (e.g. 5 Whys: keep asking why past the first symptom until you
  reach something actionable) rather than patching the first thing that looks related
- If behavior changed intentionally → update the test
- If regression → fix your code, don't modify the test

### Step 3: VERIFY — Quality gate before done

Run every check. Fix failures before claiming completion:

```bash
# 1. Syntax check all changed files (adapt for project language)
<python -m py_compile | npx tsc --noEmit | go build | mvn compile | cargo check | flutter analyze | xcodebuild build> <changed_files>

# 2. Full test suite
<pytest | npm test | go test ./... | mvn test | cargo test | flutter test | xcodebuild test> <project_test_runner>

# 3. Linter (if configured)
<project_linter> <changed_paths>

# 4. No magic numbers (project-specific regex/paths — not in the bundled script below)
grep -n '<number_pattern>' <source_dir>/*.<ext> | grep -v "constants\|config\|enums\|#"

# 5. Dependency vulnerability scan (pick per stack — see references/security-implementation-checklist.md §19)
pip-audit   # or: govulncheck ./...  |  mvn org.owasp:dependency-check-maven:check  |  npm audit  |  cargo audit

# 6. Grep sweep for secrets, sensitive-data logging, query-in-loop/N+1, unbounded
#    fetch-all, fire-and-forget async, direct status assignment, money-as-float,
#    and unbounded goroutine/thread spawn — a hit is a candidate to check by hand,
#    not an automatic verdict:
scripts/verify-checks.sh <changed_files_or_source_dir>
```

Full security/performance/distributed/data-integrity/API/ops-readiness passes are detailed in
the REFERENCE section below — run through whichever apply to what the change touches; the
commands above are the minimum baseline for every change.

Project test-runner reference by stack: `pytest` (Python, FastAPI), `npx vitest run` / `npm test`
(TypeScript, Next.js, NestJS, Angular, React unit), `npm run test:e2e` (NestJS e2e), `go test ./...`
(Go/Fiber), `mvn test` / `./gradlew test` (Spring Boot), `cargo test` (Rust), `./gradlew test`
(Android unit) / instrumented tests via `./gradlew connectedAndroidTest`, `xcodebuild test`
(iOS — XCTest), `flutter test` (Flutter — widget/unit) / `flutter drive` (Flutter integration).

**Self-review checklist** (read your own diff with fresh eyes, as if reviewing someone else's
code — memory of writing it hides the gaps a reader would catch):
- [ ] Every number I added is in an enum file, not hardcoded
- [ ] I read the files before modifying them
- [ ] My code matches existing patterns in those files
- [ ] I haven't added features not in the plan
- [ ] Edge cases are handled (empty, None, boundaries)
- [ ] All tests pass (not just mine)
- [ ] Every non-public endpoint/handler has an explicit, verified authorization check (role + resource ownership) — not assumed from the route name
- [ ] No password/token/OTP/secret/PII appears in a log statement or API response
- [ ] State-changing financial/approval operations have the design's idempotency/concurrency-control mechanism actually wired (not just present, unused)
- [ ] No query/repository call sits inside a loop — batch-fetched instead
- [ ] No DB transaction spans an external HTTP call, blocking queue publish, or large computation
- [ ] Every external call has an explicit timeout; every retry is bounded with backoff/jitter
- [ ] Any list/export endpoint has a max page size — no unbounded `findAll()`/`SELECT *` on a growable table
- [ ] Any Kafka/queue consumer checks for already-processed messages before applying an effect, marking processed in the same transaction as the business update
- [ ] Any status/lifecycle field is only ever changed through a validated transition — never a direct field assignment from a consumer
- [ ] Any timeout calling an external system (Core Banking, payment gateway) transitions to UNKNOWN, not directly to FAILED
- [ ] Every business invariant/uniqueness the design named has a real migration-level constraint (`CHECK`/`UNIQUE`/`FK`), not just app-level validation
- [ ] Any `NOT NULL` column added to a populated table splits into add → backfill → constrain migrations, with a tested rollback — not one single-step migration
- [ ] Every endpoint's response envelope, status codes, and pagination shape match the project's convention — not an ad hoc shape for just this endpoint
- [ ] No monetary amount is represented as `float`/`double`
- [ ] Any audit-logged action writes actor/before/after/correlation, not just a log message
- [ ] Readiness and liveness endpoints (if this is a deployed service) actually check different things — liveness never calls out to the DB
- [ ] Any consumer/worker traps `SIGTERM` and drains in-flight work with a bounded timeout before exiting
- [ ] Every value the design labeled Configuration is read from env/config service — not a hardcoded literal
- [ ] No goroutine/thread/task is spawned per request/message with no concurrency cap

**Reporting status:** whoever reads your result next — a human, a controller session running
`superpowers:subagent-driven-development`, or another agent that dispatched you as an
implementer — needs to know which of these four states you're in, not just a wall of narration:
- **DONE** — every HARD-GATE completion check and self-review box above is genuinely checked, not assumed.
- **DONE_WITH_CONCERNS** — complete, but say the specific doubt out loud (correctness you're not
  sure of, a file growing beyond the plan's intent). Concerns are for the next reader to weigh,
  not a reason to withhold the report.
- **BLOCKED** — you cannot finish: the task needs an architectural decision with more than one
  valid answer, or what you found in the code conflicts with the plan/spec. State exactly what's
  blocking you and what you already tried — don't just say "stuck."
- **NEEDS_CONTEXT** — you're missing information nobody gave you (an undocumented convention, an
  ambiguous acceptance criterion, a constant with no obvious home). Ask for it.

Guessing past a BLOCKED or NEEDS_CONTEXT moment instead of reporting it is how an undecided
business question gets silently answered in code — the same failure the "blocked scope"
rationalization above exists to catch.

---

## CONSTRAINTS

- ❌ Don't write code without a plan/spec — suggest creating one first
- ❌ Don't implement a section the plan/SDS/spec marked `BLOCKED`, or a part outside a `PARTIALLY_READY` scope — that's an undecided business question, not a coding task
- ❌ Don't implement features not in the plan — ask if something seems missing
- ❌ Don't hardcode constants in logic — use the module's enum file
- ❌ Don't skip syntax/type check after each file change (`python -m py_compile`, `npx tsc --noEmit`, `go build`, etc. — whichever fits the project)
- ❌ Don't claim completion with failing tests
- ❌ Don't trust client/external input as validated just because a framework pipe/annotation exists — verify it's actually applied on this endpoint, not just present somewhere in the codebase
- ❌ Don't skip the authorization/ownership check on an endpoint that returns or mutates another user's resource, even if it "looks read-only" — IDOR is the most common gap between looks-secure and is-secure
- ❌ Don't log or return a password, token, OTP, or secret — even in a debug/dev-only code path that could ship
- ❌ Don't put a repository/query call inside a loop — batch-fetch and build an in-memory map instead
- ❌ Don't let a DB transaction span an external HTTP call, a blocking queue publish, or a large computation — keep it short and database-only
- ❌ Don't call an external service with no timeout, or retry without a bound/backoff/jitter
- ❌ Don't implement a business-critical async operation as fire-and-forget (bare `@Async`/`go func()` with no durable backing) — use a durable queue or persisted job
- ❌ Don't write a message consumer without an idempotency check — assume every message can be delivered more than once
- ❌ Don't treat a timeout from an external call as business failure — transition to UNKNOWN and resolve via status inquiry or reconciliation, never a blind retry that could double-execute
- ❌ Don't rely on app-level validation alone for a uniqueness/amount/state invariant the design named — verify the migration actually has the matching DB constraint
- ❌ Don't add a `NOT NULL` column to a populated table in a single migration step — split into add (nullable) → backfill → constrain, and verify the rollback migration actually runs clean
- ❌ Don't return an ad hoc response shape, status code, or error format from one endpoint that doesn't match the project's envelope convention — a client shouldn't have to special-case any single endpoint
- ❌ Don't represent a monetary amount as a floating-point type
- ❌ Don't write an audit log entry as a bare message string when the design specified an actor/before/after/correlation shape
- ❌ Don't let a liveness probe depend on a downstream dependency, or a readiness probe that always returns healthy
- ❌ Don't hardcode a value the design labeled Configuration as a compile-time constant
- ❌ Don't spawn a goroutine/thread/task per request or per message with no concurrency cap
- ❌ Don't introduce a message broker, circuit breaker, distributed lock, or service split the SDS didn't design — even with good intentions, that's an undesigned architecture decision made in code
- ✅ If requirements are unclear → AskUserQuestion, don't guess
- ✅ If the plan has gaps → flag them before coding, don't fill silently
- ✅ Scope creep → note it, don't act on it

---

## REFERENCE

> **Verification details** (full commands, troubleshooting, language-specific tooling): Read `references/verification-checklist.md`
> **Next.js + Prisma specifics** (Server Action error contracts, cookie/session gotchas, draft-leak prevention, version-drift traps): Read `references/nextjs-prisma-checklist.md` when the target codebase is a Next.js + Prisma project
> **Spring Boot specifics** (entity-vs-DTO leaks, `@Transactional` boundaries, javax/jakarta version drift, N+1 traps): Read `references/spring-boot-checklist.md` when the target codebase is a Spring Boot (Java) project
> **NestJS specifics** (`ValidationPipe`/DTO trust boundary, `ClassSerializerInterceptor`, Guard wiring, TypeORM vs Prisma): Read `references/nestjs-checklist.md` when the target codebase is a NestJS (TypeScript) project
> **FastAPI specifics** (async/blocking-call traps, `Depends()` injection, Pydantic-vs-ORM-model leaks, background tasks): Read `references/fastapi-checklist.md` when the target codebase is a FastAPI (Python) project
> **Rust specifics** (`unwrap()`/`panic!` discipline, typed errors at the domain boundary, trait-object/adapter wiring, async runtime pitfalls): Read `references/rust-checklist.md` when the target codebase is a Rust (Axum/Actix) project
> **Angular specifics** (subscription leaks, `OnPush`/change detection, `core`/`shared`/`features` boundary, standalone component wiring): Read `references/angular-checklist.md` when the target codebase is an Angular project
> **React specifics** (server-state vs. client-state conflation, effect dependency arrays, memoization misuse, prop-drilling): Read `references/react-checklist.md` when the target codebase is a React SPA project
> **Android specifics** (ViewModel holding a `Context`/`View` reference, Compose recomposition traps, coroutine/lifecycle scoping, Room/Retrofit wiring): Read `references/android-checklist.md` when the target codebase is an Android (Kotlin) project
> **iOS specifics** (retain cycles/`weak self`, main-thread UI updates, Core Data/SwiftData concurrency, force-unwrap discipline): Read `references/ios-checklist.md` when the target codebase is an iOS (Swift) project
> **Flutter specifics** (`setState` misuse, widget rebuild scope, BLoC/Riverpod wiring, platform-channel error handling): Read `references/flutter-checklist.md` when the target codebase is a Flutter project
> **Security implementation checklist** (auth/authorization, injection, SSRF, file upload, secrets, business security, logging, mandatory security test cases — stack-agnostic, covers Go/Fiber too since it has no dedicated checklist file): Read `references/security-implementation-checklist.md` whenever the code touches auth, payments/state transitions, file handling, secrets, or external calls
> **Performance implementation checklist** (N+1, transaction scope, timeouts/retry, connection pools/concurrency bounds, cache stampede, memory/streaming, anti-pattern grep sweep — stack-agnostic, covers Go/Fiber too): Read `references/performance-implementation-checklist.md` whenever the code has a loop over a query, a list/export endpoint, a DB transaction, an external call, a cache, or a queue consumer
> **Distributed systems & async implementation checklist** (idempotent consumers, transactional outbox, state-machine transitions, unknown-result handling, reconciliation, DLQ wiring, mandatory failure-scenario tests — stack-agnostic, covers Go/Fiber too): Read `references/distributed-systems-implementation-checklist.md` whenever the code publishes/consumes a message, calls another service or an external system (Core Banking, payment gateway), or manages an entity with a status/lifecycle field
> **Data integrity implementation checklist** (DB constraints actually migrated, duplicate prevention via real constraints not check-then-insert, multi-table write atomicity, optimistic-lock wiring, money never as float, audit-entry shape, migration safety — add/backfill/constrain and tested rollback — stack-agnostic): Read `references/data-integrity-implementation-checklist.md` whenever the code writes to a table/collection this service owns, or the change includes a schema migration
> **API implementation checklist** (response envelope consistency, status-code discipline, `Idempotency-Key` wiring, pagination contract, filter/sort allowlisting, versioning enforcement, mandatory API test cases — stack-agnostic): Read `references/api-implementation-checklist.md` whenever the code exposes an HTTP endpoint or Server Action
> **Operations readiness implementation checklist** (readiness vs. liveness, graceful shutdown wiring, structured logging fields, config externalization, bounded per-request resource spawning — stack-agnostic): Read `references/operations-readiness-implementation-checklist.md` whenever the code is a deployed service, worker, or consumer
> **System scale & architecture fit** (Tier 1 MVP / Tier 2 async-growing / Tier 3 enterprise-distributed, and which checklists above apply at what depth): Read `.claude/skills/architecture/references/system-scale-checklist.md` if the SDS doesn't state a tier, or if the code you're touching has a signal (external critical-system call, new cross-service data dependency, a workflow that needs to run outside the request cycle) the SDS's stated tier doesn't seem to account for

**Project-specific context** (enum files, test patterns, module structure) belongs in the project's **CLAUDE.md**, not here. This skill is project-agnostic — read CLAUDE.md before implementing to find:
- Where constants/enums/config live
- Test file naming conventions
- Module/source directory structure
- Linter/formatter configuration
- Language-specific tooling commands
