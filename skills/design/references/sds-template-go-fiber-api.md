# SDS Template B: Go / REST API

> Reference for `design` skill — loaded on demand when creating MODE B SDS documents.

---

## TEMPLATE B: Go / REST API SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: {tech_stack — discover from CLAUDE.md or project config}

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
internal/
├── domain/{module}/entity/        # Pure Go structs
├── domain/{module}/repository/    # Repository interfaces
├── domain/{module}/service/       # Service interfaces
├── domain/{module}/errors.go      # Domain errors
├── usecase/{module}/              # Use cases
├── adapter/http/{module}/         # Fiber handlers, DTOs, routes
├── infrastructure/mongodb/{module}/ # MongoDB implementations
├── infrastructure/redis/{module}/   # Redis implementations
└── infrastructure/service/{module}/ # Service implementations
```

**Entities**: [List domain structs]
**APIs**: [List main endpoints]
**Dependencies**: [M-01 IAM for auth, etc.]

---

## 2. Data Model

### 2.1 Domain Entity: [EntityName]

```go
// internal/domain/{module}/entity/{entity}.go
// Traceability: SDS M-XX Section 2.1
package entity

import "time"

type [EntityName] struct {
    ID        string    `bson:"_id,omitempty" json:"id"`
    [Field]   string    `bson:"[field]" json:"[field]"`
    Active    bool      `bson:"active" json:"active"`
    CreatedAt time.Time `bson:"created_at" json:"created_at"`
    UpdatedAt time.Time `bson:"updated_at" json:"updated_at"`
}
```

**Field Definitions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ID | string (ObjectID hex) | Yes | MongoDB document ID |
| [field] | string | Yes | [description] |
| active | bool | Yes | Soft delete flag |
| created_at | time.Time | Yes | Creation timestamp |
| updated_at | time.Time | Yes | Last update timestamp |

### 2.2 MongoDB Collection Design

**Collection**: `[collection_name]`

```json
{
  "_id": ObjectId("..."),
  "[field]": "value",
  "active": true,
  "created_at": ISODate("..."),
  "updated_at": ISODate("...")
}
```

**Indexes:**

| Index | Fields | Type | Reason |
|-------|--------|------|--------|
| `idx_[field]` | `{[field]: 1}` | Unique | Frequent lookup |
| `idx_active_created` | `{active: 1, created_at: -1}` | Compound | List query with sort |

```go
// MongoDB index creation (run at startup)
indexes := []mongo.IndexModel{
    {
        Keys:    bson.D{{"[field]", 1}},
        Options: options.Index().SetUnique(true),
    },
    {
        Keys: bson.D{{"active", 1}, {"created_at", -1}},
    },
}
```

### 2.3 Redis Cache Design (if applicable)

| Key Pattern | Value | TTL | Eviction |
|-------------|-------|-----|---------|
| `{module}:{id}` | JSON entity | 15 min | On update/delete |
| `bloom:{module}:emails` | Bloom filter | - | Never (persistent) |

---

## 3. Domain Interfaces

### 3.1 Repository Interface

```go
// internal/domain/{module}/repository/{name}_repository.go
package repository

import (
    "context"
    "{module_path}/internal/domain/{module}/entity"
)

type [Entity]Repository interface {
    FindByID(ctx context.Context, id string) (*entity.[Entity], error)
    FindByField(ctx context.Context, field string) (*entity.[Entity], error)
    FindAll(ctx context.Context, filter [Entity]Filter) ([]*entity.[Entity], error)
    // Write operations only if module requires it
}

type [Entity]Filter struct {
    Active    *bool
    Page      int
    PageSize  int
}
```

### 3.2 Service Interface (if needed)

```go
// internal/domain/{module}/service/{name}_service.go
package service

type [Name]Service interface {
    [Method](ctx context.Context, ...) (..., error)
}
```

### 3.3 Domain Errors

```go
// internal/domain/{module}/errors.go
package {module}

import "errors"

var (
    Err[Entity]NotFound   = errors.New("{entity} not found")
    Err[Entity]Conflict   = errors.New("{entity} already exists")
    ErrInvalidInput       = errors.New("invalid input")
)
```

---

## 4. API Specification

### 4.1 Endpoints Overview

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/v1/[resource] | JWT | List resources |
| GET | /api/v1/[resource]/:id | JWT | Get by ID |
| POST | /api/v1/[resource] | JWT | Create resource |

### 4.2 Request DTOs

```go
// internal/adapter/http/{module}/dto.go
package {module}

type Create[Entity]Request struct {
    Field string `json:"field" validate:"required,min=1,max=255"`
}

type List[Entity]Request struct {
    Page     int    `query:"page" validate:"min=1"`
    PageSize int    `query:"page_size" validate:"min=1,max=100"`
}
```

### 4.3 Response DTOs

```go
type [Entity]Response struct {
    ID        string    `json:"id"`
    Field     string    `json:"field"`
    CreatedAt time.Time `json:"created_at"`
}

// Mapping function
func To[Entity]Response(e *entity.[Entity]) *[Entity]Response {
    return &[Entity]Response{
        ID:        e.ID,
        Field:     e.Field,
        CreatedAt: e.CreatedAt,
    }
}
```

### 4.4 API Details

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

## 5. Use Case Design

### 5.1 Use Cases List

| Use Case | File | SDS Reference |
|----------|------|---------------|
| Get[Entity] | usecase/{module}/get_{entity}_usecase.go | Section 5.2 |
| List[Entity] | usecase/{module}/list_{entity}_usecase.go | Section 5.3 |
| Create[Entity] | usecase/{module}/create_{entity}_usecase.go | Section 5.4 |

### 5.2 Get[Entity] Use Case

```go
// internal/usecase/{module}/get_{entity}_usecase.go
// Traceability: SDS M-XX Section 5.2 Get[Entity] Flow

type Get[Entity]Input struct {
    ID     string
    UserID string // For ownership check
}

type Get[Entity]Output struct {
    [Entity] *entity.[Entity]
}

type Get[Entity]UseCase struct {
    repo repository.[Entity]Repository
}

func NewGet[Entity]UseCase(repo repository.[Entity]Repository) *Get[Entity]UseCase

func (uc *Get[Entity]UseCase) Execute(
    ctx context.Context,
    input *Get[Entity]Input,
    meta RequestMeta,
) (*Get[Entity]Output, error)
```

**Flow:**
```
1. Validate input (ID not empty)
2. Query repository: repo.FindByID(ctx, input.ID)
3. If not found → return domain.Err[Entity]NotFound
4. Optional: check ownership (if user-specific resource)
5. Return output
```

### 5.3 Create[Entity] Use Case

**Flow:**
```
1. Validate input (business rules)
2. Check uniqueness (via Bloom filter → MongoDB if needed)
3. Map input → entity
4. Save via repository
5. Invalidate relevant Redis cache
6. Return output
```

---

## 6. Handler Design

### 6.1 Handler Structure

```go
// internal/adapter/http/{module}/handler.go
package {module}

type [Entity]Handler struct {
    get[Entity]UC  *usecase.Get[Entity]UseCase
    list[Entity]UC *usecase.List[Entity]UseCase
    // ...
}

func New[Entity]Handler(
    get[Entity]UC *usecase.Get[Entity]UseCase,
    list[Entity]UC *usecase.List[Entity]UseCase,
) *[Entity]Handler

func (h *[Entity]Handler) GetByID(c *fiber.Ctx) error
func (h *[Entity]Handler) List(c *fiber.Ctx) error
```

### 6.2 Route Registration

```go
// internal/adapter/http/{module}/routes.go
func RegisterRoutes(app *fiber.App, handler *[Entity]Handler, authMiddleware fiber.Handler) {
    v1 := app.Group("/api/v1")
    resource := v1.Group("/[resource]")

    // Public routes (if any)
    resource.Get("/", handler.List)

    // Protected routes
    protected := resource.Group("/", authMiddleware)
    protected.Get("/:id", handler.GetByID)
    protected.Post("/", handler.Create)
}
```

---

## 7. Security Design

### 7.1 Authentication Requirements

| Endpoint | Auth | Role |
|----------|------|------|
| GET /api/v1/[resource] | Optional | - |
| GET /api/v1/[resource]/:id | Required (JWT) | Any |
| POST /api/v1/[resource] | Required (JWT) | ADMIN |

### 7.2 Authorization Rules

```go
// In handler: extract user from JWT claims
userID := c.Locals("userID").(string)
role := c.Locals("role").(string)

// Role check
if role != "admin" {
    return c.Status(fiber.StatusForbidden).JSON(shared.ErrorResponse("insufficient permissions"))
}

// Ownership check
if resource.OwnerID != userID && role != "admin" {
    return c.Status(fiber.StatusForbidden).JSON(shared.ErrorResponse("not your resource"))
}
```

### 7.3 Data Security

- **Sensitive fields**: [fields] → never expose in response DTOs
- **Input sanitization**: Trim whitespace, normalize email/symbol
- **MongoDB injection**: Always use typed BSON, never string concat
- **Rate limiting**: Applied via middleware at route group level — state the tier for auth/payment/search endpoints specifically, not just "rate limiting exists"

### 7.4 Universal Security (see `design/references/security-checklist.md`)

Apply the full checklist's `[MUST]` items; the ones most likely to be missed for a Go/Fiber
feature:

- **Secrets**: JWT signing key / DB credentials from env var or secret manager — never a literal in code or config committed to the repo
- **Business security**: for any state-changing endpoint touching balance/payment/approval, name the concurrency-control mechanism (DB transaction + `SELECT ... FOR UPDATE`, optimistic version column, or distributed lock) and, for transfers/payments, the idempotency mechanism (`Idempotency-Key` header)
- **Error handling**: confirm §8's error mapping never lets a Mongo/driver error message reach the client — internal detail goes to the log only
- **CORS/CSRF**: this API is Bearer-token auth — state that CSRF tokens aren't needed for that reason (not left implicit), and that CORS is not configured with `*` alongside credentialed requests
- **Command injection**: N/A unless this feature shells out — state so explicitly if it does not
- **Security testing**: §Test plan must include unauthenticated, unauthorized/IDOR (fetch another user's resource by id), expired/invalid JWT, and rate-limit-exceeded cases

---

## 8. Error Handling

### 8.1 Domain Error → HTTP Status Mapping

```go
// internal/shared/errors/handler.go
func HandleError(c *fiber.Ctx, err error) error {
    switch {
    case errors.Is(err, domain.Err[Entity]NotFound):
        return c.Status(404).JSON(ErrorResponse("not found"))
    case errors.Is(err, domain.Err[Entity]Conflict):
        return c.Status(409).JSON(ErrorResponse("already exists"))
    case errors.Is(err, domain.ErrInvalidInput):
        return c.Status(400).JSON(ErrorResponse(err.Error()))
    default:
        log.Error("internal error", "err", err)
        return c.Status(500).JSON(ErrorResponse("internal server error"))
    }
}
```

### 8.2 Error Code Mapping

| Domain Error | HTTP Status | Scenario |
|-------------|------------|---------|
| Err[Entity]NotFound | 404 Not Found | Resource doesn't exist |
| Err[Entity]Conflict | 409 Conflict | Duplicate entry |
| ErrInvalidInput | 400 Bad Request | Business rule violation |
| (validation error) | 400 Bad Request | DTO validation failure |
| (auth error) | 401 Unauthorized | Invalid/missing JWT |
| (permissions) | 403 Forbidden | Insufficient role |

---

## 9. Performance Design

### 9.1 MongoDB Index Strategy

| Index | Fields | Rationale |
|-------|--------|-----------|
| `idx_[field]` | `{[field]: 1}` | Unique lookup |
| `idx_active_created` | `{active: 1, created_at: -1}` | List queries |

### 9.2 Redis Caching

| Cache Key | Value | TTL | Eviction Trigger |
|-----------|-------|-----|-----------------|
| `{module}:{id}` | Entity JSON | 15 min | Update/delete |
| `bloom:{module}:{field}` | Bloom filter | Persistent | Never |

### 9.3 Pagination

- Default page size: 20
- Max page size: 100 (enforce in use case)
- Use MongoDB skip/limit with indexed sort field; switch to keyset (`_id`/`created_at` cursor) if this collection can grow past a few hundred thousand documents or is queried at deep offsets

### 9.4 Universal Performance (see `design/references/performance-checklist.md`)

- **Performance baseline**: state expected RPS and P95/P99 latency target for this endpoint (§0 of the checklist) — mark `[PERF TARGET NEEDED]` if the SRS doesn't specify one
- **Transaction scope**: if any use case wraps a Mongo multi-document transaction, state that no HTTP/Kafka call happens inside it — Mongo transactions held open during a network round-trip are as costly as a SQL equivalent
- **Timeout**: every downstream call (Core Banking, other services) states connect/read/overall timeout; every retry states bound + backoff + jitter, and excludes 4xx/validation errors
- **Connection pools**: state the Mongo client pool size and any downstream HTTP client pool size, sized against expected pod count × per-pod pool ≤ downstream capacity
- **Concurrency**: state whether any goroutine fan-out this use case performs is bounded (a semaphore/worker-pool pattern), not one goroutine per item with no cap

---

## 10. Distributed & Async Design

> Full checklist: `design/references/distributed-systems-checklist.md`. Fill this section when
> this module crosses a service boundary, publishes/consumes a Kafka/queue message, runs work
> asynchronously, or calls an external system (Core Banking, payment gateway). If this module is
> a plain synchronous CRUD API with no external dependency, state
> "N/A — synchronous, single-service, no messaging" and skip to Test Plan.

### 10.1 Data Ownership & Consistency

- **Owner**: this module owns `[entity]` — no other service writes to its MongoDB collection directly
- **Source of truth**: [this service | Core Banking | another service] is authoritative for `[field]`
- **Consistency**: [STRONG | EVENTUAL] for `[operation]` — state the reason if STRONG

### 10.2 Async Boundary & Durability

- **Sync vs. async**: [this operation returns synchronously | this operation returns 202 and processes via Kafka topic `[topic]`]
- **Durability**: if async, the operation is persisted (outbox row / Kafka publish inside the DB transaction) before returning 202 — not a bare goroutine

### 10.3 Idempotency & Ordering

- **Idempotency key**: `[idempotencyKey field]` propagated from [client/API] through to [consumer/external call]
- **Duplicate handling**: consumer checks `alreadyProcessed(eventId)` before applying, marks processed in the same Mongo transaction as the business update
- **Ordering scope**: [Global | Tenant | Account | Aggregate] — partition key: `[field, e.g. accountId]`

### 10.4 State Machine (if this entity has a status field)

```text
[PENDING] → [PROCESSING] → [COMPLETED]
                ↓
           [RETRYING] → [FAILED]
```
Transitions validated in `[UseCase/Service method]` — never set directly by a consumer.

### 10.5 Failure Handling

- **Retry**: [bounded count] attempts, exponential backoff + jitter, retryable errors: `[list]`; non-retryable: `[list]`
- **DLQ**: topic `[topic].dlq`, carries `eventId, eventType, payload, retryCount, error, failedAt, correlationId`
- **Unknown result**: a timeout calling `[external system]` transitions this record to `UNKNOWN`, resolved via `[status-inquiry endpoint | reconciliation job]` — never directly to `FAILED`
- **Reconciliation**: [if financial/critical] `[job name]` compares `[fields]` against `[external system]` on `[schedule]`

---

## 11. Test Plan

### 11.1 Use Case Unit Tests

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `TestGet_Success` | Valid ID | Returns entity |
| `TestGet_NotFound` | Invalid ID | ErrNotFound |
| `TestCreate_Success` | Valid input | Returns created entity |
| `TestCreate_Conflict` | Duplicate field | ErrConflict |

### 11.2 Handler Integration Tests (fiber.Test())

| Test Case | Endpoint | Auth | Expected Status |
|-----------|----------|------|----------------|
| GET success | GET /:id | Valid JWT | 200 OK |
| GET not found | GET /invalid-id | Valid JWT | 404 Not Found |
| GET no auth | GET /:id | None | 401 Unauthorized |
| POST create | POST / | Admin JWT | 201 Created |
| POST conflict | POST / | Admin JWT | 409 Conflict |
| POST validation | POST / | Admin JWT | 400 Bad Request |

### 11.3 SRS Traceability

| SRS Requirement | Implemented In |
|----------------|---------------|
| FR-01: [requirement] | UseCase: [name], API: [endpoint] |
| FR-02: [requirement] | Entity field: [field] |
| BR-01: [business rule] | UseCase validation logic |
```

---

## NAMING CONVENTIONS (MODE B)

Discover exact conventions from CLAUDE.md — below are typical patterns:

- SDS path: Glob `docs/*/sds/` or `docs/04-sds/` → compute next M-XX
- Module ID: `M-XX` (project-specific numbering)
- Module name: lowercase, hyphen-separated
- Go package: match directory name
- Entity: PascalCase
- Use case file: `{action}_{entity}_usecase.go`
- Handler: `{entity}_handler.go`
- Repository impl: `{db}_{entity}_repository.go`

---

## CLEAN ARCHITECTURE RULES (MODE B)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|---------------|
| Domain | stdlib only | Fiber, MongoDB, Redis, infrastructure |
| Usecase | Domain interfaces | HTTP, DB implementations |
| Adapter | Domain, Usecase | Business logic, DB directly |
| Infrastructure | Domain interfaces | Usecase layer |

**Entity Design:**
- Pure Go structs, no framework annotations
- `bson` tags for MongoDB (acceptable in entity for simplicity)
- No methods with side effects in domain entities
- `CreatedAt`, `UpdatedAt` fields required

**Use Case Pattern:**
```go
// Every use case: single struct, single Execute method
func (uc *XxxUseCase) Execute(
    ctx context.Context,
    input *XxxInput,
    meta RequestMeta,
) (*XxxOutput, error)
```

**SDS Traceability Comment (required):**
```go
// Traceability: SDS M-XX Section Y.Z [Use Case Name]
func (uc *LoginUseCase) Execute(...) { ... }
```

**SDS Design Principle:**
Design from the domain (Entity) outward → don't design API-first and only think about the Entity afterward.
