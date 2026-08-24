# Implement Skill — Rust (Axum/Actix) Reference Material

> Load this when implementing in a Rust codebase. It complements `verification-checklist.md` —
> that file's language-agnostic checklist (linting, testing, secrets scan, docs) still applies;
> this file adds the traps specific to this stack. It also complements
> `security-implementation-checklist.md`/`performance-implementation-checklist.md` — those cover
> the universal items (input validation, timeouts, connection pools); this file covers only what's
> Rust-specific: the compiler-enforced guarantees Rust gives you, and the ways implementation code
> throws them away.
>
> **First, confirm the web framework and async runtime** (`Cargo.toml`): Axum or Actix-web, and
> tokio (almost always — Actix-web ships its own runtime built on tokio). Axum extractors
> (`State`, `Path`, `Json`) and Actix-web's (`web::Data`, `web::Path`, `web::Json`) are not
> interchangeable — writing one framework's handler signature against the other's imports produces
> code that doesn't compile, not a runtime bug. Also confirm the edition (`edition = "2021"` vs
> `"2024"` in `[package]`) — `gen`/`dyn*` and a few `std` items differ across the boundary.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ `.unwrap()`/`panic!` on a normal, expected failure

```rust
pub async fn get_order(State(pool): State<PgPool>, Path(id): Path<Uuid>) -> Json<OrderResponse> {
    let row = sqlx::query_as::<_, OrderRow>("SELECT * FROM orders WHERE id = $1")
        .bind(id)
        .fetch_one(&pool)
        .await
        .unwrap(); // a missing order is a normal client mistake (bad id), not a bug —
                   // this panics the request instead of returning 404
    Json(row.into())
}
```

### ✅ Typed `Result` propagated to a mapped HTTP response

```rust
pub async fn get_order(
    State(pool): State<PgPool>,
    Path(id): Path<Uuid>,
) -> Result<Json<OrderResponse>, ApiError> {
    let row = sqlx::query_as::<_, OrderRow>("SELECT * FROM orders WHERE id = $1")
        .bind(id)
        .fetch_optional(&pool)
        .await
        .map_err(|e| ApiError::from(OrderError::from(e)))?
        .ok_or(ApiError::from(OrderError::NotFound(id)))?;
    Ok(Json(row.into()))
}
```

**Why this is better:** a missing row, a malformed request body, or a duplicate key are outcomes
the caller *causes* and the API must answer for — a `Result` that reaches the HTTP layer's error
mapping turns that into a 404/409/400. `.unwrap()`/`.expect()`/`panic!` are for states that must
never happen if the code is correct (a `main()` startup misconfiguration, an internal invariant a
test would catch) — using them for "the database didn't have this row" turns a routine client
error into a crashed worker thread and, on Actix-web's actor-per-worker model or a panic that
escapes a tokio task, either a dropped connection or (with `catch_unwind` middleware) an opaque
500 with the real cause visible only in the panic log, not the response.

---

### ❌ `anyhow`/`Box<dyn Error>` crossing the domain/application boundary

```rust
// application/create_order.rs
pub async fn execute(repo: &dyn OrderRepo, input: CreateOrderInput) -> anyhow::Result<Order> {
    if repo.exists(&input.sku).await? {
        anyhow::bail!("order already exists"); // caller can only match on a string now
    }
    // ...
}

// infrastructure/http handler
match create_order::execute(repo, input).await {
    Ok(order) => Ok(Json(order.into())),
    Err(e) => {
        // every failure — conflict, DB down, invalid input — becomes the same 500;
        // there is no typed variant left to match on to pick 409 vs 400 vs 500
        Err(ApiError::Internal(e.to_string()))
    }
}
```

### ✅ Typed error enum at the boundary, `anyhow` only at the outermost edge

```rust
// domain/errors.rs
#[derive(Debug, thiserror::Error)]
pub enum OrderError {
    #[error("order for sku {0} already exists")]
    Conflict(String),
    #[error("invalid input: {0}")]
    InvalidInput(String),
    #[error("repository error")]
    Repo(#[source] sqlx::Error),
}

// application/create_order.rs
pub async fn execute(repo: &dyn OrderRepo, input: CreateOrderInput) -> Result<Order, OrderError> {
    if repo.exists(&input.sku).await.map_err(OrderError::Repo)? {
        return Err(OrderError::Conflict(input.sku));
    }
    // ...
}

// infrastructure/http/error.rs — the ONE place this converts to a status code
impl From<OrderError> for ApiError {
    fn from(e: OrderError) -> Self {
        match e {
            OrderError::Conflict(_) => ApiError::Status(StatusCode::CONFLICT, e.to_string()),
            OrderError::InvalidInput(_) => ApiError::Status(StatusCode::BAD_REQUEST, e.to_string()),
            OrderError::Repo(_) => ApiError::Status(StatusCode::INTERNAL_SERVER_ERROR, "internal error".into()),
        }
    }
}
```

**Why this is better:** `anyhow::Error`/`Box<dyn Error>` erase the failure's identity — a caller
can `.to_string()` it or `.downcast()` (fragile, easy to get wrong) but can't cleanly `match` on
"is this a conflict or a genuine outage." A `thiserror` enum keeps that identity all the way to
the one place — the HTTP adapter — that's allowed to collapse it into a status code. `anyhow` is
still fine at the true outer edge: `main()`'s `-> anyhow::Result<()>`, or a CLI tool with no caller
to hand a typed error back to.

---

### ❌ A web-framework type leaking into a domain struct

```rust
// domain/order.rs — supposedly framework-free
pub struct Order {
    pub id: Uuid,
    pub state: axum::extract::State<AppState>, // domain now depends on axum; won't
                                                 // compile without the web framework,
                                                 // can't be constructed in a unit test
    pub claims: actix_web::HttpRequest,         // same problem from the other framework
}
```

### ✅ Domain stays plain; the adapter does the translating

```rust
// domain/order.rs — compiles with `cargo check -p domain`, no web framework in the dep tree
pub struct Order {
    pub id: OrderId,
    pub sku: String,
    pub status: OrderStatus,
}

// infrastructure/http/order.rs — the adapter extracts what it needs and passes plain values in
pub async fn create_order(
    State(repo): State<Arc<dyn OrderRepo>>,
    Json(req): Json<CreateOrderRequest>,
) -> Result<Json<OrderResponse>, ApiError> {
    let input = CreateOrderInput { sku: req.sku }; // plain struct, no axum type inside it
    let order = create_order::execute(repo.as_ref(), input).await?;
    Ok(Json(order.into()))
}
```

**Why this is better:** the same test that verifies `domain`/`application` compile without axum or
actix-web (`cargo check -p domain`) catches this immediately if it's set up — but only if nothing
in `domain` ever imports the framework in the first place. A domain struct that can't be
constructed without an `HttpRequest`/`axum::extract::State` can't be unit-tested without spinning
up the framework, which defeats the entire reason for the domain/application/infrastructure split.

---

### ❌ Blocking call inside an `async fn` stalls the runtime

```rust
pub async fn export_report(State(pool): State<PgPool>) -> Result<Vec<u8>, ApiError> {
    let rows = fetch_rows(&pool).await?;
    let csv = std::fs::read_to_string("/templates/report.csv")?; // sync file I/O —
                                                                   // blocks this worker thread
    let report = build_report(rows, &csv); // if this is CPU-heavy, same problem
    Ok(report)
}
```

### ✅ Blocking work moved off the async worker thread

```rust
pub async fn export_report(State(pool): State<PgPool>) -> Result<Vec<u8>, ApiError> {
    let rows = fetch_rows(&pool).await?;
    let report = tokio::task::spawn_blocking(move || {
        let csv = std::fs::read_to_string("/templates/report.csv")?; // fine here — this
        Ok::<_, std::io::Error>(build_report(rows, &csv))            // runs on the blocking
    })                                                                // thread pool, not a
    .await
    .map_err(|_| ApiError::Internal("report task panicked".into()))??;
    Ok(report)
}
```

**Why this is better:** tokio schedules many `.await`-yielding tasks cooperatively onto a small
worker-thread pool. A sync call that never yields (blocking file/socket I/O, a tight CPU loop, a
non-async DB driver call, a `std::sync::Mutex` held across a network call) occupies its worker
thread for the whole call — every *other* task scheduled on that thread stalls too, not just the
one that made the blocking call. This is the async-runtime equivalent of a Go handler that blocks
a goroutine without a reason, except the blast radius is worse: Go's scheduler can usually spin up
another OS thread, tokio's default runtime has a fixed worker pool sized to the CPU count.
`spawn_blocking` hands the work to a separate, larger thread pool meant exactly for this.

---

### ❌ Missing `Send + Sync` papered over with `unsafe`

```rust
pub trait OrderRepo {                    // no Send + Sync bound
    fn find_by_id(&self, id: Uuid) -> BoxFuture<'_, Option<Order>>;
}

// the trait object won't compile as Arc<dyn OrderRepo> shared across axum's worker threads,
// so instead of adding the bound, the compile error gets "fixed" like this:
unsafe impl Send for OrderRepoImpl {}
unsafe impl Sync for OrderRepoImpl {} // now the compiler can't catch a real data race —
                                       // this is a promise to the compiler, not a fact
```

### ✅ Bound the trait so the compiler proves thread-safety for you

```rust
#[async_trait::async_trait]
pub trait OrderRepo: Send + Sync {
    async fn find_by_id(&self, id: Uuid) -> Result<Option<Order>, OrderError>;
}
// Arc<dyn OrderRepo> now shares safely across axum/Actix-web worker threads because every
// implementor is required to actually be Send + Sync — sqlx::PgPool and diesel's pooled
// connections already are, so the bound costs nothing for a normal DB-backed implementation
```

**Why this is better:** `unsafe impl Send`/`Sync` is a manual assertion that a type is safe to
share/move across threads — correct only if every field genuinely is, and the compiler no longer
checks it for you once you've written it. The right fix is almost always adding `Send + Sync` to
the trait/generic bound so non-thread-safe implementations fail to compile *before* they reach
production, rather than reaching for `unsafe` to silence an error that's telling you something
true. Reach for `unsafe` here only with a specific, documented reason (e.g. wrapping a verified-safe
FFI type) — never as a generic "make the compiler stop complaining" move.

---

### ❌ Unbounded `tokio::spawn` fan-out per request

```rust
pub async fn bulk_notify(Json(req): Json<BulkNotifyRequest>) -> Result<(), ApiError> {
    for recipient in req.recipient_ids {          // caller-controlled length —
        tokio::spawn(send_notification(recipient)); // one request with 100k ids spawns
    }                                                // 100k tasks with no cap
    Ok(())
}
```

### ✅ Bounded concurrency via a semaphore

```rust
pub async fn bulk_notify(Json(req): Json<BulkNotifyRequest>) -> Result<(), ApiError> {
    let semaphore = Arc::new(Semaphore::new(20)); // at most 20 concurrent sends
    let mut set = JoinSet::new();
    for recipient in req.recipient_ids {
        let permit = semaphore.clone().acquire_owned().await.unwrap(); // Semaphore::acquire_owned
        set.spawn(async move {                                        // only errors if closed —
            let _permit = permit;                                     // acceptable unwrap
            send_notification(recipient).await
        });
    }
    while set.join_next().await.is_some() {}
    Ok(())
}
```

**Why this is better:** an unbounded `tokio::spawn` per item in a caller-controlled collection lets
one large request exhaust the runtime's task queue, memory, or a downstream service's connection
limit — the same shape as an unbounded goroutine-per-item loop in Go, or an unbounded thread pool
in Java. A `Semaphore`/bounded channel caps concurrent in-flight work regardless of how large the
input collection is, and `JoinSet` gives a place to observe each task's failure instead of a
fire-and-forget `tokio::spawn` whose panic silently vanishes.

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — Rust specifics slot in as follows:

### **P0 - Critical**
- No `.unwrap()`/`.expect()`/`panic!` on a fallible operation that's a normal, expected outcome
  (missing row, malformed input, duplicate key) in request-handling code — only in `main()` at
  startup or in `#[test]` code
- Typed error enum (`thiserror`) at every domain/application boundary — no bare
  `anyhow::Error`/`Box<dyn Error>` a caller would need to `.downcast()` to react to
- No `axum`/`actix-web`/`sqlx`/`diesel` type in a `domain` struct, enum, or trait signature
- Every blocking call (sync file I/O, a non-async crate, a CPU-heavy loop) inside an `async fn`
  is moved to `tokio::task::spawn_blocking` — verified by reading the actual function body, not
  assumed from the `async` keyword

### **P1 - High**
- Port traits used as `Arc<dyn Trait>` across threads/await points carry `Send + Sync` — no
  `unsafe impl Send`/`Sync` added to work around a missing bound
- Any `tokio::spawn`/task fan-out over a caller-controlled collection is bounded (`Semaphore`,
  bounded channel, or a sized `JoinSet`) — never one task per item with no cap
- Domain error → HTTP status mapping lives in one place (`infrastructure/http/error.rs` or
  equivalent), not scattered `match`es duplicated per handler

### **P2 - Medium**
- Unit tests assert the specific `Result` error *variant* returned (`assert!(matches!(err,
  OrderError::Conflict(_)))`), not just `is_err()` — a test that only checks "it failed" doesn't
  catch a 409 silently becoming a 500 the next time someone edits the match arms
- `cargo clippy -- -D warnings` clean (clippy catches several of the above automatically:
  `unwrap_used`, `expect_used`, `large_enum_variant`)

### **P3 - Low**
- `cargo fmt --check` clean
- Workspace crate split (if used) reflects the actual bounded-context boundaries, not left as an
  arbitrary split that doesn't match how the code changes together

---

## VERIFICATION CHECKLIST (Rust additions)

Run these in addition to the general checklist:

### 1. Code Quality
```bash
cargo check --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --check
```
- [ ] `domain` (and `application`, if split into its own crate) compiles standalone:
      `cargo check -p domain` with no `axum`/`actix-web`/`sqlx`/`diesel` in its `Cargo.toml`

### 2. Correctness
```bash
# unwrap/expect/panic outside main()/tests — inspect each hit, not every one is wrong
git grep -nE '\.unwrap\(\)|\.expect\(|panic!\(' -- '*.rs' | grep -v -E 'fn main|#\[test\]|tests/|_test.rs'

# anyhow/Box<dyn Error> reaching into domain or application modules
git grep -nE 'anyhow::(Error|Result)|Box<dyn( std::error::)?Error' -- 'src/domain/*.rs' 'src/application/*.rs'

# a web-framework or DB-driver import inside domain
git grep -nE '^use (axum|actix_web|sqlx|diesel)::' -- 'src/domain/*.rs'
```
- [ ] Every `Result` returned from `domain`/`application` uses a typed error enum, not
      `anyhow`/`Box<dyn Error>`
- [ ] Every handler maps its `Result`'s `Err` through the central `ApiError`/status mapping, never
      an ad-hoc `Err(...).to_string()` embedded directly in a response body

### 3. Async & Concurrency
```bash
# blocking-call candidates inside async fn — inspect each; not every hit is a real stall
git grep -nE 'std::fs::|std::thread::sleep|\.lock\(\)' -- '*.rs' | grep -B2 'async fn'

# unbounded spawn over a loop
git grep -n 'tokio::spawn' -- '*.rs' | grep -B3 'for '

# unsafe Send/Sync impls — each one needs a specific justification comment, not a blanket fix
git grep -n 'unsafe impl \(Send\|Sync\)' -- '*.rs'
```
- [ ] No blocking call runs directly on an async worker thread — wrapped in `spawn_blocking` or
      swapped for an async-native equivalent (`tokio::fs`, an async DB driver)
- [ ] No `unsafe impl Send`/`Sync` was added to silence a compile error — the actual fix is either
      a genuinely `Send + Sync` type or a bound added to the trait/generic
- [ ] Every task-fan-out over a caller-controlled collection (batch request, bulk import) has an
      explicit concurrency cap

### 4. Testing
```bash
cargo test --workspace
```
- [ ] Application-layer tests use a fake/mock implementation of the port trait, not a real DB
- [ ] Tests assert the specific error *variant*, not just `.is_err()`
- [ ] HTTP integration tests cover: success, not-found (404), conflict (409), validation failure
      (400), missing/invalid auth (401), IDOR (403/404)

### 5. Performance (Rust-specific only — see `performance-implementation-checklist.md` for the rest)
- [ ] `spawn_blocking` used for any blocking call identified in §3, not left inline
- [ ] Task fan-out bounded per §3 — no unbounded `tokio::spawn` in a loop over user-supplied input
- [ ] Connection pool (`sqlx::PgPool`/diesel) size is explicit config, not left at a library default

---

## TROUBLESHOOTING

**`error[E0277]: `... ` cannot be sent between threads safely`:**
Something non-`Send` (commonly a `Rc<RefCell<..>>`, a `std::sync::MutexGuard`, or a raw pointer) is
held across an `.await` point, or a trait object is missing a `Send + Sync` bound. Don't reach for
`unsafe impl Send` — restructure so the non-`Send` value is dropped before the `.await` (scope a
`MutexGuard` in a block, or clone the data you need out of it first), or switch the type to a
`Send`-safe equivalent (`Arc<tokio::sync::Mutex<..>>` instead of `Rc<RefCell<..>>`).

**Requests time out or the whole service feels "stuck" under moderate load:**
Look for a blocking call executed directly inside an `async fn` — sync file I/O, a non-async
crate's HTTP client, a tight CPU-bound loop, or a `std::sync::Mutex` held across an `.await`. One
such call occupies a tokio worker thread for its entire duration, and every other task scheduled on
that thread stalls with it — this reproduces as "everything is slow," not just the one endpoint
that has the blocking call, which is what makes it easy to misdiagnose as a database or network
issue instead.

**A background task's failure is never logged, and the effect it was supposed to have never
happens:**
A bare `tokio::spawn(fut)` with no `JoinHandle` awaited (or awaited but its `Result` ignored) drops
a panic or error silently. Either `.await` the `JoinHandle` and handle its `Result`, or use a
`JoinSet` that surfaces each task's outcome.

**A previously-passing build stopped compiling after adding a trait object (`Arc<dyn Trait>`)
shared with a spawned task:**
Add `Send + Sync` (and, if the trait has async methods via `#[async_trait]`, confirm the
`#[async_trait]` attribute itself is present on both the trait and every `impl`) rather than
downgrading to a non-shared reference or reaching for `unsafe`.

**`cargo clippy` flags `unwrap_used`/`expect_used` in code that "obviously" can't fail:**
Treat this as a prompt to make the invariant explicit rather than to `#[allow]` it away — either
the call really can fail (return a typed error) or the invariant should be encoded in the type
system (a newtype, an enum variant that makes the "impossible" state unrepresentable) so nothing
downstream has to trust a comment saying "this never happens."
