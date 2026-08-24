# SDS Template G: Rust / REST API

> Reference for `design` skill — loaded on demand when creating MODE G SDS documents.

---

## TEMPLATE G: Rust / REST API SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: {tech_stack — discover from Cargo.toml: axum|actix-web, sqlx|diesel, tokio}

---

## 1. Module Overview

### 1.1 Description
[Describe what this module does in the system]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Module Type**: [Core Domain / Supporting / Infrastructure]
**Scale Tier**: [Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed — one-line reason, see `.claude/skills/architecture/references/system-scale-checklist.md`]

### 1.3 Architecture Layer

```
src/
├── domain/{module}/
│   ├── model.rs           # Plain structs/enums, business rules — no tokio/axum/sqlx
│   ├── ports.rs           # Port traits (e.g. `trait OrderRepo`) — the only boundary out
│   └── error.rs           # Typed error enum for this feature's failure modes
├── application/{module}/
│   └── use_cases.rs        # Functions/structs taking `&dyn OrderRepo` (or a generic bound)
├── infrastructure/
│   ├── http/{module}/      # axum/actix-web handlers, request/response DTOs, routes
│   └── persistence/{module}/ # sqlx/diesel implementations of the port traits
└── main.rs                 # Wiring: constructs adapters, injects them into use cases
```

**Dependency direction (compiler-enforced, not just convention)**:
- `domain/` — plain structs/enums, business rules, port traits. Depends on **stdlib only**.
  Compiles without `tokio`, `axum`/`actix-web`, `sqlx`/`diesel` in scope.
- `application/` — use cases: functions/structs taking `&dyn OrderRepo` or a generic
  `<R: OrderRepo>` bound, orchestrating domain logic. Depends on **domain + port traits only**.
- `infrastructure/` — adapters: axum/actix-web handlers, sqlx/diesel implementations of the
  port traits, external HTTP clients. Depends on **domain + application**, never the reverse.

**Domain structs/enums**: [List]
**Port traits**: [List]
**APIs**: [List main endpoints]
**Dependencies**: [M-01 IAM for auth, etc.]

**[DESIGN DECISION]** Module boundary enforced by folder convention (default) vs. a Cargo
workspace with one crate per bounded context (compiler-enforced — `domain` crate can't even
`Cargo.toml`-depend on `axum`). Use the workspace split once folder-convention enforcement has
actually been violated more than once, or when this module is large/stable enough to warrant its
own release cadence — not upfront for a single-feature module. [ASSUMPTION unless SRS/architecture
doc states otherwise]

---

## 2. Domain Model

### 2.1 Domain Struct/Enum: `[EntityName]`

```rust
// src/domain/{module}/model.rs
// Traceability: SDS M-XX Section 2.1

#[derive(Debug, Clone, PartialEq)]
pub struct [EntityName] {
    pub id: [EntityName]Id,
    pub [field]: String,
    pub active: bool,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct [EntityName]Id(pub uuid::Uuid);
```

**Field Definitions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | `[EntityName]Id` (newtype over `Uuid`) | Yes | Strongly-typed ID — prevents passing the wrong entity's ID by accident |
| [field] | `String` | Yes | [description] |
| active | `bool` | Yes | Soft delete flag |
| created_at | `DateTime<Utc>` | Yes | Creation timestamp |
| updated_at | `DateTime<Utc>` | Yes | Last update timestamp |

**Business rules enforced on construction** (not left to callers to remember):

```rust
impl [EntityName] {
    pub fn new([field]: String) -> Result<Self, [EntityName]Error> {
        if [field].trim().is_empty() {
            return Err([EntityName]Error::InvalidField { reason: "must not be empty".into() });
        }
        Ok(Self { id: [EntityName]Id(uuid::Uuid::new_v4()), [field], active: true,
                   created_at: chrono::Utc::now(), updated_at: chrono::Utc::now() })
    }
}
```

### 2.2 Typed Error Enum

**[REQUIRED]** One `enum` per feature's failure modes — never `anyhow::Error`/`Box<dyn Error>`
crossing the domain/application boundary. Convert to `anyhow`/a generic error only at the
outermost boundary (the axum/actix handler, or `main()`).

```rust
// src/domain/{module}/error.rs
// Traceability: SDS M-XX Section 2.2

#[derive(Debug, thiserror::Error)]
pub enum [EntityName]Error {
    #[error("{entity} not found: {id}")]
    NotFound { id: [EntityName]Id },

    #[error("{entity} already exists: {field}")]
    Conflict { field: String },

    #[error("invalid field: {reason}")]
    InvalidField { reason: String },

    #[error("repository error: {0}")]
    Repository(#[from] RepoError),
}
```

Callers pattern-match on this (`match err { [EntityName]Error::NotFound { .. } => ... }`) rather
than string-matching an `anyhow` message.

---

## 3. Port Traits

### 3.1 Repository Port

```rust
// src/domain/{module}/ports.rs
// Traceability: SDS M-XX Section 3.1
use async_trait::async_trait;

#[async_trait]
pub trait [Entity]Repo: Send + Sync {
    async fn find_by_id(&self, id: [Entity]Id) -> Result<Option<[Entity]>, RepoError>;
    async fn find_by_field(&self, field: &str) -> Result<Option<[Entity]>, RepoError>;
    async fn find_all(&self, filter: [Entity]Filter) -> Result<Vec<[Entity]>, RepoError>;
    async fn save(&self, entity: &[Entity]) -> Result<(), RepoError>;
}

pub struct [Entity]Filter {
    pub active: Option<bool>,
    pub page: u32,
    pub page_size: u32,
}
```

`RepoError` is a typed enum too (`NotFound`/`Conflict`/`Unavailable`), defined alongside the
trait — infrastructure adapters map `sqlx::Error`/`diesel::result::Error` into it, so the domain
never sees a driver-specific error type.

### 3.2 External Service Port (if this feature calls an external system)

```rust
#[async_trait]
pub trait [Name]Client: Send + Sync {
    async fn [method](&self, ...) -> Result<..., [Name]ClientError>;
}
```

Naming this as a trait (not a concrete `reqwest::Client` field on the use case) is what makes the
use case testable with a fake, and is the Rust equivalent of MODE B's repository interface.

---

## 4. Application / Use-Case Design

### 4.1 Use Cases List

| Use Case | File | SDS Reference |
|----------|------|---------------|
| Get[Entity] | application/{module}/get_{entity}.rs | Section 4.2 |
| List[Entity] | application/{module}/list_{entity}.rs | Section 4.3 |
| Create[Entity] | application/{module}/create_{entity}.rs | Section 4.4 |

### 4.2 Get[Entity] Use Case

```rust
// src/application/{module}/get_{entity}.rs
// Traceability: SDS M-XX Section 4.2 Get[Entity] Flow

pub struct Get[Entity]Input {
    pub id: [Entity]Id,
    pub requester_id: UserId, // for ownership check
}

pub async fn get_[entity](
    repo: &dyn [Entity]Repo,
    input: Get[Entity]Input,
) -> Result<[Entity], [Entity]Error> {
    let entity = repo.find_by_id(input.id).await?
        .ok_or([Entity]Error::NotFound { id: input.id })?;
    // Optional: ownership check here (never .unwrap() past this — expected failure case)
    Ok(entity)
}
```

**Flow:**
```
1. Validate input (ID well-formed — already guaranteed by the newtype)
2. Query repo.find_by_id(id)
3. If None → return [Entity]Error::NotFound (not a panic, not an .unwrap())
4. Optional: ownership check
5. Return entity
```

**Dependency injection shape**: `&dyn [Entity]Repo` (trait object) when the use case is called
polymorphically across request handlers, or `<R: [Entity]Repo>` (generic bound) when
monomorphization is preferred for a hot path — state which and why; both satisfy the same port
boundary, this is a performance/compile-time trade-off, not an architecture one.

### 4.3 Create[Entity] Use Case

**Flow:**
```
1. Validate input via [Entity]::new(...) — construction enforces invariants
2. Check uniqueness via repo.find_by_field(...)
3. If exists → return [Entity]Error::Conflict
4. repo.save(&entity)
5. Return entity
```

**No `.unwrap()`/`panic!` in this path** — a missing row, a duplicate key, a malformed request
are normal expected cases modeled as `Result` variants. `.unwrap()`/`panic!` is acceptable only
in `main()` at startup (e.g. a config value that must exist for the process to run at all) or in
tests.

---

## 5. API Specification

> Full checklist: `design/references/api-design.md`.

### 5.1 Endpoints Overview

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/v1/[resource] | JWT | List resources |
| GET | /api/v1/[resource]/:id | JWT | Get by ID |
| POST | /api/v1/[resource] | JWT | Create resource |

### 5.2 Request/Response Types (axum)

```rust
// src/infrastructure/http/{module}/dto.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct Create[Entity]Request {
    pub [field]: String,
}

#[derive(Debug, Serialize)]
pub struct [Entity]Response {
    pub id: uuid::Uuid,
    pub [field]: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

impl From<[Entity]> for [Entity]Response {
    fn from(e: [Entity]) -> Self {
        Self { id: e.id.0, [field]: e.[field], created_at: e.created_at }
    }
}
```

### 5.3 Handlers

```rust
// src/infrastructure/http/{module}/handler.rs
// Traceability: SDS M-XX Section 5.3

use axum::{extract::{State, Path}, Json, http::StatusCode};

pub async fn get_[entity](
    State(state): State<AppState>,
    Path(id): Path<uuid::Uuid>,
) -> Result<Json<[Entity]Response>, ApiError> {
    let entity = get_[entity]_use_case(&*state.[entity]_repo, Get[Entity]Input {
        id: [Entity]Id(id),
        requester_id: /* from auth extractor */,
    }).await?;
    Ok(Json(entity.into()))
}
```

`AppState`/`axum::extract::State` and `Path`/`Json` extractors live **only** in
`infrastructure/http/` — never referenced by a `domain`/`application` type signature.

### 5.4 API Details

#### GET /api/v1/[resource]
**Purpose**: [description]
**Auth**: JWT required, role: [ROLE]
**Query Params**: `page` (default: 1), `page_size` (default: 20, max: 100)
**Response**: `{ "data": [[Entity]Response], "pagination": {...} }`
**HTTP Status**: 200 OK

#### GET /api/v1/[resource]/:id
**Purpose**: [description]
**Auth**: JWT required
**Response**: `{ "data": [Entity]Response }`
**HTTP Status**: 200 OK | 404 Not Found

#### POST /api/v1/[resource]
**Purpose**: [description]
**Auth**: JWT required, role: [ROLE]
**Request Body**: `Create[Entity]Request`
**Response**: `{ "data": [Entity]Response }`
**HTTP Status**: 201 Created | 400 Bad Request | 409 Conflict

---

## 6. Security Design

### 6.1 Authentication Requirements

| Endpoint | Auth | Role |
|----------|------|------|
| GET /api/v1/[resource] | Optional | - |
| GET /api/v1/[resource]/:id | Required (JWT) | Any |
| POST /api/v1/[resource] | Required (JWT) | ADMIN |

### 6.2 Authorization Rules

```rust
// axum extractor pulls claims from the JWT — never trust a header the client can set directly
pub struct AuthUser { pub user_id: UserId, pub role: Role }

// In handler or middleware layer (tower::Layer), not inside the use case:
if claims.role != Role::Admin {
    return Err(ApiError::Forbidden);
}
// Ownership check happens inside the use case (domain-level), using requester_id vs entity owner
```

Auth chain: Authenticated → Role → Permission → Resource ownership → Action — not just "has a
valid JWT."

### 6.3 Data Security

- **Sensitive fields**: [fields] → never appear in `[Entity]Response` (they exist on the domain
  struct but the `From<[Entity]> for [Entity]Response` impl is the enforcement point — it simply
  never reads them)
- **Input sanitization**: trim/normalize at DTO→domain conversion, not deep inside a use case
- **SQL injection**: sqlx compile-time-checked queries (`sqlx::query!`) or diesel's query builder
  — never a `format!()`-built query string with user input
- **Rate limiting**: `tower::limit`/gateway-level — state the tier for auth/payment/search
  endpoints specifically

### 6.4 Universal Security (see `design/references/security-checklist.md`)

Apply the full checklist's `[MUST]` items; the ones most likely to be missed for a Rust/Axum
feature:

- **Secrets**: JWT signing key / DB credentials from env var or secret manager — never a literal
  in code or a committed config
- **Business security**: for any state-changing endpoint touching balance/payment/approval, name
  the concurrency-control mechanism (DB transaction + `SELECT ... FOR UPDATE`, an optimistic
  version column, or a distributed lock) and, for transfers/payments, the idempotency mechanism
  (`Idempotency-Key` header)
- **Error handling**: confirm §7's mapping never lets a `sqlx::Error`/`diesel::result::Error`
  message or a Rust panic message reach the client
- **CORS/CSRF**: state whether this API is Bearer-token or cookie-based auth, and design the
  corresponding protection (CSRF tokens only needed for cookie auth)
- **Panics as a DoS surface**: a reachable `.unwrap()`/`panic!`/array-index-out-of-bounds on
  attacker-controlled input is a crash-the-worker vector, not just a code-quality nit — treat it
  as a security item, not only a correctness one
- **Security testing**: Test plan must include unauthenticated, unauthorized/IDOR, expired/invalid
  JWT, and rate-limit-exceeded cases

---

## 7. Error Handling

### 7.1 Typed Error → HTTP Status Mapping

Done **once**, at the adapter boundary (`infrastructure/http/`) — not repeated per handler.

```rust
// src/infrastructure/http/error.rs
// Traceability: SDS M-XX Section 7.1

pub enum ApiError {
    NotFound(String),
    Conflict(String),
    BadRequest(String),
    Unauthorized,
    Forbidden,
    Internal,
}

impl From<[Entity]Error> for ApiError {
    fn from(e: [Entity]Error) -> Self {
        match e {
            [Entity]Error::NotFound { .. } => ApiError::NotFound(e.to_string()),
            [Entity]Error::Conflict { .. } => ApiError::Conflict(e.to_string()),
            [Entity]Error::InvalidField { reason } => ApiError::BadRequest(reason),
            [Entity]Error::Repository(_) => {
                tracing::error!(error = %e, "repository error");
                ApiError::Internal // internal detail stays in the log only
            }
        }
    }
}

impl axum::response::IntoResponse for ApiError {
    fn into_response(self) -> axum::response::Response {
        let (status, msg) = match self {
            ApiError::NotFound(m) => (StatusCode::NOT_FOUND, m),
            ApiError::Conflict(m) => (StatusCode::CONFLICT, m),
            ApiError::BadRequest(m) => (StatusCode::BAD_REQUEST, m),
            ApiError::Unauthorized => (StatusCode::UNAUTHORIZED, "unauthorized".into()),
            ApiError::Forbidden => (StatusCode::FORBIDDEN, "forbidden".into()),
            ApiError::Internal => (StatusCode::INTERNAL_SERVER_ERROR, "internal server error".into()),
        };
        (status, Json(ErrorResponse { error: msg })).into_response()
    }
}
```

### 7.2 Error Code Mapping

| Domain/Typed Error | HTTP Status | Scenario |
|--------------------|------------|---------|
| `[Entity]Error::NotFound` | 404 Not Found | Resource doesn't exist |
| `[Entity]Error::Conflict` | 409 Conflict | Duplicate entry |
| `[Entity]Error::InvalidField` | 400 Bad Request | Business rule violation |
| (deserialization failure) | 400 Bad Request | Malformed JSON body / query params |
| (auth extractor failure) | 401 Unauthorized | Invalid/missing JWT |
| (role/ownership check failure) | 403 Forbidden | Insufficient role or not resource owner |
| `[Entity]Error::Repository` | 500 Internal Server Error | DB/driver failure — logged, never detailed to client |

---

## 8. Performance Design

### 8.1 Indexing & Query Access Pattern

| Index | Fields | Rationale |
|-------|--------|-----------|
| `idx_[field]` | `[field]` | Unique lookup |
| `idx_active_created` | `active, created_at DESC` | List queries with sort |

### 8.2 Pagination

- Default page size: 20
- Max page size: 100 (enforced in the use case, not just the handler)
- `OFFSET`/`LIMIT` via sqlx/diesel with an indexed sort column; switch to keyset pagination
  (`id`/`created_at` cursor) once the table can grow past a few hundred thousand rows or is
  queried at deep offsets

### 8.3 Connection Pool Sizing

- `sqlx::PgPool`/diesel connection pool `max_connections`: state the value and size it against
  expected pod count × per-pod pool ≤ DB's own max connection limit
- State the pool's `acquire_timeout` — an unbounded wait to acquire a connection under load turns
  a DB slowdown into a full request-queue backup

### 8.4 Async Runtime Concurrency Bounds

- Any fan-out this use case performs (e.g. `futures::future::join_all` over N items) is bounded
  (`buffer_unordered(n)` or a semaphore), not one unbounded task per item
- State the tokio runtime flavor (`#[tokio::main]` multi-thread vs. `current_thread`) and worker
  thread count if non-default

### 8.5 Universal Performance (see `design/references/performance-checklist.md`)

- **Performance baseline**: state expected RPS and P95/P99 latency target for this endpoint
  (§0 of the checklist) — mark `[PERF TARGET NEEDED]` if the SRS doesn't specify one
- **Transaction scope**: any DB transaction stays short/deterministic/DB-only — no HTTP call,
  blocking Kafka publish, or `.await`-ing an external system inside it
- **Timeout**: every downstream call (Core Banking, other services, `reqwest` client) states
  connect/read/overall timeout; every retry states bound + backoff + jitter, excluding
  4xx/validation errors
- **Blocking work**: any CPU-heavy computation or a blocking (non-async) library call inside an
  `async fn` uses `tokio::task::spawn_blocking`, never called inline on the async executor

---

## 9. Distributed & Async Design

> Full checklist: `design/references/distributed-systems-checklist.md`. Fill this section when
> this module crosses a service boundary, publishes/consumes a queue message, runs work via
> `tokio::spawn` outside the request lifecycle, or calls an external system (Core Banking,
> payment gateway). If this module is a plain synchronous CRUD API with no external dependency,
> state "N/A — synchronous, single-service, no messaging" and skip to Test Plan.

### 9.1 Data Ownership & Consistency

- **Owner**: this module owns `[entity]` — no other service writes to its table directly
- **Source of truth**: [this service | Core Banking | another service] is authoritative for `[field]`
- **Consistency**: [STRONG | EVENTUAL] for `[operation]` — state the reason if STRONG

### 9.2 Async Boundary & Durability

- **Sync vs. async**: [this operation returns synchronously | this operation returns 202 and
  processes via a queue/Kafka topic `[topic]`]
- **Durability**: if async, the operation is persisted (outbox row in the same DB transaction, or
  a durable queue publish) before returning 202 — never a bare `tokio::spawn` with no persistence,
  since a process restart loses an in-flight `tokio::spawn`ed task entirely

### 9.3 Idempotency & Ordering

- **Idempotency key**: `[idempotencyKey field]` propagated from [client/API] through to
  [consumer/external call]
- **Duplicate handling**: consumer checks `already_processed(event_id)` before applying, marks
  processed in the same DB transaction as the business update
- **Ordering scope**: [Global | Tenant | Account | Aggregate] — partition key: `[field]`

### 9.4 State Machine (if this entity has a status field)

```text
[PENDING] → [PROCESSING] → [COMPLETED]
                ↓
           [RETRYING] → [FAILED]
```
Transitions validated in a domain method (e.g. `impl [Entity] { fn transition_to(...) }`) that
returns `Result<(), [Entity]Error>` — never set directly via a public field mutation from a
consumer/handler.

### 9.5 Failure Handling

- **Retry**: [bounded count] attempts, exponential backoff + jitter, retryable errors: `[list]`;
  non-retryable: `[list]`
- **DLQ**: topic/queue `[name].dlq`, carries `event_id, event_type, payload, retry_count, error, failed_at, correlation_id`
- **Unknown result**: a timeout calling `[external system]` transitions this record to `UNKNOWN`,
  resolved via `[status-inquiry endpoint | reconciliation job]` — never directly to `FAILED`
- **Reconciliation**: [if financial/critical] `[job name]` compares `[fields]` against
  `[external system]` on `[schedule]`

---

## 10. Test Plan

### 10.1 Use-Case Unit Tests (fake repository implementing the port trait)

```rust
struct Fake[Entity]Repo { store: Mutex<HashMap<[Entity]Id, [Entity]>> }

#[async_trait]
impl [Entity]Repo for Fake[Entity]Repo {
    async fn find_by_id(&self, id: [Entity]Id) -> Result<Option<[Entity]>, RepoError> {
        Ok(self.store.lock().unwrap().get(&id).cloned())
    }
    // ...
}
```

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `test_get_success` | Valid ID | Returns entity |
| `test_get_not_found` | Unknown ID | `[Entity]Error::NotFound` |
| `test_create_success` | Valid input | Returns created entity |
| `test_create_conflict` | Duplicate field | `[Entity]Error::Conflict` |
| `test_create_invalid_field` | Empty required field | `[Entity]Error::InvalidField` |

No `.unwrap()` on the *result under test* in a case expected to fail — assert on the `Err`
variant explicitly (`assert!(matches!(result, Err([Entity]Error::NotFound { .. })))`).

### 10.2 Handler Integration Tests (axum `tower::ServiceExt::oneshot` or `axum-test`)

| Test Case | Endpoint | Auth | Expected Status |
|-----------|----------|------|----------------|
| GET success | GET /:id | Valid JWT | 200 OK |
| GET not found | GET /invalid-id | Valid JWT | 404 Not Found |
| GET no auth | GET /:id | None | 401 Unauthorized |
| POST create | POST / | Admin JWT | 201 Created |
| POST conflict | POST / | Admin JWT | 409 Conflict |
| POST validation | POST / | Admin JWT | 400 Bad Request |

### 10.3 SRS Traceability

| SRS Requirement | Implemented In |
|----------------|---------------|
| FR-01: [requirement] | Use case: [name], API: [endpoint] |
| FR-02: [requirement] | Domain field: [field] |
| BR-01: [business rule] | `[Entity]::new(...)` construction invariant |

---

## 11. Design Decisions & Alternatives

Per `.claude/skills/design/references/decision-records.md` §2 — record any costly-to-reverse
choice (e.g. axum vs. actix-web, sqlx vs. diesel, workspace-per-crate boundary vs. a single crate)
with alternatives considered and why this one won.

## 12. Risks & Trade-offs

[State risks — e.g. "no compile-time enforcement between application and infrastructure beyond
convention until a workspace split" — and whether that's accepted or deferred.]

## 13. Implementation Mapping

| SDS Section | Implementation File |
|--------------|---------------------|
| §2 Domain | `domain/{module}/mod.rs` |
| §3 Port traits | `domain/{module}/ports.rs` |
| §4 Application/use cases | `application/{module}/{use_case}.rs` |
| §5 API/handlers | `infrastructure/http/{module}/handler.rs` |

## 14. Implementation Readiness

**Status**: [READY | PARTIALLY_READY | BLOCKED]
[State any `[NEEDS SPEC CLARIFICATION]`/`[PERF TARGET NEEDED]`/`[SECURITY EXCEPTION]` items and
what `/implement` can start on now vs. what's blocked.]
```

---

## NAMING CONVENTIONS (MODE G)

Discover exact conventions from `Cargo.toml`/CLAUDE.md — below are typical patterns:

- SDS path: Glob `docs/*/sds/` or `docs/04-sds/` → compute next M-XX
- Module ID: `M-XX` (project-specific numbering)
- Crate/module name: `snake_case`
- Domain struct/enum: `PascalCase`
- Newtype IDs: `[Entity]Id` wrapping `Uuid` or `i64`
- Use case function/file: `{action}_{entity}.rs` (e.g. `create_order.rs`)
- Handler file: `{module}/handler.rs`
- Port trait: `[Entity]Repo` / `[Name]Client` (verb-free noun, not `I[Entity]Repo`)
- Repository adapter impl: `Pg[Entity]Repo` / `Sqlite[Entity]Repo` (prefixed by backing store)
- Error enum: `[Entity]Error` (domain), `ApiError` (HTTP boundary)

---

## HEXAGONAL ARCHITECTURE RULES (MODE G)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|----------------|
| Domain | stdlib only (`std`, `chrono`, `uuid`, `thiserror` are commonly accepted as "effectively stdlib" — state if this project draws the line differently) | `tokio`, `axum`/`actix-web`, `sqlx`/`diesel`, any infrastructure crate |
| Application | Domain + port traits | `axum`/`actix-web` extractor types, `sqlx`/`diesel` concrete types, HTTP/DB implementations |
| Infrastructure | Domain + Application | Nothing above it — infrastructure is a leaf; nothing else in the graph imports it |

**Domain Design:**
- Plain structs/enums, no framework derive macros beyond `serde`'s if the domain type is directly
  (de)serialized — prefer a separate DTO in `infrastructure/http/` when the wire shape and the
  domain shape diverge even slightly
- Business rules enforced at construction (`::new()` returning `Result`) or via a transition
  method — never a public field mutation that bypasses validation
- No `.unwrap()`/`panic!`/`expect()` on a fallible operation that's a normal expected case;
  acceptable only in `main()` at startup or in tests
- Port traits (`trait [Entity]Repo`) are the *only* boundary a domain/application type depends on
  to reach the outside world — never a concrete `sqlx::PgPool` field on a use case struct

**Use-Case Pattern:**
```rust
// Every use case: a function (or a struct with an `execute`/`call` method) taking
// `&dyn Trait` or a generic `<R: Trait>` bound — never a concrete infrastructure type
pub async fn create_[entity](
    repo: &dyn [Entity]Repo,
    input: Create[Entity]Input,
) -> Result<[Entity], [Entity]Error>
```

**SDS Traceability Comment (required):**
```rust
// Traceability: SDS M-XX Section Y.Z [Use Case Name]
pub async fn create_[entity](...) { ... }
```

**SDS Design Principle:**
Design from the domain (struct/enum + port trait) outward → don't design the HTTP layer first and
retrofit the domain to match whatever axum's extractors happened to give you.
