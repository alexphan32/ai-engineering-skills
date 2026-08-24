# API Design Checklist

Load this during ANALYZE, before shaping any endpoint/Server Action, and again in DRAFT when
writing Section 4 (API Specification) — MODE B/C/D/E. It is the stack-agnostic master list for the
*contract shape* itself: naming, status codes, envelopes, pagination, versioning. Mode templates
hold only the stack-specific transport mechanics (route registration, DTO class, controller
signature) — this file holds the conventions that make every endpoint in the system consistent with
every other one, so a client never has to special-case one feature's response shape.

This complements, not duplicates: `security-checklist.md` §9 (auth/rate-limit/size-limit per
endpoint) and §12 (error shape must not leak internals), `performance-checklist.md` (pagination
size vs. latency budget), `distributed-systems-checklist.md` §35–36 (event envelopes, backward
compatibility for a *published* API), and `data-integrity-checklist.md` §12 (idempotency at the
data layer). This file is where those conventions get one canonical *shape* so every checklist
above can point at it instead of re-deriving it per feature.

**Scope note**: this file assumes REST/HTTP JSON APIs, which is what MODE B/C/D/E all use today. If
a future mode targets GraphQL or gRPC, most sections below (status→error mapping, pagination,
versioning intent) still apply conceptually, but the concrete shapes (§2–4) don't transfer as-is —
don't force this file's REST shapes onto a non-REST transport; write the equivalent instead.

## Priority levels

Same convention as the other checklists: **[MUST]** blocks the SDS from being done for a feature
this applies to, **[SHOULD]** needs an explicit reason if skipped, **[MAY]** is a recommendation.

## 1. Resource Naming & URL Structure [MUST]

- Nouns, not verbs: `POST /transactions`, never `POST /createTransaction`. The HTTP method carries
  the verb.
- Plural collection names: `/accounts`, `/accounts/{id}`, not `/account/{id}`.
- Nesting reflects genuine ownership, capped at one level: `/accounts/{id}/transactions` is fine;
  `/accounts/{id}/transactions/{txId}/line-items/{itemId}/audit` is a sign the resource needs its
  own top-level collection with a filter query param instead
  (`/audit?transactionId=&lineItemId=`).
- Path params identify a specific resource; query params filter/sort/paginate a collection — never
  put a filter in the path (`/transactions/status/PENDING` is wrong; `/transactions?status=PENDING`
  is right).
- Actions that don't map to CRUD (approve, reject, cancel) are a sub-resource verb on purpose:
  `POST /transactions/{id}/approve`, not a `PATCH` that overloads `status` with hidden side effects
  the client can't discover from the field name alone.

## 2. HTTP Methods & Status Codes [MUST]

State the method and success/error status codes for every endpoint — don't leave "200 or maybe 201"
ambiguous:

| Method | Use | Success | Common errors |
|---|---|---|---|
| `GET` | Read, no side effects, safe to retry/cache | `200` | `404` not found |
| `POST` | Create, or a non-CRUD action | `201` (with `Location` header for creates) / `200` (action) | `400` validation, `409` conflict |
| `PUT` | Full replace of a resource, idempotent | `200`/`204` | `404`, `400` |
| `PATCH` | Partial update | `200`/`204` | `404`, `400`, `409` |
| `DELETE` | Remove, idempotent | `204` (or `200` with a body if returning the deleted state) | `404` |

Beyond the table: `401` (no/invalid credentials) vs. `403` (authenticated but not authorized) are
never interchangeable — collapsing them into one generic "access denied" status is a design gap,
not a simplification. `409` for a state-conflict (approving an already-approved transaction) is
distinct from `422` for semantically invalid input (well-formed JSON, business-rule violation).
`429` for rate-limit exceeded states a `Retry-After` header. `503` for a downstream dependency being
down is distinct from `500` for an unexpected server bug — a design that only ever returns `500`
gives the client no way to decide whether retrying makes sense.

## 3. Response Envelope [MUST]

Pick one shape per project/mode and apply it to every endpoint — a client should never have to
special-case one feature's response format:

```json
// Success (single resource)
{ "data": { "id": "tx_123", "amount": 100 } }

// Success (collection)
{ "data": [ { "id": "tx_123" } ], "pagination": { "page": 1, "pageSize": 50, "totalItems": 230 } }

// Error
{ "error": { "code": "INSUFFICIENT_BALANCE", "message": "Account balance too low", "details": {} } }
```

- `code` is a stable machine-readable string the client can branch on — never make the client parse
  `message` to decide behavior, and never let `message` alone carry information the client depends
  on programmatically.
- MODE C's Server Actions use the equivalent result-union instead of an HTTP envelope —
  `{success, data|error, fieldErrors?}` — same principle (client never has to guess the shape),
  different mechanism because Server Actions aren't raw HTTP responses.
- Never let the error shape include a stack trace, raw SQL, file path, internal hostname, or
  framework version (`security-checklist.md` §12) — `details` is for field-level validation errors
  the client can act on, not internal diagnostics.

## 4. Pagination [MUST for any list endpoint]

State explicitly: default page size, **max page size** (never unbounded —
`security-checklist.md` §9 requires this), and which style:

- **Offset-based** (`?page=1&pageSize=50`): simple, but "page 40 of a table with concurrent
  inserts" can skip or repeat rows — acceptable for small/rarely-changing collections.
- **Cursor-based** (`?cursor=eyJpZCI6MTIzfQ&limit=50`): stable under concurrent writes, required
  for a large or high-churn collection (feeds, transaction logs) — state the cursor's encoding
  (opaque base64 of the sort key) so it isn't treated as a raw offset by callers.

Every collection response states `totalItems` (offset-based) or `hasMore`/`nextCursor`
(cursor-based) — a client should never have to fetch page N+1 speculatively just to find out if it
exists.

## 5. Filtering & Sorting [SHOULD]

State the allowed filter/sort fields explicitly per list endpoint — an unbounded
`?sort=<any column>` risks exposing an internal column name or forcing a full table scan on an
unindexed field. The filter/sort fields stated here are exactly what `database-design.md` §2's
indexing strategy is built from — design them together, not filtering first and indexing as an
afterthought.

## 6. Versioning [MUST — state the strategy even if "none yet"]

- **URI versioning** (`/v1/accounts`): most explicit, easiest for clients to pin to, costs a
  duplicated route tree per version.
- **Header versioning** (`Accept: application/vnd.api+json;version=2`): keeps URLs stable, harder
  for clients to discover/test manually.
- **No versioning yet** is a valid MVP answer (Tier 1) — but state it explicitly and cross-reference
  `distributed-systems-checklist.md` §36 for what happens the day a breaking change is needed with
  active consumers, rather than discovering there's no plan when that day arrives.

## 7. Idempotency [MUST for any state-changing endpoint susceptible to duplicate submission]

An `Idempotency-Key` request header (client-generated UUID) lets a retried `POST` (network timeout,
double-click, at-least-once delivery from a gateway) return the original result instead of creating
a second effect. Design states: where the key is stored (with a uniqueness constraint —
`data-integrity-checklist.md` §12), the response returned on a repeat key (original result, same
status code), and the key's expiry window. `GET`/`PUT`/`DELETE` are idempotent by HTTP semantics
already — this section is specifically for `POST` actions with side effects (transfers, payments,
approvals).

## 8. Content Negotiation & Validation [MUST]

- Reject a request whose `Content-Type` doesn't match what the endpoint expects (`415`) rather than
  attempting to parse it anyway.
- Every request body validated against a schema/DTO before touching business logic — this is what
  each mode template's DTO/validation layer implements; this file just states that the *contract*
  (which fields, which types, which are required) is itself part of the API design, not an
  implementation afterthought.

## 9. API Contract Documentation [SHOULD]

State whether this feature's endpoints are documented via OpenAPI/Swagger (MODE B/D/E — generated
from annotations or a spec file) or a typed contract shared between client and server (MODE C —
Server Action types imported directly by the calling component). A REST API with no machine-readable
contract is a design gap for any consumer outside the same codebase.

## 10. Anti-Patterns — Red Flags

If any of these appear in a design, stop and redesign: a verb in a URL path (`/getUser`); a filter
value embedded in the path instead of a query param; a single generic error `code` used for every
failure so the client can't branch; a list endpoint with no stated max page size; a `PUT` that isn't
actually idempotent (side effects beyond replacing the resource); a `200` returned for a request
that failed; a versioning strategy left unstated because "we'll figure it out later"; an
`Idempotency-Key` accepted but not enforced with a uniqueness constraint.

## 11. Invariants

```text
1. Every endpoint's method + success/error status codes are stated explicitly, not implied.
2. Every list endpoint states a max page size — no unbounded response is possible.
3. One response envelope shape is used consistently across every endpoint in the same mode.
4. Every error code is a stable, client-actionable string — never a raw exception message.
5. Every state-changing POST endpoint states its idempotency mechanism or explicitly notes N/A.
6. The versioning strategy is stated even when the answer is "none yet."
```

## 12. Mandatory Test Cases [MUST include in the test plan for any feature exposing an endpoint]

Malformed/wrong-Content-Type request (expect `400`/`415`, not a 500 crash); oversized page-size
query param (expect it clamped or rejected, never served in full); duplicate request with the same
`Idempotency-Key` (expect the original result, not a second effect); sort/filter on a
non-allowlisted field (expect `400`, not a raw DB error or unindexed full scan); response body
matches the documented envelope shape on both the success and error path.
