# Operations Readiness Implementation Checklist

Load this whenever the code being implemented is a service/process deployed on its own (an API,
a worker, a consumer) — not a pure library or a static page. Design-time rationale lives in
`.claude/skills/design/references/operations-readiness-checklist.md` — this file verifies the code
actually wires up what was designed.

## Priority levels

Same convention as the other implementation checklists: **[MUST]** blocks completion, **[SHOULD]**
needs an explicit reason if skipped.

## 1. Health Endpoints Actually Differ [MUST]

```text
GET /health/live   → process responds at all (no dependency checks)
GET /health/ready   → checks the DB connection / required cache-queue connection is up
```

Verify these aren't the same handler, and that `/live` doesn't call out to the database — a
liveness check that depends on the DB turns one slow dependency into a full restart-loop across
every instance.

## 2. Graceful Shutdown Actually Wired [MUST for a consumer/worker process]

```go
sigCh := make(chan os.Signal, 1)
signal.Notify(sigCh, syscall.SIGTERM)
go func() {
    <-sigCh
    server.Shutdown(ctx)      // stop accepting new work, drain in-flight
    consumer.Stop()           // stop polling
    consumer.CommitOffsets()  // commit only after in-flight messages finish
    db.Close()
}()
```

Verify the process actually traps `SIGTERM` (not just relies on the orchestrator's default
SIGKILL-after-timeout) and that the drain step has a bounded timeout — an unbounded drain can hang
a deploy forever if one request never completes.

## 3. Structured Logging Fields Present [MUST]

```python
logger.info("transaction.approved", extra={
    "correlationId": ctx.correlation_id, "userId": ctx.user_id, "transactionId": tx.id
})
```

Verify log calls on this feature's critical paths actually include the correlation/trace ID from
context — not just a bare message string with no way to tie it to a specific request during an
incident.

## 4. Configuration Values Are Actually Externalized [MUST]

```java
// vulnerable — recompiled constant for a value an operator needs to tune live
private static final int MAX_RETRY = 5;

// required, if the design named this Configuration
@Value("${transfer.max-retry:5}")
private int maxRetry;
```

Verify every value the design labeled Configuration (not Code) is read from environment/config
service/feature-flag system — grep for a hardcoded literal where the design called for a tunable
value.

## 5. No Environment-Name Branching Standing in for a Feature Flag [SHOULD]

```java
if (environment.equals("prod")) { ... }   // flag this — usually should be a named feature flag
```

An `if (env == "prod")` branch conflates "which environment am I in" with "which behavior should be
active," and can't be toggled independently of a full redeploy to a different environment. Verify
a genuinely environment-specific behavior (not a rollout toggle) is actually what's intended before
accepting this pattern.

## 6. Resource Bound on Every Per-Request/Per-Message Spawn [MUST]

```go
// vulnerable — 1M concurrent requests spawns 1M goroutines
for req := range requests {
    go process(req)
}

// required — bounded worker pool
sem := make(chan struct{}, maxConcurrency)
for req := range requests {
    sem <- struct{}{}
    go func(r Request) { defer func() { <-sem }(); process(r) }(req)
}
```

Verify any goroutine/thread/task spawned per unit of external input has a cap — this overlaps with
`performance-implementation-checklist.md`'s concurrency-bound check; this is the operability framing
of the same bug (a resource exhaustion that shows up hours into a traffic spike, not in one request's
load test).

## 7. Resource Release on Every Path, Including Error Paths [MUST]

```python
# vulnerable — leaked on the exception path
conn = pool.acquire()
result = conn.execute(query)   # raises → conn never released
pool.release(conn)

# required
with pool.acquire() as conn:
    result = conn.execute(query)
```

Grep for manual acquire/release pairs (connections, file handles, locks) not wrapped in a
context-manager/`try-finally`/`defer` — a happy-path-only release leaks under any error condition.

## 8. Backup/Migration Reversibility Considered [SHOULD, for a schema migration]

If this change includes a migration, verify a rollback path exists or is explicitly stated as
not possible (some migrations, like an irreversible data transformation, genuinely aren't
reversible — that's acceptable only when stated, not discovered during an incident).

## 9. Anti-Pattern Grep Sweep [MUST]

```bash
# unbounded goroutine/thread spawn per item
grep -n "go func\|new Thread(" <changed_files>

# hardcoded config value where the design named it as tunable
grep -n "MAX_RETRY\s*=\|private static final int" <changed_files>

# environment-name branching
grep -rn "environment.equals\|process.env.NODE_ENV ===\|os.Getenv(\"ENV\")" <changed_files>

# manual resource acquire with no matching try/finally or context manager nearby
grep -n -A5 "pool.acquire\|\.getConnection(" <changed_files> | grep -L "finally\|with \|defer"
```

## 10. Test Coverage [MUST]

Verify tests exist (or an integration/smoke check is documented) for: readiness returning
unhealthy when a required dependency is down while liveness still passes; a graceful-shutdown
test that an in-flight request completes rather than being dropped when `SIGTERM` arrives; and, for
any newly-externalized config value, that changing it without a redeploy actually takes effect
(confirms it's genuinely externalized, not read once at startup from a baked-in default with no
live-reload path if the design required one).
