# API Implementation Checklist

Load this whenever the code being implemented exposes an HTTP endpoint or Server Action.
Design-time rationale for every item here lives in
`.claude/skills/design/references/api-design.md` — this file verifies the code actually
implements the contract shape that was designed, with concrete per-stack patterns. It
complements, not duplicates: `security-implementation-checklist.md` (auth/rate-limit per
endpoint, error-shape leakage) and `performance-implementation-checklist.md` §2–3 (payload/page
size limits) — this file is specifically about the *contract shape* being consistent and correct.

## Priority levels

Same convention as the other implementation checklists: **[MUST]** blocks completion,
**[SHOULD]** needs an explicit reason if skipped.

## 1. Response Envelope Consistency [MUST]

Grep every handler/controller in the changed code for its success and error response shape and
verify they all match the one envelope the project uses — a handler that returns a bare array,
or an error as a raw string instead of `{error: {code, message, details}}`, forces every client
to special-case that one endpoint:

```javascript
// inconsistent — this endpoint alone returns a bare array
return res.json(transactions);
// required — matches the project's envelope
return res.json({ data: transactions, pagination: {...} });
```

MODE C Server Actions: verify every action returns the `{success, data|error, fieldErrors?}`
result union — not a thrown exception for an expected validation/business error (that breaks the
"preserve form input on failure" behavior the design specified).

## 2. Status Code Discipline [MUST]

Verify the actual status code returned for each path, not just the happy path:

- `401` (no/invalid credentials) is never substituted for `403` (authenticated but not
  authorized) or vice versa — grep for a single generic `catch` that maps every auth failure to
  one status code.
- `409` (state conflict — approving an already-approved resource) is distinct from `422`
  (semantically invalid input) — both are distinct from a blanket `400`.
- `429` responses include a `Retry-After` header if the design specified rate limiting.
- A downstream/dependency failure returns `503`, not `500` — collapsing the two removes the
  client's ability to decide whether retrying makes sense.
- No success path returns `200` for a request that actually failed (a caught exception papered
  over with a `200 { error: ... }` body is a common way this slips in).

## 3. Idempotency-Key Implementation [MUST for a state-changing POST susceptible to duplicate submission]

```python
# required shape
key = request.headers.get("Idempotency-Key")
existing = IdempotencyRecord.objects.filter(key=key).first()
if existing:
    return existing.cached_response, existing.status_code   # same result, not a second effect
record = IdempotencyRecord.objects.create(key=key)   # backed by a UNIQUE constraint
result = process_payment(...)
record.cached_response = result
record.save()
```

Verify: the key is stored behind a real uniqueness constraint (not just an in-memory cache —
cross-reference `data-integrity-implementation-checklist.md` §1–2), a repeated key returns the
original result and status code rather than re-running the side effect, and the key has a stated
expiry rather than growing the table forever.

## 4. Pagination Contract [MUST for any list endpoint]

Verify the endpoint enforces a **max** page size (not just validates the type of the `page`/`size`
param — cross-reference `performance-implementation-checklist.md` §3), and that the response
actually includes `totalItems`/`hasMore`/`nextCursor` matching the style (offset vs. cursor) the
design specified — a client should never have to speculatively fetch page N+1 to find out if it
exists.

## 5. Filter/Sort Allowlist Enforcement [MUST for any list endpoint accepting filter/sort params]

```javascript
// vulnerable — any client-supplied column name reaches the query builder
const sorted = query.orderBy(req.query.sort);
// required — allowlisted
const ALLOWED_SORT = ["createdAt", "amount", "status"];
if (!ALLOWED_SORT.includes(req.query.sort)) throw new BadRequestException();
```

Grep for a filter/sort parameter passed directly into a query/ORM call with no allowlist check —
this is both a correctness gap (exposes internal column names) and a performance gap (forces a
full scan on an unindexed field).

## 6. Versioning Enforcement [MUST — verify it matches what the design stated, even "none yet"]

If the design specified URI (`/v1/...`) or header versioning, verify the route registration/
middleware actually implements it — a design section stating a versioning strategy that the
routes don't reflect is a silent drift between design and code.

## 7. Content-Type & Request Validation [MUST]

Verify every endpoint validates its request body against a schema/DTO before touching business
logic (framework validation pipe/decorator actually applied on *this* endpoint, not assumed from
a global default — cross-reference `security-implementation-checklist.md`'s trust-boundary item),
and that a wrong `Content-Type` is rejected with `415` rather than an attempt to parse it anyway.

## 8. Error Shape Leak Check [MUST]

Grep the error-handling path for a stack trace, raw SQL, file path, internal hostname, or
framework version reaching the client response — cross-reference
`security-implementation-checklist.md` §12, this file just adds the API-envelope framing: a leak
inside the `details` field of an otherwise-correct envelope is still a leak.

## 9. Anti-Pattern Grep Sweep [MUST — run before claiming API-contract-reviewed]

```bash
# verb-in-path or filter-in-path smell (manual check — grep flags candidates)
grep -rn "app\.\(get\|post\)('/[a-z]*[A-Z]" <changed_files>

# generic catch-all error status (candidates — verify each hit)
grep -n -A3 "catch" <changed_files> | grep "status(500)\|status(400)"

# list endpoint with no visible page-size clamp
grep -n -B5 "findMany\|\.find(\|SELECT " <changed_files> | grep -L "take:\|LIMIT\|pageSize"

# sort/filter param passed straight into a query with no allowlist nearby
grep -n "orderBy(req\.\|sort(req\.\|\.sort(ctx\." <changed_files>
```

## 10. Mandatory Test Cases [MUST include for any feature exposing an endpoint]

Malformed/wrong-`Content-Type` request (expect `400`/`415`, not a 500 crash); oversized
page-size query param (expect clamped or rejected, never served in full); duplicate request with
the same `Idempotency-Key` (expect the original result, not a second effect); sort/filter on a
non-allowlisted field (expect `400`, not a raw DB error or unindexed full scan); response body on
both the success and error path matches the documented envelope shape exactly.
