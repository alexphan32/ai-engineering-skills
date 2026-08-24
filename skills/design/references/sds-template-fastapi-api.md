# SDS Template F: Python / FastAPI REST API

> Reference for `design` skill — loaded on demand when creating MODE F SDS documents.

---

## TEMPLATE F: FastAPI REST API SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: {tech_stack — discover from CLAUDE.md or project config, e.g. FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL}

---

## 1. Module Overview

### 1.1 Description
[Describe what this module/feature does in the system]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Module Type**: [Core Domain / Supporting / Infrastructure]
**Scale Tier**: [Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed — one-line reason, see `.claude/skills/architecture/references/system-scale-checklist.md`]

### 1.3 Architecture Layer
```
app/
├── features/{feature}/
│   ├── router.py          # FastAPI endpoints — HTTP concern only
│   ├── service.py         # Business logic, orchestration, Depends()-injected
│   ├── repository.py      # The only place queries live
│   ├── schemas.py         # Pydantic request/response models
│   └── models.py          # SQLAlchemy ORM model(s) owned by this feature
├── core/
│   ├── database.py        # Async engine, session factory, get_db() dependency
│   ├── config.py          # Settings (env-driven)
│   └── security.py        # Auth dependency (JWT/OAuth2), shared across features
└── main.py                # App factory, router registration
```

**Note**: feature-organized (`app/features/{feature}/*.py`), NOT layer-organized
(`app/routers/` + `app/services/` + `app/models/` each holding every feature's files). A new
feature adds one new `app/features/{name}/` directory, never a new file scattered across three
top-level layer folders.

**Entities**: [List SQLAlchemy models]
**APIs**: [List main endpoints]
**Dependencies**: [M-01 IAM for auth, etc.]

---

## 2. Data Model

### 2.1 SQLAlchemy Model: [ModelName]

```python
# app/features/{feature}/models.py
# Traceability: SDS M-XX Section 2.1
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class [ModelName](Base):
    __tablename__ = "[table_name]"

    id: Mapped[int] = mapped_column(primary_key=True)
    [field]: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

**Field Definitions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | Yes | Primary key |
| [field] | str | Yes | [description] |
| active | bool | Yes | Soft delete flag |
| created_at | datetime (tz-aware) | Yes | Creation timestamp |
| updated_at | datetime (tz-aware) | Yes | Last update timestamp |

### 2.2 Migration Notes

- **Migration tool**: Alembic — `alembic revision --autogenerate -m "add_[table_name]"`
- **Backward compatibility**: [new column nullable/defaulted so existing rows don't break | N/A, new table]
- **Data backfill**: [required for field X, script at `scripts/backfill_[table].py` | N/A]

### 2.3 Indexing

| Index | Fields | Type | Reason |
|-------|--------|------|--------|
| `ix_[table]_[field]` | `[field]` | Unique | Frequent lookup |
| `ix_[table]_active_created` | `(active, created_at)` | Composite | List query with sort/filter |

```python
__table_args__ = (
    Index("ix_[table]_active_created", "active", "created_at"),
)
```

---

## 3. Repository Layer

> The only place SQLAlchemy queries live. Service layer never constructs a query directly.

```python
# app/features/{feature}/repository.py
# Traceability: SDS M-XX Section 3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.{feature}.models import [ModelName]


class [Entity]Repository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, entity_id: int) -> [ModelName] | None:
        result = await self._session.execute(
            select([ModelName]).where([ModelName].id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list(self, *, active: bool | None = None, page: int = 1, page_size: int = 20) -> list[[ModelName]]:
        stmt = select([ModelName])
        if active is not None:
            stmt = stmt.where([ModelName].active == active)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, entity: [ModelName]) -> [ModelName]:
        self._session.add(entity)
        await self._session.flush()
        return entity


def get_[entity]_repository(session: AsyncSession = Depends(get_db)) -> [Entity]Repository:
    return [Entity]Repository(session)
```

---

## 4. Service Layer

> Business logic and orchestration. Injected into routers via `Depends()` so tests can override
> it with a fake/mock. Never imports `fastapi.Request`/`Response` or a Pydantic *request* schema
> directly — it takes plain Python values/domain objects.

```python
# app/features/{feature}/service.py
# Traceability: SDS M-XX Section 4
from fastapi import Depends, HTTPException, status
from app.features.{feature}.repository import [Entity]Repository, get_[entity]_repository


class [Entity]Service:
    def __init__(self, repo: [Entity]Repository):
        self._repo = repo

    async def get_[entity](self, entity_id: int) -> [ModelName]:
        entity = await self._repo.get_by_id(entity_id)
        if entity is None:
            raise [Entity]NotFoundError(entity_id)
        return entity

    async def create_[entity](self, [field]: str) -> [ModelName]:
        # 1. Business rule validation
        # 2. Uniqueness check via repository
        # 3. Construct model, persist via repository
        # 4. Return created entity
        ...


def get_[entity]_service(repo: [Entity]Repository = Depends(get_[entity]_repository)) -> [Entity]Service:
    return [Entity]Service(repo)
```

### 4.1 Async-vs-Sync Boundary

State explicitly, per method, whether the work inside is genuinely non-blocking:

| Method | Calls made | Genuinely async? | Note |
|--------|-----------|-------------------|------|
| `get_[entity]` | SQLAlchemy async engine query | Yes | asyncpg/async driver, no blocking I/O |
| `create_[entity]` | repository insert + [external call, e.g. email send] | [Yes/No] | [if the external client is sync (e.g. `requests`, sync SMTP lib), it MUST run via `run_in_threadpool`/`anyio.to_thread.run_sync` — flag it here, don't leave it implicit] |
| `[method]` | [CPU-heavy work, e.g. image resize, PDF render] | No | offload via `run_in_threadpool` or a background worker — never inline in `async def` |

**[DESIGN DECISION]**: [name the specific driver/client for every external call this feature
makes — psycopg2 vs asyncpg, `requests` vs `httpx.AsyncClient` — a sync call inside `async def`
blocks the entire event loop, not just this request.]

---

## 5. Pydantic Schemas

> Explicitly separate from the SQLAlchemy model. A router never returns a SQLAlchemy instance
> directly — always maps through one of these.

```python
# app/features/{feature}/schemas.py
# Traceability: SDS M-XX Section 5
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Create[Entity]Request(BaseModel):
    [field]: str = Field(..., min_length=1, max_length=255)


class Update[Entity]Request(BaseModel):
    [field]: str | None = Field(None, min_length=1, max_length=255)


class [Entity]Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Pydantic v2 (was orm_mode in v1)

    id: int
    [field]: str
    created_at: datetime


class [Entity]ListResponse(BaseModel):
    data: list[[Entity]Response]
    page: int
    page_size: int
    total: int
```

**[DESIGN DECISION]**: `[Entity]Response` never exposes [internal-only field, e.g. `internal_notes`,
password hash] — the Pydantic response schema is the API contract; the SQLAlchemy model is the
storage shape, and the two are allowed to diverge.

---

## 6. API Specification

### 6.1 Endpoints Overview

| Method | Path | Auth | Request Schema | Response Schema | Status Codes |
|--------|------|------|-----------------|-------------------|---------------|
| GET | /api/v1/[resource] | Bearer JWT | - (query params) | `[Entity]ListResponse` | 200 |
| GET | /api/v1/[resource]/{id} | Bearer JWT | - | `[Entity]Response` | 200, 404 |
| POST | /api/v1/[resource] | Bearer JWT (role: [ROLE]) | `Create[Entity]Request` | `[Entity]Response` | 201, 400, 409 |
| PATCH | /api/v1/[resource]/{id} | Bearer JWT (role: [ROLE]) | `Update[Entity]Request` | `[Entity]Response` | 200, 400, 404 |

### 6.2 Router

```python
# app/features/{feature}/router.py
# Traceability: SDS M-XX Section 6
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from app.features.{feature}.service import [Entity]Service, get_[entity]_service
from app.features.{feature}.schemas import Create[Entity]Request, [Entity]Response, [Entity]ListResponse

router = APIRouter(prefix="/api/v1/[resource]", tags=["[resource]"])


@router.get("/{entity_id}", response_model=[Entity]Response)
async def get_[entity](
    entity_id: int,
    service: [Entity]Service = Depends(get_[entity]_service),
    user=Depends(get_current_user),
):
    entity = await service.get_[entity](entity_id)
    return [Entity]Response.model_validate(entity)


@router.post("/", response_model=[Entity]Response, status_code=status.HTTP_201_CREATED)
async def create_[entity](
    body: Create[Entity]Request,
    service: [Entity]Service = Depends(get_[entity]_service),
    user=Depends(get_current_user),
):
    entity = await service.create_[entity](body.[field])
    return [Entity]Response.model_validate(entity)
```

### 6.3 Endpoint Detail

#### GET /api/v1/[resource]/{id}
**Purpose**: [description]
**Auth**: Bearer JWT required (any authenticated user | role: [ROLE])
**Path Params**: `id: int`
**Response**: `[Entity]Response`
**Status**: 200 OK | 404 Not Found

#### POST /api/v1/[resource]
**Purpose**: [description]
**Auth**: Bearer JWT required, role: [ROLE]
**Request Body**: `Create[Entity]Request`
**Response**: `[Entity]Response`
**Status**: 201 Created | 400 Bad Request (validation) | 409 Conflict (duplicate)

---

## 7. Security Design

### 7.1 Authentication Requirements

| Endpoint | Auth | Role |
|----------|------|------|
| GET /api/v1/[resource] | Required (Bearer JWT) | Any |
| GET /api/v1/[resource]/{id} | Required (Bearer JWT) | Any (+ ownership check) |
| POST /api/v1/[resource] | Required (Bearer JWT) | [ROLE] |

### 7.2 Authorization Rules

```python
# app/core/security.py — reusable dependency
async def require_role(role: str):
    async def _check(user=Depends(get_current_user)):
        if user.role != role:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient permissions")
        return user
    return _check

# Ownership check — inside the service, not the router
if entity.owner_id != user.id and user.role != "admin":
    raise [Entity]ForbiddenError()
```

### 7.3 Data Security

- **Sensitive fields**: [fields] → never present on any `*Response` Pydantic schema
- **Input sanitization**: Pydantic validators trim/normalize (email, phone) at the schema boundary
- **SQL injection**: always use SQLAlchemy's `select(...).where(...)` parameterized construction —
  never `text(f"... {value}")` / raw string interpolation into a query
- **Rate limiting**: [middleware/gateway tier] — state the tier for auth/payment/search endpoints
  specifically, not just "rate limiting exists"

### 7.4 Universal Security (see `design/references/security-checklist.md`)

Apply the full checklist's `[MUST]` items; the ones most likely to be missed for a FastAPI feature:

- **Secrets**: DB credentials / JWT signing key from env var or secret manager (`pydantic-settings`
  reading `.env` in dev, real secret manager in prod) — never a literal in code or committed config
- **SQL injection**: confirm every query in `repository.py` uses SQLAlchemy's expression language
  or bound parameters — grep for `text(f"` / `.format(` / `%` string-building near a query
- **Business security**: for any state-changing endpoint touching balance/payment/approval, name
  the concurrency-control mechanism (`SELECT ... FOR UPDATE`, optimistic version column via
  SQLAlchemy `version_id_col`, or distributed lock) and, for transfers/payments, the idempotency
  mechanism (`Idempotency-Key` header)
- **Error handling**: confirm §8's exception handlers never let a SQLAlchemy/driver error message
  reach the client — internal detail goes to the log only
- **CORS/CSRF**: this API is Bearer-token auth — state that CSRF tokens aren't needed for that
  reason (not left implicit), and that `CORSMiddleware` is not configured with `allow_origins=["*"]`
  alongside `allow_credentials=True`
- **Security testing**: §11 must include unauthenticated, unauthorized/IDOR (fetch another user's
  resource by id), expired/invalid JWT, and rate-limit-exceeded cases

---

## 8. Error Handling

### 8.1 Exception → HTTP Status Mapping

```python
# app/features/{feature}/exceptions.py
class [Entity]NotFoundError(Exception):
    def __init__(self, entity_id: int):
        self.entity_id = entity_id

class [Entity]ConflictError(Exception):
    ...

# app/main.py — registered exception handlers, not per-route try/except
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler([Entity]NotFoundError)
async def not_found_handler(request: Request, exc: [Entity]NotFoundError):
    return JSONResponse(status_code=404, content={"detail": f"[entity] {exc.entity_id} not found"})

@app.exception_handler([Entity]ConflictError)
async def conflict_handler(request: Request, exc: [Entity]ConflictError):
    return JSONResponse(status_code=409, content={"detail": "[entity] already exists"})
```

Or, for a single call site, raise `HTTPException` directly:

```python
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="[entity] not found")
```

### 8.2 Error Code Mapping

| Exception | HTTP Status | Scenario |
|-----------|-------------|----------|
| `[Entity]NotFoundError` | 404 Not Found | Resource doesn't exist |
| `[Entity]ConflictError` | 409 Conflict | Duplicate entry |
| `RequestValidationError` (Pydantic) | 422 Unprocessable Entity | Schema validation failure — FastAPI's default |
| (auth dependency raises) | 401 Unauthorized | Missing/invalid JWT |
| (role check fails) | 403 Forbidden | Insufficient role / IDOR |

---

## 9. Performance Design

### 9.1 SQLAlchemy Indexing

| Index | Fields | Rationale |
|-------|--------|-----------|
| `ix_[table]_[field]` | `[field]` | Unique lookup |
| `ix_[table]_active_created` | `(active, created_at)` | List queries with filter + sort |

### 9.2 Pagination

- Default page size: 20
- Max page size: 100 (validated in `Query(le=100)` on the router or in the service)
- Offset pagination (`.offset().limit()`) for now; switch to keyset (`id`/`created_at` cursor) if
  this table can grow past a few hundred thousand rows or is queried at deep offsets

### 9.3 Connection Pool Sizing (async engine)

```python
# app/core/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=[N],       # steady-state connections per pod
    max_overflow=[N],    # burst allowance above pool_size
    pool_timeout=30,      # seconds to wait for a free connection
    pool_recycle=1800,    # avoid stale connections behind a load balancer/proxy
)
```

**[DESIGN DECISION]**: `pool_size` × expected pod count must stay under the DB's max connection
limit — state the arithmetic, don't leave the driver default unexamined.

### 9.4 Universal Performance (see `design/references/performance-checklist.md`)

- **Performance baseline**: state expected RPS and P95/P99 latency target for this endpoint
  (§0 of the checklist) — mark `[PERF TARGET NEEDED]` if the SRS doesn't specify one
- **N+1 avoidance**: any relationship this feature loads uses `selectinload()`/`joinedload()`
  explicitly — never lazy-loaded inside a loop over query results
- **Timeout**: every downstream call (`httpx.AsyncClient`, another service) states connect/read/
  overall timeout; every retry states bound + backoff + jitter, and excludes 4xx/validation errors
- **Concurrency**: state whether any `asyncio.gather()` fan-out this feature performs is bounded
  (a `Semaphore`), not unbounded concurrent tasks with no cap

---

## 10. Distributed & Async Design

> Full checklist: `design/references/distributed-systems-checklist.md`. Fill this section when
> this module crosses a service boundary, publishes/consumes a queue message, runs work via
> `BackgroundTasks`/a worker, or calls an external system. If this module is a plain synchronous
> CRUD API with no external dependency, state "N/A — synchronous, single-service, no messaging"
> and skip to Test Plan.

### 10.1 Data Ownership & Consistency

- **Owner**: this module owns `[entity]` — no other service writes to its table directly
- **Source of truth**: [this service | another service] is authoritative for `[field]`
- **Consistency**: [STRONG | EVENTUAL] for `[operation]` — state the reason if STRONG

### 10.2 Async Boundary & Durability

- **Sync vs. async**: [this operation returns synchronously | this operation returns 202 and
  processes via [queue/worker]]
- **Durability**: if deferred, the work is persisted to a durable queue/job table *before*
  returning 202 — `BackgroundTasks` alone does not survive a process crash/restart and must not
  be used for anything that must complete even if the pod dies mid-request

### 10.3 Idempotency & Ordering

- **Idempotency key**: `[idempotencyKey field]` propagated from [client/API] through to
  [consumer/external call]
- **Duplicate handling**: consumer checks an `already_processed(event_id)` table before applying,
  marks processed in the same DB transaction as the business update
- **Ordering scope**: [Global | Tenant | Account | Aggregate] — partition key: `[field]`

### 10.4 State Machine (if this entity has a status field)

```text
[PENDING] → [PROCESSING] → [COMPLETED]
                ↓
           [RETRYING] → [FAILED]
```
Transitions validated in `[Service method]` — never set directly by a router or consumer.

### 10.5 Failure Handling

- **Retry**: [bounded count] attempts, exponential backoff + jitter, retryable errors: `[list]`;
  non-retryable: `[list]`
- **DLQ**: `[topic/table].dlq`, carries `event_id, event_type, payload, retry_count, error, failed_at`
- **Unknown result**: a timeout calling `[external system]` transitions this record to `UNKNOWN`,
  resolved via `[status-inquiry endpoint | reconciliation job]` — never directly to `FAILED`

---

## 11. Test Plan

### 11.1 Service Unit Tests (mocked repository)

```python
# tests/features/{feature}/test_service.py
async def test_get_[entity]_success(mocker):
    repo = mocker.AsyncMock(spec=[Entity]Repository)
    repo.get_by_id.return_value = [ModelName](id=1, [field]="x")
    service = [Entity]Service(repo)
    result = await service.get_[entity](1)
    assert result.id == 1

async def test_get_[entity]_not_found(mocker):
    repo = mocker.AsyncMock(spec=[Entity]Repository)
    repo.get_by_id.return_value = None
    service = [Entity]Service(repo)
    with pytest.raises([Entity]NotFoundError):
        await service.get_[entity](999)
```

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `test_get_[entity]_success` | Valid id | Returns entity |
| `test_get_[entity]_not_found` | Invalid id | `[Entity]NotFoundError` |
| `test_create_[entity]_success` | Valid input | Returns created entity |
| `test_create_[entity]_conflict` | Duplicate field | `[Entity]ConflictError` |

### 11.2 Router Integration Tests (TestClient / httpx.AsyncClient)

```python
# tests/features/{feature}/test_router.py
async def test_get_[entity]_200(client, auth_headers):
    resp = await client.get("/api/v1/[resource]/1", headers=auth_headers)
    assert resp.status_code == 200

async def test_get_[entity]_401_no_auth(client):
    resp = await client.get("/api/v1/[resource]/1")
    assert resp.status_code == 401
```

| Test Case | Endpoint | Auth | Expected Status |
|-----------|----------|------|------------------|
| Get success | GET /{id} | Valid JWT | 200 |
| Get not found | GET /invalid-id | Valid JWT | 404 |
| Get no auth | GET /{id} | None | 401 |
| Get IDOR | GET /{other_user_id} | Valid JWT (not owner) | 403/404 |
| Create success | POST / | Role-valid JWT | 201 |
| Create conflict | POST / | Role-valid JWT | 409 |
| Create validation | POST / | Role-valid JWT | 422 |

### 11.3 SRS Traceability

| SRS Requirement | Implemented In |
|------------------|-----------------|
| FR-01: [requirement] | Service: `[method]`, API: `[endpoint]` |
| FR-02: [requirement] | Model field: `[field]` |
| BR-01: [business rule] | Service validation logic |
```

---

## 12. Design Decisions & Alternatives

| Decision | Alternative(s) Considered | Rationale |
|----------|---------------------------|-----------|
| [e.g. async SQLAlchemy engine over sync] | Sync `psycopg2` + threadpool | [why] |
| [e.g. feature-organized module layout] | Layer-organized (`routers/`, `services/`, `models/`) | Keeps a feature's files together; matches MODE F convention |

## 13. Risks & Trade-offs

- **[Risk]**: [description] — **Mitigation**: [approach]
- **[ASSUMPTION]**: [stated assumption, flagged for confirmation]

## 14. Implementation Mapping

| SDS Section | Implementation File(s) |
|--------------|--------------------------|
| §2 Data Model | `app/features/{feature}/models.py`, `alembic/versions/*` |
| §3 Repository | `app/features/{feature}/repository.py` |
| §4 Service | `app/features/{feature}/service.py` |
| §5 Schemas | `app/features/{feature}/schemas.py` |
| §6 API | `app/features/{feature}/router.py` |
| §11 Test Plan | `tests/features/{feature}/test_service.py`, `test_router.py` |

## 15. Implementation Readiness

**Gate**: [READY / PARTIALLY_READY / BLOCKED]

- [READY]: every FR traced, every endpoint's auth/schema/status codes specified, async-vs-sync
  boundary stated for every service method, no `[OPEN QUESTION]` left unresolved.
- [PARTIALLY_READY]: list exactly which sections are `[ASSUMPTION]`/`[NEEDS SPEC CLARIFICATION]`
  and which endpoints/tests can proceed regardless.
- [BLOCKED]: state the blocking `[OPEN QUESTION]` and who must answer it before `implement` starts.

---

## NAMING CONVENTIONS (MODE F)

Discover exact conventions from CLAUDE.md — below are typical patterns:

- SDS path: Glob `docs/*/sds/` or `docs/04-sds/` → compute next M-XX
- Module ID: `M-XX` (project-specific numbering)
- Feature directory: `app/features/{feature_name}/` — lowercase, snake_case
- SQLAlchemy model class: PascalCase (`Order`, `UserAccount`)
- Pydantic schema class: PascalCase + suffix (`CreateOrderRequest`, `OrderResponse`)
- Repository class: `{Entity}Repository`
- Service class: `{Entity}Service`
- Router prefix: `/api/v1/{resource}` (kebab/plural resource name)
- Test file: `tests/features/{feature}/test_{layer}.py`

---

## LAYERED ARCHITECTURE RULES (MODE F)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|----------------|
| `models.py` | SQLAlchemy, stdlib | FastAPI, Pydantic schemas, service/router |
| `repository.py` | SQLAlchemy, `models.py` | FastAPI, Pydantic schemas, service logic |
| `service.py` | `repository.py`, domain/business logic, stdlib | FastAPI request/response objects, Pydantic *request* schemas, raw SQLAlchemy queries |
| `schemas.py` | Pydantic, stdlib | SQLAlchemy models, service/repository |
| `router.py` | `service.py`, `schemas.py`, FastAPI | `repository.py`, SQLAlchemy directly |

**Model Design:**
- SQLAlchemy `Mapped[...]`/`mapped_column` declarative style, no framework annotations beyond ORM
- No business logic methods with side effects on the model itself — that belongs in `service.py`
- `created_at`/`updated_at` columns required (server-side default, not app-computed)

**Service Pattern:**
```python
# Every service method: plain async def, takes plain values, returns domain/ORM objects
async def create_[entity](self, [field]: str) -> [ModelName]:
    ...
```

**SDS Traceability Comment (required):**
```python
# Traceability: SDS M-XX Section Y.Z [Method Name]
async def create_[entity](self, ...): ...
```

**SDS Design Principle:**
Design from the data model (SQLAlchemy model) outward — Model → Repository → Service → Schema →
Router, in that order. Don't design the router first and only think about the model afterward;
never let a route return a SQLAlchemy instance directly — always map to a Pydantic response schema.
