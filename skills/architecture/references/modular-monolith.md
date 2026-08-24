# Modular Monolith

Default topology for Tier 1 and Tier 2 systems (`system-scale-checklist.md` §1–2,
`architecture-selection.md` §1). Load this when MODE: SELECT/UPGRADE lands here, or when MODE:
EXPLORE finds an existing monolith and the reader needs to assess whether its internal module
boundaries are sound.

## 1. What It Is

One deployable, one database (or one DB with schema-per-module isolation), organized internally
as a set of modules with enforced boundaries — as opposed to either (a) a monolith with no
internal boundaries at all ("big ball of mud"), or (b) microservices (separate deployables,
separate databases, network calls between them).

The module boundary is the same seam a microservice boundary would use — a bounded context
(`domain-driven-design.md` §1) — the difference is purely deployment: everything still ships and
runs as one process. This is what makes later extraction (if a real Tier 3 signal ever appears)
a targeted operation instead of an untangling project.

## 2. Structuring Rules

**Organize by feature/bounded context, not by technical layer.** A layer-first structure
(`controllers/`, `services/`, `repositories/` each containing every feature's files) forces every
change to touch three top-level directories and makes module boundaries invisible. Prefer:

```text
src/
├── orders/                 # one module = one bounded context
│   ├── domain/              # entities, value objects, domain events
│   ├── application/         # use cases / application services
│   ├── infrastructure/      # persistence, external clients
│   └── api.ts                # the ONLY file other modules may import from
├── inventory/
│   └── ... (same shape)
└── shared/                 # cross-cutting only: logging, config, error types
```

**Every module exposes exactly one public surface** (`api.ts`/`__init__.py`/`mod.rs`'s `pub use`,
whatever the language's visibility mechanism is) — everything else in the module is internal.
Another module may only import through that surface, never reach into `orders/infrastructure/`
directly.

**No cross-module direct database access.** If `inventory` needs order data, it calls `orders`'s
public API (in-process function call or in-process domain event) — it never queries the `orders`
tables itself, even though they're in the same physical database. This single rule is what makes
later extraction to a real service boundary mechanical rather than a rewrite: the call becomes a
network call, but the caller-side contract doesn't change.

**One aggregate/entity, one owning module.** If two modules both feel they need to write to the
same table, one of them doesn't actually own that data — reroute the write through the owning
module's API.

## 3. Communication Between Modules

- Default: direct in-process function calls through the module's public API — simplest, and
  perfectly fine for most cross-module interactions in a Tier 1/2 system.
- When a module needs to react to something without the triggering module needing to know about
  it (e.g. "on OrderPlaced, send a confirmation email and reserve inventory" — two unrelated
  reactions to one fact): dispatch an in-process domain event through a mediator, per
  `event-driven-architecture.md` §3. This keeps `orders` from importing `notifications` and
  `inventory` directly, without needing a message broker.

## 4. Anti-Patterns

- **Package-by-layer instead of package-by-feature** — the most common way a monolith becomes
  unmaintainable without ever formally being "microservices vs. monolith" undecided; it's simply
  never organized along its actual seams.
- **A `shared`/`common`/`utils` module that accumulates business logic** — cross-cutting
  infrastructure (logging, config, generic error types) belongs there; a `calculateDiscount()`
  used by two modules belongs in whichever module owns pricing, called through its API.
- **Reaching into another module's internals "just this once"** because the public API doesn't
  expose what's needed yet — the fix is to extend the public API deliberately, not to bypass it;
  bypassing it once means the boundary is no longer enforced anywhere.
- **Treating "modular monolith" as a permanent state that never gets checked** — re-run the Scale
  Tier classification (`system-scale-checklist.md` §0) when a graduation trigger (§5) fires, rather
  than assuming the monolith is fine forever because it was fine at Tier 1.
- **Splitting into microservices prematurely because the monolith "feels big"** — file count or
  line count isn't a Tier 3 signal; check the actual five classification questions
  (`system-scale-checklist.md` §0) before extracting anything.

## 5. Extraction Readiness — What Makes a Later Split Cheap

If a module might ever become a real service (a stated Tier 3 signal appears, not a hypothetical
one), these properties — already required by §2 above — are what make that extraction a
mechanical, low-risk operation instead of a rewrite:

```text
1. The module's public API is the only thing other modules call — no back-doors to audit.
2. The module owns its own tables/collections exclusively — no shared-write tables to untangle.
3. Cross-module calls are already expressed as either a function call through the API or a domain
   event through the mediator — both map directly onto "synchronous API call" and "message on a
   broker" respectively, with no redesign of the calling code's shape.
4. The module's dependencies on other modules are one-directional or already event-based — a
   two-way synchronous dependency between the modules being split is the actual hard problem in
   any extraction, and it's far cheaper to resolve while both sides are still in-process.
```

Those four are the *logical* boundary. They're necessary but not sufficient — a module can satisfy
all four and still take a week to physically extract because nothing about how it's built, deployed,
or migrated was ever separated from its siblings. §5a below is the physical counterpart: directory
and build conventions to apply **at SELECT time, before any Tier 3 signal has appeared**, so that
when extraction is actually warranted it's "point this at its own pipeline" rather than "first,
untangle the build."

## 5a. Directory & Build Layout That Stays Split-Ready

These cost almost nothing to do from day one in a modular monolith, and are what turn "the module
boundaries are clean" into "the module can ship as its own deployable this afternoon":

| Convention | Why it matters |
|---|---|
| Independent build entrypoint per module (Go: `cmd/{module}/main.go` per module, not one shared `cmd/server/main.go`; a JVM multi-module build per bounded context; a separate ASGI app factory per Python module) | The test: can you build and run *this module alone* right now, against a stub for its dependencies? If not, untangling a shared entrypoint is cheaper now than mid-extraction under pressure. |
| Per-module Dockerfile / compose service definition, even while every module ships in one container/stack today | "Deploy separately" becomes deleting a `depends_on` line, not authoring deployment config from scratch under time pressure. |
| Per-module migration/schema namespace (`migrations/{module}/`, or schema-qualified table names) instead of one flat migrations directory | Makes "give this module its own DB instance" a connection-string change, not an archaeology project over historical migrations. |
| Module-scoped dependency manifest where the language supports it (Cargo workspace member, Go workspace module, npm/pnpm package) per bounded context | Its dependency list is accurate on day one of extraction, instead of inherited wholesale from one shared root manifest nobody has pruned. |

**Don't over-invest before it's justified**: none of the above means deploying modules separately
today, or standing up infrastructure a Tier 1/2 system doesn't need — it means shaping the *existing*
single-deployable build so a later split is a mechanical lift, per the same anti-over-engineering
stance as everywhere else in this skill. A Tier 1 system with one module doesn't need per-module
Dockerfiles; this applies once there's more than one real bounded context sharing a deployable.

**Stack-specific detail**: see the "Extraction Mechanics" note at the end of each stack's section in
`backend-script-patterns.md` for what concretely moves as-is vs. what needs a new adapter when a
module described there is actually lifted out.
