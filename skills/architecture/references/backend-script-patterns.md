# Scripts & Backend Architecture Patterns

Stack-specific application of the axes decided in `architecture-selection.md`. Detect the stack
from `Cargo.toml` (Rust), `pyproject.toml`/`requirements.txt` with `fastapi` (FastAPI), `go.mod`
with `gofiber/fiber` (Go/Fiber), `pom.xml`/`build.gradle` with `spring-boot-starter` (Spring Boot
Java), `package.json` with `next` + `prisma`/`@prisma/client` (Next.js + Prisma full-stack),
`package.json` with `@nestjs/core` (NestJS), or the absence of any long-running server entry point
(script/CLI) before assuming.

**Extraction mechanics, once for every stack below** (each stack's section states only what's
stack-specific): a layer with zero dependency on sibling modules — domain/application in Rust,
`domain`/`usecase` in Go, the equivalent in FastAPI/Spring Boot — moves to the new service's own
codebase unchanged, because the module boundary already enforced that isolation. What changes is
the layer that called a sibling module in-process: it becomes a client (HTTP/gRPC/REST/Feign)
implementing the same port/interface the domain layer already depended on, so nothing on the
calling side's contract changes, only which concrete type is wired in. `modular-monolith.md` §5a's
per-module build entrypoint and migration namespace are the prerequisite that makes this a lift
instead of an untangling project — each stack note below says what's specific to that prerequisite
for its own layout.

## 1. Scripts & CLI Tools

A single-process script is, by construction, always Tier 1 topology (there's no service boundary
to draw) — the architecture question here isn't monolith-vs-microservices, it's internal
organization and operational safety for something that runs unattended (cron, a scheduler,
CI):

- **Separate I/O from pure logic.** Argument parsing, file/network reads and writes, and
  environment access belong in a thin outer layer; the actual transform/calculation is a pure
  function of its inputs. This is what makes the logic testable without mocking the filesystem or
  network for every test.
- **Idempotency, if the script can be re-run or retried** (a scheduled job, a CI step, a webhook
  handler invoked as a script) — re-running it with the same input should not double-apply an
  effect. This is `system-scale-checklist.md` §2's "Idempotent" requirement, applying even at
  single-script scale whenever retries are possible.
- **Config via environment variables/CLI flags with defaults**, never hardcoded paths/credentials
  — a script that only runs correctly on its author's machine isn't operationally safe.
- **Structured exit codes and logging** — `exit 0` only on genuine success, a distinct non-zero
  code (or at least a non-zero exit) on failure, and log output a human (or a monitoring system
  watching cron output) can actually use to tell what happened without reading the source.
- **One clear entry point (`main()`) composing named functions** — a single top-to-bottom script
  with no function boundaries is the script equivalent of a monolith with no module boundaries: it
  works until it needs to change, then every change risks breaking an unrelated part.
- **Recognize the inflection point**: once a script accumulates multiple stages with defined
  input/output schemas between them (a real data pipeline), that's `design` skill's MODE A
  territory — this file's job is spotting that the script has outgrown "script" and pointing
  there, not designing the pipeline itself.

**Anti-patterns**: side effects (writes, network calls) buried inside a function that's supposed to
be a pure calculation, making it untestable without live I/O; secrets hardcoded in source instead
of read from environment/a secrets manager; a script that always exits 0 regardless of what
happened, making failures invisible to whatever's scheduling it.

## 2. Rust Backend Services

**Recommended: Hexagonal / Ports-and-Adapters (Clean Architecture)** — Rust's trait system maps
directly onto "define a port as a trait, provide adapters as implementations," making this the
natural fit rather than an import from another language's convention:

```text
domain/         — plain structs/enums, business rules, and port traits (e.g. `trait OrderRepo`).
                  No dependency on tokio/axum/sqlx — this layer compiles without a web framework.
application/    — use cases: functions/structs taking `&dyn OrderRepo` (or a generic bound) and
                  orchestrating domain logic. Depends on domain + port traits only.
infrastructure/ — adapters: axum/actix-web handlers, sqlx/diesel implementations of the port
                  traits, external HTTP clients. Depends on domain + application, never the reverse.
```

- **Workspace-per-bounded-context** (a Cargo workspace with one crate per module) once
  `modular-monolith.md`'s boundary enforcement needs to be stronger than folder convention — a
  crate boundary is compiler-enforced, so another crate genuinely cannot reach into your internals
  without an explicit `pub` export, which is a stronger guarantee than most languages' module
  systems give for free.
- **Typed domain errors** (an `enum` per failure mode) rather than `anyhow`/`Box<dyn Error>`
  throughout domain/application code — callers need to pattern-match on *which* failure happened to
  react correctly (retry vs. 400 vs. 404); a type-erased error loses that at the call site. Convert
  to `anyhow`/a generic error only at the outermost boundary (the binary's `main`, or the HTTP
  adapter mapping to a status code) where no further caller needs to distinguish cases.
- **No `unwrap()`/`panic!` in library/domain/application code** — acceptable only in `main()` at
  startup (e.g. failing fast on invalid config) or in tests.

**Anti-patterns**: web-framework types (`axum::extract::State`, `actix_web::HttpRequest`) appearing
in domain structs, coupling business logic to a specific framework's request lifecycle; a single
crate with no boundary enforcement even though the codebase has clear bounded contexts that would
benefit from a workspace split; `.unwrap()` on a fallible operation whose failure is a normal,
expected case (a missing DB row, a malformed request) rather than a genuine bug.

**Extraction mechanics**: `domain/` and `application/` move verbatim into the new service's crate.
`infrastructure/` is what changes — an adapter that called another crate's `application` layer
in-process becomes an HTTP/gRPC client implementing the same port trait. Needs its own
`Cargo.toml`/binary entrypoint and migration directory (§5a.1/§5a.3) if not already split that way.

## 3. Python FastAPI Backend Services

**Recommended: layered architecture, feature-organized**:

```text
app/features/orders/
├── router.py       # HTTP concern only: parse request → call service → map response.
│                   #   No business logic here.
├── service.py      # business logic, use-case orchestration. Depends on repository via
│                   #   FastAPI's Depends() for testability (swap in a fake in tests).
├── repository.py   # DB access (SQLAlchemy/async equivalent). The only place queries live.
└── schemas.py      # Pydantic request/response models — separate from the ORM model.
```

- **Never return an ORM model directly from a route.** A Pydantic response schema that happens to
  mirror the ORM model today will diverge from it eventually, and returning the ORM model directly
  leaks internal fields (password hashes, foreign keys the client shouldn't see) and couples the
  public API contract to the DB schema — the same rule `design` skill's MODE D (Spring Boot) states
  for JPA entities, applying here to SQLAlchemy models.
- **Async all the way down** when using an async DB driver (`asyncpg`, async SQLAlchemy) — a
  blocking call (a sync DB driver, `requests` instead of `httpx`, a CPU-heavy loop) inside an
  `async def` route handler blocks the whole event loop, stalling every other concurrent request,
  not just the one that made the blocking call.
- **`Depends()` for dependency injection** — inject the repository/service into the router rather
  than importing and instantiating it directly, so tests can override the dependency with a fake.
- **Feature-organized, not `app/routers/` + `app/services/` + `app/models/`** each containing every
  feature's files — same package-by-layer anti-pattern `modular-monolith.md` §4 calls out, and it
  produces the same result: one feature's change touches three unrelated top-level directories.

**Anti-patterns**: business logic (validation beyond shape, uniqueness/ownership checks, orchestration) written directly in the router function instead of the service; a Pydantic response model that's just the SQLAlchemy model's fields copied over (leaks internal fields, couples contract to schema); a synchronous blocking library call inside an `async def` handler; a repository function that returns a query result the caller must know how to interpret, instead of a domain-shaped return value.

**Extraction mechanics**: `app/features/{module}/` becomes the new service's entire `app/` —
`router.py`/`service.py`/`schemas.py` keep their shape. A plain-Python import into another
feature's `service.py` becomes an `httpx` call needing `microservices.md` §2's timeout/retry
handling. `repository.py`'s models move to their own DB/connection string — which is why the
per-module schema namespace (§5a.3) has to already exist, or splitting `orders.*` from
`inventory.*` tables becomes the hard part of the extraction.

## 4. Go / Fiber Backend Services

Detect via `go.mod` requiring `github.com/gofiber/fiber`.

**Recommended: Clean Architecture / Ports-and-Adapters**, layered domain → usecase → adapter →
infrastructure. This is deliberately the same shape `design` skill's MODE B assumes when it writes
an SDS for this stack — keeping the two skills aligned means an SDS and the architecture docs never
disagree about where a new use case or repository is supposed to live:

```text
internal/
├── domain/{module}/entity/         — pure Go structs. `bson`/`json` tags are fine for simplicity,
│                                      but no Fiber types and no repository/DB calls in this package.
├── domain/{module}/repository/     — repository interfaces (ports)
├── domain/{module}/service/        — service interfaces (ports), when a module composes external services
├── domain/{module}/errors.go       — sentinel/typed domain errors, not raw fmt.Errorf strings
├── usecase/{module}/               — one struct + `Execute(ctx, input, meta)` per use case; the
│                                      only place that orchestrates domain logic
├── adapter/http/{module}/          — Fiber handlers, request/response DTOs, route registration —
│                                      HTTP concern only, no business logic
└── infrastructure/{mongodb,redis,service}/{module}/ — port implementations (DB drivers, external clients)
```

- **Import direction is enforced by convention, not the compiler** — unlike the Rust-workspace case
  above, Go's `internal/` only gates access from *outside* the module, not between the sub-packages
  within it. `domain` must not import Fiber or anything under `infrastructure/`; `usecase` depends
  on domain interfaces only, never a concrete infra type; `adapter` and `infrastructure` both depend
  inward on domain+usecase, never on each other. A reviewer has to actually check imports for this —
  nothing fails to compile if it's violated.
- **Domain errors are sentinel/typed values, mapped to HTTP status in one place** (the adapter
  layer's single error-mapping function), not scattered `c.Status(...)` calls copied into every
  handler — keeps every status-code decision auditable in one function.
- **DTOs are distinct types from domain entities**, mapped explicitly (a `ToEntityResponse`
  function) — never return the entity struct straight from a Fiber handler. Same client-facing-
  contract principle as FastAPI's Pydantic-vs-ORM-model rule above and Spring Boot's DTO rule below;
  it isn't Go-specific, it's a rule about not coupling a public response shape to an internal one.
- **One `Execute` method per use case struct** — this is what keeps the usecase layer testable with
  a fake repository, and keeps orchestration logic out of the Fiber handler.
- **A MongoDB/Postgres transaction spanning multiple documents/rows states its isolation/locking
  approach explicitly** in the design output — the same distributed-data-integrity expectation
  applies regardless of stack; flag it against `references/system-scale-checklist.md` if it signals
  the module has outgrown Tier 1.

**Anti-patterns**: a `*fiber.Ctx` or a raw `bson.M` appearing inside a `domain/` struct (framework
or DB details leaking into business logic); a handler calling the Mongo/Postgres driver directly
instead of going through usecase → repository; business validation (uniqueness, ownership,
state-transition rules) living in the handler instead of the usecase; one flat `internal/` package
with no per-module boundary once the codebase has more than a couple of distinct domains — the same
package-by-layer problem `modular-monolith.md` §4 calls out, just Go-flavored (`internal/handlers/`,
`internal/models/`, `internal/repositories/`, each containing every module's files together).

**Extraction mechanics**: `domain/{module}/`, `usecase/{module}/`, and `adapter/http/{module}/` move
to the new service's `internal/` unchanged. `infrastructure/` is what changes — a usecase that
called another module's usecase in-process now calls an HTTP/gRPC client implementing the same
port interface, with only the implementation wired at `main.go` differing. Needs a per-module
`cmd/{module}/main.go` (§5a.1) already in place, or untangling a shared `cmd/server/main.go` is
the first step before the split can even start.

## 5. Spring Boot (Java) Backend Services

Detect via `pom.xml`/`build.gradle` requiring `spring-boot-starter-web` (or `-webflux` for
reactive). **Check the Spring Boot major version before writing anything** — 3.x requires Java 17+
and the `jakarta.*` namespace instead of `javax.*` (`jakarta.persistence.Entity`,
`jakarta.validation`), and moved security config from `WebSecurityConfigurerAdapter` to a
`SecurityFilterChain` `@Bean`. Getting this wrong from training-data memory is the single most
common source of dead-on-arrival generated code for this stack — the same warning `design` skill's
MODE D states before drafting Spring code.

**Recommended: layered architecture** (controller → service → repository → domain), organized per
module/feature under one base package — matching `design` skill's MODE D package layout so an SDS
and the actual codebase agree on where a new endpoint or entity belongs:

```text
src/main/java/{basePackage}/{module}/
├── domain/{Entity}.java                  — JPA entity: persistence + minimal invariants only
├── repository/{Entity}Repository.java    — Spring Data JPA interface
├── service/{Entity}Service.java          — service interface
├── service/impl/{Entity}ServiceImpl.java — @Service, @Transactional boundaries
├── controller/{Entity}Controller.java    — @RestController — HTTP concern only
├── dto/{Entity}Request.java, {Entity}Response.java — request/response records, never the entity
├── mapper/{Entity}Mapper.java            — Entity <-> DTO (MapStruct or static methods)
└── exception/{Entity}NotFoundException.java
```

- **Import direction**: `domain` depends on JPA annotations/stdlib only; `repository` depends on
  Spring Data JPA + domain; `service` depends on repository + domain + DTO (mapping happens at this
  boundary); `controller` depends on service + DTO + mapper, never the repository directly. A
  controller injecting a `Repository` bean and skipping the service layer is the most common
  violation to check for during review.
- **Never return a JPA entity from a controller.** Lazy-loaded associations serialize
  unpredictably — or throw `LazyInitializationException` once outside the persistence context — and
  any field added to the entity later leaks to clients automatically. Map to a DTO at the service
  boundary, always. Same rule as FastAPI's ORM-model warning and Go/Fiber's DTO rule above.
- **`@Transactional` boundary lives in the service layer, not the controller or repository.** State
  per-service whether it's class-level `@Transactional(readOnly = true)` with a per-method override
  for writes, and confirm no `@Transactional` method makes a blocking external HTTP/Kafka call
  inside its boundary — that holds a DB connection open across a network round-trip, the same
  failure mode the Go/Fiber Mongo-transaction note above describes for a different stack.
- **N+1 prevention is an architectural review item, not just a performance afterthought.** Any
  repository method backing a list endpoint that also renders a `@ManyToOne`/`@OneToMany` relation
  needs `@EntityGraph` or `JOIN FETCH` named explicitly in the design — its absence means silently
  issuing N extra queries, which is a correctness-adjacent design gap worth catching at architecture
  review, not something to defer to a later performance pass.
- **Package-by-feature under one base package**, not package-by-layer at the top level
  (`com.acme.controller/`, `com.acme.service/`, `com.acme.repository/`, each containing every
  module's classes) — the same anti-pattern `modular-monolith.md` §4 flags for any stack, just
  visible here as Spring's default tutorial layout rather than a deliberate choice.

**Anti-patterns**: business logic (validation beyond `@Valid` shape-checking, ownership/state-
transition rules, cross-repository orchestration) written directly in the `@RestController` method
instead of the service; a `@Transactional` service method that also performs a blocking external
call or `Thread.sleep`/retry inside its transaction boundary; a DTO whose fields are the entity's
fields copied verbatim with no divergence, which signals the mapping step exists in name only; an
`@Entity` class calling out to other services or holding business rules that belong in `service/`.

**Extraction mechanics**: `{module}/domain`, `repository`, `service`, `controller`, `dto`, and
`mapper` move to the new service's own base package unchanged — package-per-feature already
isolated them. A `ServiceImpl` calling another module's `Service` bean via Spring DI becomes a
REST/Feign client implementing the same interface. Watch `@Transactional`: a transaction spanning
two modules' repositories in one JVM call has to become a Saga (`event-driven-architecture.md` §4)
*before* the split, not discovered as a bug after. A Gradle/Maven multi-module build (§5a.4) is
what makes each module's dependency list already accurate on day one, instead of reverse-engineered
from one shared root build file.

## 6. Next.js + Prisma Full-Stack

Detect via `package.json` requiring `next` + `prisma`/`@prisma/client`. Unlike the other stacks in
this file, frontend and backend are colocated in one deployable — App Router route/page files are
the transport layer, Server Actions are the mutation layer, and there's no separate service process
to stand up before the layering discipline applies. **Check the installed Next.js and Prisma major
versions before writing anything** — both have had breaking API-shape changes across majors
(middleware/proxy rename, generator/datasource config location, mandatory driver adapters); verify
against `node_modules/next/dist/docs/` and the installed Prisma docs rather than training-data
memory, the same warning `design` skill's MODE C states before drafting Next.js code.

**Recommended: inside-out layering, same discipline as the REST-API stacks above, adapted to
colocated frontend/backend** — this is deliberately the same shape `design` skill's MODE C assumes:

```text
prisma/schema.prisma       — the data model. Read existing models before adding fields; never
                              invent field names/types on a model another feature owns.
lib/{feature}/             — data-access layer: read functions wrapping Prisma queries. The only
                              place `prisma.<model>.findMany/...` calls for this feature live.
app/{feature}/actions.ts   — Server Actions: mutation layer, calling lib/{feature} + Prisma writes.
                              Returns a result union (`{success, data|error, fieldErrors?}`), never
                              throws for an expected validation/business-rule failure.
app/{feature}/page.tsx     — Server/Client Component split: Server Component fetches via
                              lib/{feature}, Client Component handles interactivity only.
```

- **A Server Component must not query Prisma directly** — same repository-boundary discipline as
  MODE B's Go repository layer or FastAPI's `repository.py`, just colocated in the same app instead
  of a separate service. Skipping the `lib/*.ts` layer "to save an indirection" is the most common
  way this stack's module boundaries erode.
- **Every DB-backed route's rendering mode is a stated decision** (`force-dynamic` vs. a
  revalidation interval), not left to Next.js's default — Next.js prerenders any route with no
  dynamic segment and no other opt-in, which silently freezes that route's data at build time.
- **A shared Prisma model states per-field write-ownership** when more than one feature writes to
  it — the same shared-model ownership rule any multi-writer schema needs, stated explicitly here
  because Prisma's single `schema.prisma` makes it easy to add a field without checking who else
  reads/writes the model.
- **Auth/session checks live in both places they're needed**: the route guard (middleware/proxy)
  for page access, and inside every mutating Server Action independently — a Server Action is a
  callable HTTP endpoint in its own right and isn't covered by route-level middleware alone.

**Anti-patterns**: a page or Server Component calling `prisma.<model>` directly instead of through
`lib/{feature}`; a Server Action that `throw`s on an expected validation/business error instead of
returning a result union (breaks the form's ability to re-render with the user's input intact); a
shared Prisma model with no stated field ownership once a second feature starts writing to it; a
route rendering DB-backed content with no stated rendering-mode decision.

**Extraction mechanics**: `lib/{feature}/` and `app/{feature}/actions.ts` move to the new service's
own data-access and mutation layers unchanged if the feature's Prisma models are already isolated
in the shared schema. A Server Action or Server Component that called another feature's
`lib/*.ts` function in-process becomes an HTTP call to the extracted service. The hard part is
almost always the schema, not the code: extracting a feature whose Prisma models are entangled
with another feature's (shared foreign keys, no per-feature ownership) means splitting
`schema.prisma` and the underlying tables first — do that split (or at least name the target
boundary) before treating the extraction as a simple lift.

## 7. NestJS Backend Services

Detect via `package.json` requiring `@nestjs/core`. **Confirm the ORM before drafting anything** —
`@nestjs/typeorm` (TypeORM entities) and `@prisma/client` (Prisma schema, `PrismaService` injected)
produce completely different data-access shapes; check `package.json`/`prisma/` rather than
assuming, the same warning `design` skill's MODE E states before drafting Section 2 of an SDS.

**Recommended: Nest's module system as the modular-monolith boundary**, one Nest module per
bounded context — this is deliberately the same shape `design` skill's MODE E assumes:

```text
src/{module}/
├── entities/{entity}.entity.ts   — TypeORM entity, or the Prisma model (schema.prisma) if Prisma
├── dto/{entity}-request.dto.ts, {entity}-response.dto.ts   — class-validator rules live on the
│                                    request DTO; the response DTO is mapped to, never the entity
├── {module}.service.ts           — business logic; injects the repository (TypeORM) or
│                                    `PrismaService` (Prisma) — never called from the controller
├── {module}.controller.ts        — thin transport boundary: `@Controller`, Guards/Roles per
│                                    endpoint, delegates to the service — no business logic here
└── {module}.module.ts            — wires controller + service + repository/Prisma provider;
                                     exports only what other modules are allowed to depend on
```

- **Import direction**: `entities`/schema depend on the ORM only; `service` depends on the
  repository/`PrismaService` + entities/DTOs (mapping to the response DTO happens at this
  boundary); `controller` depends on the service + DTOs, never the repository or `PrismaService`
  directly. A controller injecting a repository and skipping the service is the violation to check
  for first during review — same failure mode as Spring Boot's controller-bypasses-service anti-
  pattern above, Nest-flavored.
- **Never return a raw entity or Prisma model from a controller.** Map through the response DTO
  (`plainToInstance` + `ClassSerializerInterceptor`, or an explicit mapper function) — same
  client-facing-contract rule as every other stack's ORM-model warning in this file.
- **DTO validation rules are the actual design decision, not an implementation detail** — a DTO
  with no stated `class-validator` rules per field means the validation logic doesn't exist yet, it
  isn't just "left to Nest." State the global `ValidationPipe` config (`whitelist`,
  `forbidNonWhitelisted`) explicitly too, since that's this stack's actual trust boundary between
  what a client sends and what the DTO accepts.
- **Guards/Roles are stated per endpoint**, not as a blanket "this module is protected" — an
  endpoint with no stated Guard is a design gap, not an implicit inheritance from its module.
- **Module `exports` array is the enforced public interface** — another module importing this
  module's provider that *isn't* in its `exports` array fails at Nest's DI-resolution step, which
  makes Nest one of the few stacks here where the framework itself enforces the module boundary
  rather than relying on review discipline (contrast Go's `internal/` convention-only enforcement
  above).

**Anti-patterns**: business logic (uniqueness/ownership checks, cross-repository orchestration)
written directly in the `@Controller` method instead of the service; a DTO whose fields mirror the
entity/Prisma model with no `class-validator` decorators, signalling validation was never actually
designed; a module importing another module's internal provider that isn't in its `exports` array
worked around with a wildcard/global module instead of an explicit export; guessing TypeORM when
the project uses Prisma (or vice versa) instead of checking first.

**Extraction mechanics**: `{module}/entities`, `dto`, `service`, `controller`, and `{module}.module.ts`
move to the new service unchanged — Nest's module boundary already isolated them, and its
DI-enforced `exports` array means there's no untracked internal coupling to untangle first. A
service injecting another module's service via Nest DI becomes an HTTP/gRPC client implementing
the same interface. If the extracted module shares TypeORM entities/Prisma models with another
module (shared foreign keys), split the schema/migration namespace first — same schema-first
warning as Next.js + Prisma above.
