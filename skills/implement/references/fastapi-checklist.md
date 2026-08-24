# Implement Skill — FastAPI Reference Material

> Load this when implementing in a FastAPI (Python) codebase. It complements
> `verification-checklist.md` — that file's language-agnostic checklist (linting, testing,
> secrets scan, docs) still applies; this file adds the traps specific to this stack. It does not
> restate `design/references/security-checklist.md` or `performance-checklist.md` — only what's
> particular to FastAPI/Pydantic/SQLAlchemy.
>
> **First, verify the Pydantic major version** (`pyproject.toml`/`requirements.txt`). Pydantic v2
> renamed `@validator` → `@field_validator`, `orm_mode` → `from_attributes`, and `.dict()`/`.json()`
> → `.model_dump()`/`.model_dump_json()`. Writing v1-shaped code against a v2 project (or vice
> versa) from training-data memory produces an import/attribute error, not a compile error —
> check the version before writing the first schema.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ Returning the SQLAlchemy model directly from a route

```python
@router.get("/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await session.get(User, user_id)
    return user
    # leaks every column (including password_hash), couples the API contract
    # to the DB schema, and FastAPI has to guess how to serialize relationships
```

### ✅ Mapping to a Pydantic response schema

```python
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    user = await service.get_user(user_id)  # raises UserNotFoundError -> 404 handler
    return UserResponse.model_validate(user)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    created_at: datetime
```

**Why this is better:** the response shape is explicit and stable regardless of what columns get
added to the model later, sensitive fields (`password_hash`) have no path to the wire, and
`response_model=` gives FastAPI a contract to validate against instead of guessing.

---

### ❌ A blocking call inside `async def`

```python
@router.post("/notify")
async def notify_user(payload: NotifyRequest):
    # requests is synchronous — this blocks the ENTIRE event loop, stalling
    # every other in-flight request on this worker, not just this one
    requests.post("https://sms-provider.example/send", json=payload.model_dump())
    return {"status": "sent"}
```

### ✅ An async-capable client, or explicit offload for sync work

```python
@router.post("/notify")
async def notify_user(
    payload: NotifyRequest,
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    await http_client.post("https://sms-provider.example/send", json=payload.model_dump())
    return {"status": "sent"}

# if the only available client is sync (legacy SDK, CPU-heavy work), offload explicitly —
# don't just call it inline and hope:
from starlette.concurrency import run_in_threadpool

result = await run_in_threadpool(legacy_sync_sdk.send, payload)
```

**Why this is better:** `httpx.AsyncClient` actually yields control back to the event loop during
I/O wait; when only a sync client exists, `run_in_threadpool` moves the blocking call off the
event loop instead of stalling every concurrent request on that worker process.

---

### ❌ Constructing the service/repository inline, with no `Depends()`

```python
@router.get("/{order_id}")
async def get_order(order_id: int, session: AsyncSession = Depends(get_db)):
    repo = OrderRepository(session)          # hardcoded — a test can't substitute a fake
    service = OrderService(repo)
    return await service.get_order(order_id)
```

### ✅ Injected via `Depends()`

```python
def get_order_repository(session: AsyncSession = Depends(get_db)) -> OrderRepository:
    return OrderRepository(session)

def get_order_service(repo: OrderRepository = Depends(get_order_repository)) -> OrderService:
    return OrderService(repo)

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
):
    order = await service.get_order(order_id)
    return OrderResponse.model_validate(order)
```

**Why this is better:** a test overrides `app.dependency_overrides[get_order_service]` with a
fake that returns canned data — no real DB connection needed for a router unit test. Constructing
the service inline makes that override impossible.

---

### ❌ `BackgroundTasks` for something that must survive a crash

```python
@router.post("/orders/{order_id}/confirm")
async def confirm_order(order_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_confirmation_email, order_id)
    # if the process restarts/crashes between response and task execution,
    # this email is silently lost — no retry, no record it was ever queued
    return {"status": "confirmed"}
```

### ✅ A durable queue/persisted job for anything that must complete

```python
@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
):
    await service.confirm_order(order_id)  # persists a job row / publishes to a queue
    # inside the same DB transaction as the order state change — not a bare in-memory task
    return {"status": "confirmed"}
```

**Why this is better:** `BackgroundTasks` runs in-process, in memory, after the response is sent —
it has no persistence and no retry. Anything that must actually happen (email receipts, payment
webhooks, audit writes) needs a durable queue (Celery/RQ/Arq job, outbox table + worker) so a
crash between "task scheduled" and "task ran" doesn't silently drop the work. `BackgroundTasks` is
fine only for best-effort, non-critical work (e.g. cache warming) where losing it occasionally is acceptable.

---

### ❌ Pydantic v1-vs-v2 API drift

```python
# v1-shaped code written against a v2 project — raises at import/runtime, not a clean error
class UserResponse(BaseModel):
    class Config:
        orm_mode = True          # v2: `model_config = ConfigDict(from_attributes=True)`

    @validator("email")          # v2: `@field_validator("email")`
    def check_email(cls, v):
        return v.lower()

user_dict = user_response.dict()  # v2: `.model_dump()`
```

### ✅ Pydantic v2 API

```python
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return v.lower()

user_dict = user_response.model_dump()
```

**Why this is better:** matches the installed version's actual API — check `pyproject.toml`
first; don't assume v1 or v2 from memory. Mixed v1/v2 syntax fails at runtime/import time, not
at review time.

---

### ❌ Session lifecycle mistakes with the async engine

```python
# a session created once at module scope and reused across requests —
# not safe for concurrent requests, and state leaks between them
db_session = AsyncSession(engine)

@router.get("/{id}")
async def get_item(id: int):
    return await db_session.get(Item, id)
```

### ✅ Session scoped per-request via `Depends()`

```python
# app/core/database.py
async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
        # session closes automatically at request end, even on exception

@router.get("/{id}", response_model=ItemResponse)
async def get_item(id: int, session: AsyncSession = Depends(get_db)):
    item = await session.get(Item, id)
    ...
```

**Why this is better:** each request gets its own session with its own transaction/identity map
— no cross-request state leakage, no "attached to a closed session" errors from reusing an
instance across an `await` boundary that a *different* request's session commit/rollback already
touched.

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — FastAPI specifics slot in as follows:

### **P0 - Critical**
- Every route has an explicit `response_model=` (or return type mapped to a Pydantic schema) —
  no SQLAlchemy model ever serialized directly to a client
- Every non-public endpoint has an explicit auth dependency (`Depends(get_current_user)` or a
  role-checking dependency) — verified by reading the dependency, not assumed from the route name
- No blocking call (sync DB driver, `requests`, unguarded CPU-heavy loop) inside an `async def`
  route or service method
- No SQL built via raw string interpolation — SQLAlchemy's `select()`/bound parameters only

### **P1 - High**
- Repository/service constructed via `Depends()` chain, not instantiated inline in the route —
  tests must be able to override with `app.dependency_overrides`
- Exception → HTTP status mapping via registered `@app.exception_handler(...)` or consistent
  `HTTPException` raises, not ad-hoc `try/except` duplicated per route
- `created_at`/`updated_at` populated via `server_default`/`onupdate` at the DB layer, not
  inconsistently in application code across features

### **P2 - Medium**
- Service-layer unit tests with the repository mocked (`unittest.mock.AsyncMock` or a fake)
- Router integration tests via `TestClient`/`httpx.AsyncClient` against the FastAPI app
- Docstrings/comments on non-obvious business rules

### **P3 - Low**
- `selectinload()`/`joinedload()` tuning to eliminate N+1 on list endpoints
- Response caching for hot read paths

---

## VERIFICATION CHECKLIST (FastAPI additions)

Run these in addition to the general checklist:

### 1. Code Quality
```bash
ruff check .              # or: flake8 / pylint, whichever this project uses
mypy app/                 # if type-checked
```
- [ ] Pydantic API usage matches the installed major version (`@field_validator` vs `@validator`,
  `from_attributes` vs `orm_mode`, `.model_dump()` vs `.dict()`) — check `pyproject.toml` if unsure

### 2. Correctness
- [ ] Every route declares `response_model=` and never returns a SQLAlchemy instance directly
- [ ] Every `Depends()` chain (repository → service → router) resolves without a route
  instantiating a class inline
- [ ] Every request schema validates all required fields — no field silently defaulted that the
  SRS/SDS required as mandatory

### 3. Security
- [ ] Every non-public endpoint has an explicit auth dependency — verified by reading the actual
  `Depends(...)`, not assumed from the endpoint's name
- [ ] Every endpoint taking a resource id also checks ownership in the service layer, not just
  authentication — IDOR check, not just an authentication check
- [ ] No sensitive field (password hash, token, internal notes) present on any `*Response` schema
- [ ] No query built via f-string/`.format()`/`%` interpolation with a variable — `select()` or
  bound `:param` only
- [ ] A read-modify-write on balance/payment/approval matches the locking strategy the SDS named
  (`SELECT ... FOR UPDATE`, `version_id_col`, or explicit row lock) — not a bare read-then-write
- [ ] Auth/OTP/payment endpoints have a rate-limit dependency/middleware applied if the SDS specified one
- [ ] A registered exception handler's catch-all never lets a SQLAlchemy/driver error message or
  stack trace reach the client — verify with a test that intentionally triggers an uncaught exception

```bash
git grep -iE "(password|secret|api_key|token)\s*=" -- '*.py'
git grep -inE "(text\(f[\"']|\.format\(.*SELECT|% \(.*\).*SELECT)" -- '*.py'
```

### 4. Testing
```bash
pytest
```
- [ ] Service tests mock the repository (`AsyncMock(spec=Repository)`), not a real DB
- [ ] Router tests use `TestClient`/`httpx.AsyncClient` with `app.dependency_overrides` set for
  auth/service, covering: success, validation failure (422), missing auth (401), insufficient
  role (403), IDOR (authenticated user requesting another user's resource id → 403/404)
- [ ] Async tests use `pytest-asyncio` (or equivalent) — a sync `def test_...` calling `async def`
  code without awaiting it silently passes without ever running the coroutine

### 5. Performance
- [ ] List endpoints that render a relationship use `selectinload()`/`joinedload()` explicitly —
  not a loop that lazy-loads the relation per row
- [ ] Unbounded list endpoints paginate (`page`/`page_size` with an enforced max), not `SELECT *`
  with no limit
- [ ] No service method awaits a blocking/sync call (sync DB driver, `requests`, unguarded
  CPU-bound loop) inside an `async def` — read the actual body, not just the signature
- [ ] `httpx.AsyncClient`/external client config has an explicit connect/read timeout — not the
  library default (no timeout at all, for some clients)
- [ ] Async engine's `pool_size`/`max_overflow` is explicit config, not left at the driver default

```bash
# blocking-call-in-async-def candidates
grep -n "async def" -- '*.py' | cut -d: -f1 | sort -u | xargs grep -n "requests\.\|time\.sleep("
```

### 6. Distributed & Async (if this module publishes/consumes queue messages or calls an external system)
- [ ] `BackgroundTasks` is not used for a business-critical operation that must survive a crash —
  a durable queue (Celery/RQ/Arq) or persisted job row backs it instead
- [ ] Every consumer/worker checks a `processed_events` table (or equivalent) for the event id
  before applying the effect, and marks it processed in the same DB transaction as the business update
- [ ] A DB write that must be atomic with a queue publish goes through an outbox table in the same
  transaction, not an inline publish call outside it
- [ ] Any entity with a status field is only mutated through a transition method — grep for
  direct `.status = ` assignment from outside the service/state-machine module
- [ ] A timeout calling an external system (payment gateway, another service) sets the record to
  `UNKNOWN`/`PENDING`, never directly to a terminal failure state

```bash
grep -rn "BackgroundTasks" -- '*.py'
grep -n "\.status = " -- '*.py'
```

---

## TROUBLESHOOTING

**`AttributeError: 'X' object has no attribute 'dict'` (or `.orm_mode`, `@validator`):**
The code was written for the wrong Pydantic major version. Check `pyproject.toml`/
`requirements.txt` for `pydantic` version — v2 renamed `.dict()` → `.model_dump()`,
`orm_mode` → `from_attributes`, `@validator` → `@field_validator`.

**Requests pile up / the whole app feels frozen under load, even on unrelated endpoints:**
A blocking call is sitting inside an `async def` somewhere on the hot path — a sync DB driver, a
`requests.get(...)`, or a CPU-heavy loop with no `run_in_threadpool`/offload. It stalls the entire
event loop, not just the request that made the call. Grep for sync HTTP clients and sync DB
drivers inside `async def` functions.

**`sqlalchemy.exc.InvalidRequestError` / "This session is already flushing" / detached instance errors:**
Usually a session held longer than one request (module-level session, or a session object passed
across a background task or `await` boundary it wasn't scoped for). Confirm sessions are created
per-request via the `Depends(get_db)` generator, not shared.

**A test passes with `TestClient` but the real deployment behaves differently under concurrency:**
`TestClient` runs the app synchronously against ASGI in-process; it won't surface event-loop
starvation from a blocking call. Verify async behavior with a real async client
(`httpx.AsyncClient` against a running server) or a load test, not just `TestClient`.

**Tests pass individually but fail when run together:**
Check for a shared session/engine fixture without proper per-test isolation (e.g. missing
transaction rollback between tests, or a module-scoped fixture that should be function-scoped).
