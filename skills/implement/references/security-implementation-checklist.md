# Security Implementation Checklist

Load this during Step 1 (IMPLEMENT) whenever the code touches authentication, authorization,
external input, payments/state transitions, file handling, or secrets — and always during Step 3
(VERIFY)'s Security check. It's the stack-agnostic master list; `spring-boot-checklist.md`,
`nestjs-checklist.md`, and `nextjs-prisma-checklist.md` hold the framework-specific slice
(what the DTO/guard/interceptor actually looks like in that stack). Go/Fiber has no dedicated
checklist file — use this file directly for MODE B code.

## Priority levels

Same convention as the design checklist: **[MUST]** blocks completion (fix before claiming done),
**[SHOULD]** needs an explicit reason if skipped, **[MAY]** is a recommendation.

## 1. Authentication [MUST]

- Password hashing: Argon2id / bcrypt / scrypt only. Grep for anything hashing with MD5/SHA1/bare
  SHA256 and fix it.
- Never log a password, and never let one appear in an API response (including on create/update
  echo-back).
- JWT: verify signature on every decode — never call a decode-without-verify function and trust
  the result. Check `exp`, `iss`, `aud`. Don't read the algorithm from client-controlled input.

```bash
# vulnerable
jwt.decode(token, { verify: false })
# required
jwt.verify(token, secret, { issuer, audience })
```

## 2. Authorization [MUST]

Every non-public endpoint/handler needs an explicit, readable authorization check — verified by
reading the actual guard/annotation/middleware, never assumed from the route name or a comment.
For any endpoint that takes a resource ID, add the ownership check on top of the role check:

```text
user.hasPermission(ACTION) AND user.canAccess(resourceId)
```

An endpoint that only checks "is authenticated" and then trusts a path/body-supplied ID is an IDOR
bug — this is the single most common gap between "looks secure" and "is secure."

## 3. Input Validation [MUST]

Validate at the actual trust boundary for this stack (DTO + pipe for NestJS, Bean Validation for
Spring, Server Action for Next.js, explicit struct validation for Go — the design likely named
which). Treat query params, path variables, headers, cookies, JWT claims, uploaded files, and
inbound MQ messages the same as body — all untrusted, all validated before use.

```java
// vulnerable
String sql = "SELECT ... WHERE name = '" + name + "'";
// required
jdbcTemplate.query(sql, Map.of("name", name));
```

## 4. Injection [MUST]

- **SQL**: parameterized queries / ORM binding only (`PreparedStatement`, JPA parameter binding,
  `NamedParameterJdbcTemplate`, Prisma's parameterized API, TypeORM query builder). Any raw
  string-concatenated query — including a raw `$queryRaw`/`$queryRawUnsafe`/native `@Query` — gets
  flagged for extra review, not waved through because "it's just internal."
- **NoSQL (Mongo)**: never accept a client-supplied filter/operator object (`$where`, `$ne`, `$gt`)
  directly — build the query from a validated DTO's fields, not from `req.body` passed through.
- **Command injection**: never `Runtime.exec(userInput)` / `os/exec` with unsanitized args / Node
  `exec()` with string interpolation. If shelling out is unavoidable: allowlist the command,
  allowlist arguments, no shell (`exec`, not `shell: true`), timeout, least-privileged user.

```go
// vulnerable
exec.Command("sh", "-c", userInput)
// required
exec.Command(allowlistedBinary, validatedArgs...)
```

## 5. SSRF [MUST when fetching a user-supplied URL]

Before making the outbound request: check the resolved IP against loopback/link-local
(`169.254.169.254`)/private ranges, enforce a host allowlist, don't follow redirects blindly, set
a connection timeout and response size cap.

## 6. File Upload [MUST for upload/download handlers]

Check extension AND MIME type AND magic bytes (not just `Content-Type` header, which the client
controls). Generate the storage filename server-side — never write `req.file.originalname`
straight to disk (path traversal via `../../`). Enforce a size limit before reading the full body
into memory. Store outside the web root. Require the same authorization check on download as on
upload — a predictable/guessable upload path is not access control.

## 7. Secrets [MUST]

```bash
git grep -iE "(password|secret|api_key|jwt_secret|private_key)\s*=\s*['\"]" -- <src-glob>
```

Anything this matches (that isn't a variable name/config key reference) is a finding. Secrets come
from environment variables / Vault / cloud secret manager / K8s Secret — never a literal in code,
never in a committed `.env` (only `.env.example` with placeholder values).

## 8. Encryption [SHOULD, MUST for PII/financial fields]

HTTPS/TLS enforced in production config (not just "assumed handled by the platform" — confirm).
If the design called for at-rest encryption on specific fields/tables, verify it's actually wired,
not deferred silently.

## 9. API Hardening [MUST]

Rate limit (especially `/login`, `/register`, `/password-reset`, `/otp`, `/token`, `/search`,
`/file-upload`, `/payment`), request size limit, pagination cap (reject or clamp an unbounded
`size`/`limit` param — never pass a client-supplied page size straight to the query), timeout,
Content-Type validation.

```http
GET /transactions?page=1&size=10000000
```
must be clamped or rejected — verify the actual code path does this, not just that a max-size
constant exists somewhere unused.

## 10. Business Security [MUST for state-changing/financial code]

- **Idempotency**: if the design specified an `Idempotency-Key` (or equivalent) for a
  transfer/payment/state-changing endpoint, verify it's actually checked and stored — a key that's
  accepted but not enforced is worse than not having one, because it looks safe.
- **Race conditions**: verify the concurrency-control mechanism named in the design (optimistic
  lock/version column, pessimistic `SELECT ... FOR UPDATE`, distributed lock, or DB transaction
  boundary) is actually applied around the read-modify-write, not just around the write.
- **State transitions**: if a status field has a defined transition graph, verify the code rejects
  an illegal transition rather than blindly overwriting the field.

## 11. Logging & Secrets-in-Logs [MUST]

```bash
# vulnerable pattern to grep for
log.info("request={}", request)   # if request can contain password/token/OTP/PII
```

Never log password, access/refresh token, OTP, card number, private key, full PII, or the
`Authorization` header. Structured logs should carry correlation ID / trace ID / user ID instead of
raw payloads. Security-sensitive actions (LOGIN, CREATE, UPDATE, DELETE, APPROVE, REJECT, TRANSFER,
CHANGE_PERMISSION, CHANGE_PASSWORD) need an audit-log entry — verify it's actually emitted, not
just planned in the design.

## 12. Error Handling [MUST]

```json
// vulnerable
{ "error": "SQLException: relation users does not exist..." }
// required
{ "code": "INTERNAL_ERROR", "message": "Internal server error", "traceId": "..." }
```

Verify the actual exception handler/middleware produces the generic shape for unexpected errors —
don't let a framework's default error page/handler leak a stack trace, SQL, file path, internal
hostname, or dependency version in production config.

## 13. CORS / CSRF [MUST]

If cookie-based auth: verify `HttpOnly`, `Secure`, `SameSite` are actually set on the session
cookie (read the actual cookie-setting code, not the design doc), and that a CSRF check exists for
state-changing requests. If Bearer-token auth: confirm no `Access-Control-Allow-Origin: *` +
`Access-Control-Allow-Credentials: true` combination exists — that combination is invalid/unsafe
regardless of auth style.

## 14. Security Headers [SHOULD, for browser-facing services]

Verify `Content-Security-Policy`, `X-Content-Type-Options`, `Strict-Transport-Security` are set
(via middleware/framework default, e.g. Spring Security defaults, Helmet for Node) and that
`Server`/`X-Powered-By` are suppressed rather than left at framework defaults.

## 15. Database Security [SHOULD]

Verify the app's DB connection user is not `root`/superuser. Verify connection pool has a max size
and queries have a timeout (an unbounded query/connection can become a DoS vector).

## 16. Cache / Redis [SHOULD]

Verify TTL is actually set on anything cached that's sensitive (session, token, authorization
decision) — a cache write with no expiry is a bug even if it "works." Verify Redis connection uses
auth/TLS if reachable outside a fully trusted network.

## 17. Message Queue [SHOULD]

Verify consumer code validates message schema/content before acting on it — "it came from our own
topic" is not a trust boundary. Verify duplicate-delivery handling (consumer idempotency) matches
what the design specified.

## 18. Multi-Tenant Isolation [MUST if multi-tenant]

```sql
-- vulnerable
SELECT * FROM transactions WHERE id = ?
-- required
SELECT * FROM transactions WHERE id = ? AND tenant_id = ?
```

Grep for queries against tenant-owned tables that filter only by primary key — each one is a
potential cross-tenant leak.

## 19. Dependency Security [SHOULD] — run per stack

```bash
pip-audit                                   # Python
safety check                                # Python (alternative)
govulncheck ./...                           # Go
gosec ./...                                 # Go (SAST-ish)
mvn org.owasp:dependency-check-maven:check  # Java/Spring (if plugin configured)
npm audit / pnpm audit                      # Node/NestJS/Next.js
```

## 20. Container/Kubernetes [SHOULD, if this change touches deployment manifests]

No `privileged: true`. Verify `runAsNonRoot`, `readOnlyRootFilesystem`, dropped capabilities,
resource limits, and that secrets are mounted via the platform's secret mechanism, not baked into
the image or env-var'd in a plain ConfigMap.

## 21. Security Test Cases [MUST — write these, don't skip to "happy path + one error"]

For every protected or state-changing endpoint, write (or confirm existing coverage for):
unauthenticated request, unauthorized request (wrong role), IDOR (user A requests user B's
resource id → expect 403/404, never 200), expired token, invalid/tampered token, replayed request
(same idempotency key twice → second is a no-op or rejected, not a duplicate effect), rate-limit
exceeded, oversized request body, malformed JSON, and — if multi-tenant — cross-tenant access
(tenant A's token against tenant B's resource id).

```text
User A
   ↓
GET resource of User B
   ↓
403 (never 200)
```

This is the same shape as the design's Security Testing section (`design/references/security-checklist.md` §21)
— implementation's job is to prove those test cases actually pass, not to re-derive the list.
