# Security Design Checklist

Load this when drafting **Section 7 (Security Design)** of any SDS (MODE B/C/D/E), and skim it
during MODE A design when the pipeline touches secrets, external input, or PII. It is the
stack-agnostic master list — mode templates hold only the stack-specific slice (auth table shape,
ORM injection pattern, DTO mapping). This file holds the items that are easy to forget because no
template section prompts for them.

## Priority levels

- **[MUST]** — the SDS is not done without this. Missing a MUST is a blocking finding in `/review`.
- **[SHOULD]** — omit only with an explicit reason recorded in Open Questions (`[SECURITY EXCEPTION — reason]`).
- **[MAY]** — recommendation; note it, don't block on it.

Don't apply every section to every feature — a read-only reporting endpoint doesn't need file-upload
or business-security items. Do explicitly note "N/A — no file upload / no state change / no external
call" rather than silently skipping, so a reviewer can tell "considered and excluded" from "forgotten."

## Threat-modeling questions (answer during ANALYZE, before DESIGN)

Answering these in a sentence or two each is usually enough — the point is forcing the question,
not writing an essay:

1. **Assets** — what data/capability does this feature expose or mutate that's worth attacking?
2. **Trust boundaries** — where does untrusted input enter (HTTP body/query/path/headers/cookies,
   JWT claims, uploaded files, MQ messages, webhooks, another service's response)?
3. **Authentication mechanism** — how is the caller's identity established for this feature?
4. **Authorization model** — role only, or role + resource ownership? (See "User → Auth → Role →
   Permission → Resource ownership → Action" — never stop at "is logged in".)
5. **Sensitive data** — does this feature touch PII, credentials, financial data, or secrets?
6. **Attack surface** — new endpoints/topics/files this feature adds; what can an attacker reach
   that didn't exist before?
7. **External dependencies** — new libraries, external APIs, or services this feature calls.
8. **Failure scenarios** — what happens on partial failure (e.g., payment debited but confirmation
   write fails)?
9. **Abuse scenarios** — how would a malicious *authenticated* user misuse this feature (not just
   an outside attacker)?
10. **Security controls** — which of the sections below actually apply here?

## 1. Authentication [MUST]

- Password (if this feature manages credentials directly): hash with Argon2id/bcrypt/scrypt —
  never MD5/SHA1/bare SHA256. Never log, never return in any API response, never store plaintext.
- Token (JWT or similar): design must state — signature verification, `exp`/`iss`/`aud` checks,
  no trusting an algorithm hint from the client (`alg: none` class of bug), short-lived access
  token + refresh rotation, no sensitive data embedded in the token payload.
- Never accept a decoded-but-unverified token as authenticated identity.

## 2. Authorization [MUST]

Never design a check that stops at "is authenticated." Every protected action needs the full chain:

```
Authentication → Role → Permission → Resource ownership → Action
```

Explicitly design against: IDOR, horizontal privilege escalation (same role, different user's
resource), vertical privilege escalation (lower role reaching higher-role actions), missing
authorization on an endpoint, confused deputy (service acts on a user's behalf without re-checking
that user's permission).

`GET /accounts/{id}` requiring "authenticated" is not a design — it must specify
`user.hasPermission(VIEW_ACCOUNT) AND user.canAccess(accountId)`.

## 3. Input Validation [MUST]

Every entry point (HTTP body, query params, path variables, headers, cookies, JWT claims, uploaded
files, MQ messages, webhooks, external API responses) is untrusted. Design states, per field:
validate → normalize → sanitize (if rendering/interpreting) → business validation. This is on top
of — not instead of — the stack's own DTO/schema validation already covered in mode templates §7.

## 4. Injection [MUST]

Beyond the SQL/NoSQL injection pattern already in each mode template's Data Security subsection:

- **Command injection**: if the feature must ever shell out, design states an allowlist of
  commands/arguments, no shell interpolation, timeout, least-privilege execution — never
  "pass user input to a shell command" as a design.
- **NoSQL injection** (Mongo-backed features): client-supplied query operators (`$where`, `$ne`,
  `$gt`, ...) must never reach the query directly — the query object comes from a validated DTO,
  never a client-supplied filter object passed through.

## 5. SSRF [MUST if the feature fetches a user-supplied URL]

If any endpoint accepts a URL and the backend fetches it, design must state:

- URL allowlist (scheme + host)
- Reject/resolve-and-check: loopback (`127.0.0.1`, `localhost`), link-local (`169.254.169.254` —
  cloud metadata endpoint), private ranges (RFC1918), internal DNS names, Kubernetes service DNS
- Redirect validation (don't follow a redirect into a blocked range)
- Connection timeout and response size limit

## 6. File Upload [MUST if the feature accepts uploads]

Design must state: extension allowlist, MIME type check, magic-byte check (not just the declared
Content-Type), file size limit, server-generated filename (never the client-supplied filename),
storage outside the web root, no execution of uploaded files, authorization check on download (not
just on upload), and path-traversal-safe storage path construction.

## 7. Secrets Management [MUST]

No credential, API key, JWT signing secret, or private key in the SDS's example config, code
snippets, or committed anywhere — design states the source as environment variable / Vault /
cloud secret manager / K8s Secret, and for production-grade sensitivity notes that a K8s Secret
alone is not full protection — prefer Vault/AWS Secrets Manager/GCP Secret Manager/Azure Key Vault
when the data warrants it.

## 8. Encryption [SHOULD, MUST for PII/financial data]

- Transit: HTTPS/TLS 1.2+ only for anything carrying sensitive data — state this explicitly rather
  than assuming the platform handles it.
- At rest: PII, financial data, authentication secrets, and private keys should be encrypted at
  the database, backup, and object-storage layers — call out which of these apply and which are
  deferred to infrastructure (and confirm infra actually does it, don't assume).

## 9. API Security [MUST]

Every endpoint design states: auth, authorization, rate limit tier, request size limit, pagination
limit (state the max page size — e.g. 100/500, never unbounded), timeout, idempotency (see §10),
schema validation, Content-Type validation. `GET /transactions?page=1&size=10000000` must be
rejected by design, not accidentally handled.

## 10. Business Security [MUST for state-changing/financial features]

- **Replay attack**: state-changing operations (especially transfers/payments) must design an
  idempotency mechanism (`Idempotency-Key` header or equivalent) — resubmitting the same request
  must not create a second effect.
- **Race condition**: any concurrent-access resource (balance, payment, withdrawal, approval,
  limit, inventory) needs an explicit concurrency-control design — optimistic locking, pessimistic
  locking, distributed lock, or a state machine that makes the race safe by construction. Naming
  the mechanism is a required part of the SDS, not an implementation detail to figure out later.
- **State transitions**: define the allowed state graph explicitly (e.g. `PENDING → COMPLETED` is
  only valid if no business rule forbids it) — an SDS for anything with a status field should
  state which transitions are legal, not just the states.

## 11. Logging & Audit [MUST]

- Never design a log statement that includes password, access/refresh token, OTP, card number,
  private key, or full PII. Logging a whole request/response object is a design smell if that
  object can contain any of these.
- Structured logging (correlation ID, trace ID, user ID, tenant ID, request ID) for observability.
- A separate **audit log** is required for security-sensitive actions: LOGIN, CREATE, UPDATE,
  DELETE, APPROVE, REJECT, TRANSFER, CHANGE_PERMISSION, CHANGE_PASSWORD. State which of these
  this feature triggers and that they're captured.

## 12. Error Handling [MUST]

Design the client-facing error shape once and reuse it — it must never include stack trace, raw
SQL, filesystem path, internal hostname/IP, framework version, or credentials. Detail belongs in
the internal log only, correlated by a trace ID the client-facing error does carry.

## 13. CORS / CSRF [MUST — state which regime applies]

State explicitly which of these two the feature is:

- **Bearer-token API** (`Authorization: Bearer ...`) — different CSRF risk profile than cookies;
  state that CSRF tokens are not needed *because* auth isn't carried by an ambient cookie — don't
  leave this implicit.
- **Cookie-based auth** — requires `HttpOnly`, `Secure`, `SameSite`, and explicit CSRF protection.

CORS: never design `Access-Control-Allow-Origin: *` for an API that accepts credentials.

## 14. Security Headers [SHOULD, for anything served to a browser]

`Content-Security-Policy`, `X-Content-Type-Options`, `Strict-Transport-Security`,
`Referrer-Policy`, `Permissions-Policy`. Don't expose `Server`/`X-Powered-By`/framework version.

## 15. Database Security [SHOULD]

Least-privilege DB user (never `root`/`admin`/superuser for the application connection) — note
whether this feature needs a separate read-only or migration-only credential. Connection over TLS,
pool/connection/query/statement timeouts, backup encryption.

## 16. Cache (Redis) Security [SHOULD, if the feature touches cache]

Don't treat Redis as trusted-by-default: authentication, TLS, network isolation, ACL. Never cache
an authorization decision, session, or token without an explicit TTL/invalidation strategy —
"cached and never expires" is a design bug, not an optimization.

## 17. Message Queue (Kafka/etc.) Security [SHOULD, if the feature produces/consumes messages]

TLS, SASL, ACL (topic + consumer-group authorization), message schema validation. A message off
the bus is not trusted just because it came from an internal topic — validate it like any other
external input. Design explicitly for duplicate delivery, replay, and malformed/poison messages.

## 18. Multi-Tenant Security [MUST if the system is multi-tenant]

Every query against tenant-owned data must be designed with `tenant_id` (or equivalent) as part of
the lookup key, not just the primary key:

```sql
-- dangerous shape
SELECT * FROM transactions WHERE id = ?
-- required shape
SELECT * FROM transactions WHERE id = ? AND tenant_id = ?
```

Rule: **never design access to a tenant-owned resource without tenant-boundary enforcement.**

## 19. Dependency Security [SHOULD]

Note any new third-party library this feature introduces and flag it for a vulnerability/license
check in CI (SCA) before merge — don't let a new dependency ride in unreviewed as an implementation
detail.

## 20. Container/Kubernetes Security [SHOULD, if this feature ships as/changes a workload]

If the SDS touches deployment: no `privileged: true`, `runAsNonRoot`, `readOnlyRootFilesystem`,
dropped capabilities, resource limits, network policy, and secret management via the platform's
mechanism (not baked into the image).

## 21. Security Testing [MUST — feed into the SDS's test plan]

The test plan (Section on testing / traceability) must include, for any protected or state-changing
endpoint: unauthenticated access, unauthorized access (wrong role, IDOR — user A fetching user B's
resource, expect 403/404), expired token, invalid token, replay of the same request, rate-limit
exceeded, oversized request, malformed payload, and — if multi-tenant — cross-tenant access.
These are mandatory integration tests, not optional edge cases.
