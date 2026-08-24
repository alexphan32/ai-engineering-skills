# SDS Template C: Next.js + Prisma (App Router)

> Reference for `design` skill — loaded on demand when creating MODE C SDS documents.
>
> **Before drafting**: verify the installed Next.js and Prisma major versions against
> `node_modules/next/dist/docs/` and the Prisma docs/changelog. Both frameworks have had
> breaking changes across majors (`middleware.ts` → `proxy.ts`, Edge runtime dropped,
> Prisma generator/datasource config location, mandatory driver adapters, etc.) — do not
> assume an older API shape from prior knowledge.

---

## TEMPLATE C: Next.js + Prisma SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: Next.js {version} (App Router), Prisma {version}, {database}

---

## 0. Adaptation Note (if reusing an org design template)

If this project's design template originates from a different stack (e.g. a Go/Fiber
"MODE B" template), state the mapping explicitly so reviewers can trace conventions:

| Template concept | Next.js + Prisma equivalent |
|---|---|
| Handler | Server Component (reads) / Server Action (writes) |
| Repository | Data-access module (`lib/*.ts`) |
| Use Case | Server Action or a plain function it calls |
| Entity | Prisma model |
| Middleware | `proxy.ts` (Next.js 16+) — confirm current name against installed docs |

---

## 1. Module Overview

### 1.1 Description
[Describe what this module does in the system]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Module Type**: [Visitor-facing read path / Admin write path / Shared]
**Scale Tier**: [Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed — one-line reason, see `.claude/skills/architecture/references/system-scale-checklist.md`]

### 1.3 File Layout
```
prisma/schema.prisma        [Entity]-related model(s) — note if shared with another feature
lib/
  {module}.ts                Data-access reads: get{Entity}ById, list{Entity}sBy...
  admin-{module}.ts          Data-access writes (if this feature owns writes): create/update/delete
app/
  {route}/page.tsx            Server Component — reads via lib/{module}.ts
  {route}/actions.ts           Server Actions — writes via lib/admin-{module}.ts
  actions/{name}.ts             Standalone Server Action (if not colocated with a route)
```

**Entities (Prisma models)**: [List models this module touches]
**Server Actions**: [List — one row per mutation]
**Routes/Pages**: [List]
**Dependencies**: [e.g. M-01 auth/session for protected routes]

---

## 2. Data Model

### 2.1 Prisma Model: [ModelName]

```prisma
// prisma/schema.prisma
// Traceability: SDS M-XX Section 2.1
model [ModelName] {
  id        String   @id @default(cuid())
  [field]   String
  status    [Status] @default(DRAFT)
  order     Int
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

**Field Definitions:**

| Field | Type | Required | Owner (if shared model) | Description |
|-------|------|----------|--------------------------|-------------|
| id | String (cuid) | Yes | — | Primary key |
| [field] | String | Yes | this feature | [description] |
| status | enum | Yes | this feature | Draft/Published gate — see §7 |
| order | Int | Yes | this feature | **Can have gaps** if rows are hard-deleted — see §9.3 |
| createdAt / updatedAt | DateTime | Yes | — | Standard timestamps |

**If this model is shared across features** (e.g. one feature owns content fields, another
owns a derived counter): state it explicitly here, not just in code comments — this is the
single most common MODE C design gap. Example: "M-02 (admin) owns every field except
`viewCount`, which only M-01 (visitor) writes."

### 2.2 Migration Notes
- New model / new fields on existing model? [state which]
- Any field renamed/removed → note downstream readers that must be updated
- Indexes needed: [field(s), reason — e.g. `@@index([status, order])` for list queries]

---

## 3. Data Access Layer (Reads)

### 3.1 Read Functions — `lib/{module}.ts`

```typescript
// lib/{module}.ts
// Traceability: SDS M-XX Section 3.1

export async function get{Entity}ById(id: string): Promise<{Entity} | null> {
  // MUST filter status = PUBLISHED at the query layer if this is a public-facing
  // read — never filter in the component. Prevents draft-leak-by-guessed-id.
}

export async function list{Entity}sBySection(section: string): Promise<{Entity}[]> {
  // ...
}
```

**Query-layer filtering rules (state explicitly per function):**

| Function | Filters applied at query layer | Why |
|----------|-------------------------------|-----|
| `get{Entity}ById` | `status = 'PUBLISHED'` | Public route must not leak drafts by id |
| `list{Entity}sBySection` | `status = 'PUBLISHED'`, `section = ?` | Same |

### 3.2 Ordering / Adjacency Queries (if applicable)

If the feature needs "previous/next" or similar positional lookups and rows can be
hard-deleted, `order` **will have gaps**. Design the query as nearest-greater /
nearest-lesser, never `order ± 1`:

```typescript
// prev: WHERE order < current.order ORDER BY order DESC LIMIT 1
// next: WHERE order > current.order ORDER BY order ASC LIMIT 1
```

---

## 4. Server Actions (Writes)

### 4.1 Actions List

| Action | File | Auth Required | SDS Reference |
|--------|------|---------------|---------------|
| create{Entity}Action | app/{route}/actions.ts | Admin session | Section 4.2 |
| update{Entity}Action | app/{route}/actions.ts | Admin session | Section 4.2 |
| delete{Entity}Action | app/{route}/actions.ts | Admin session | Section 4.2 |

### 4.2 Action Contract

Server Actions **must not throw for expected validation/business errors** — a thrown
error surfaces as an unhandled error boundary and, for form actions, wipes whatever the
user typed. Return a discriminated union instead:

```typescript
// app/{route}/actions.ts
// Traceability: SDS M-XX Section 4.2 [Action Name]

type ActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string; fieldErrors?: Record<string, string> };

export async function create{Entity}Action(
  input: Create{Entity}Input
): Promise<ActionResult<{Entity}>> {
  // 1. Verify session (see §6) — refresh cookie if needsSessionRefresh()
  // 2. Validate input — return { success: false, fieldErrors } on failure, don't throw
  // 3. Business rule checks (e.g. "at most one PUBLISHED row in this group")
  // 4. Write via lib/admin-{module}.ts
  // 5. revalidatePath(...) for affected routes
  // 6. Return { success: true, data }
}
```

**Flow (business rules):**
```
1. Verify session / auth
2. Validate input shape
3. [Business rule — e.g. uniqueness, single-published-item constraint, ownership]
4. Persist via data-access write function
5. Revalidate affected paths/pages
6. Return result union
```

### 4.3 Client Wiring Note

State which pattern the corresponding client component uses, and why, if the SDS's
target codebase has an established convention (e.g. `useTransition` + direct action call
vs. `useActionState` + `<form action={fn}>`) — the two are not interchangeable when a
mutating action also refreshes a session cookie, since a cookie write inside a Server
Action re-renders the current route in the same response ("seeded navigation"), which can
remount a form and lose in-progress input on a *failed* submission if the action is wired
directly as `<form action={fn}>`. Confirm the current framework behavior in
`node_modules/next/dist/docs/` before assuming either pattern is safe by default.

---

## 5. Routes / Pages (App Router)

### 5.1 Route Overview

| Route | Component Type | Auth | Rendering Mode |
|-------|----------------|------|-----------------|
| `/{route}` | Server Component | Public | `force-dynamic` (reads DB, no dynamic segment) |
| `/{route}/[id]` | Server Component | Public | Dynamic segment — no extra opt-in needed |
| `/admin/{route}` | Server Component | Admin session | `force-dynamic` |

**Rendering mode rule**: any route with **no dynamic segment** that reads the database
needs an explicit opt-out of static prerendering (e.g. `export const dynamic =
"force-dynamic"` in App Router) — otherwise Next.js may prerender it at build time and
freeze its data until the next deploy. State this per route; don't leave it implicit.

### 5.2 Server/Client Component Split

- Server Component: [what it renders, what data-access function it calls]
- Client Component (`"use client"`): [only the interactive parts — forms, buttons wired to Server Actions]

---

## 6. Auth & Session Design (if this module has protected routes)

### 6.1 Route Guard
- Where enforced: [proxy.ts / route group layout / per-page check] — confirm the current
  file name/convention for the installed Next.js version before writing this section
- Redirect target on missing/expired session: [path]

### 6.2 Session Refresh
- Session refresh must be checked in **both** places: the route guard (covers page
  navigation) **and** every mutating Server Action (covers direct action calls that
  bypass navigation). Missing either breaks "expires after N minutes idle."
- State the coalescing strategy if refreshing on every request would cause unwanted
  side effects (e.g. only re-issue the session cookie once it's past the halfway point
  to expiry, not on every request) — this avoids remounting components that shouldn't
  reset on read-only navigation.

### 6.3 Cookie Deletion (if this module has a logout/session-clear action)
- State the cookie's `path` option explicitly, and require the delete call to pass the
  **same** `path` — a delete call with a mismatched path (e.g. omitting `path` when the
  cookie was set with a non-default one) silently fails to remove it in the browser.

---

## 7. Security Design

### 7.1 Draft/Unpublished Content Leak Prevention (if applicable)
- Every public read filters by publication status **at the query layer** (§3.1), not by
  hiding it in the UI — a direct URL/id guess must not be able to retrieve unpublished
  content.

### 7.2 Input Validation
- Validate at the Server Action boundary (the trust boundary for writes) — don't rely on
  client-side validation alone.
- [Field]: [validation rule, max length, allowed values]

### 7.3 Data Security
- **Sensitive fields**: [fields] → confirm no Server Component ships them to the client
  (Server Components serialize their return value to the client bundle — don't select
  more than the page needs)
- **Injection**: Prisma parameterizes queries by default — flag any raw SQL (`$queryRaw`)
  for extra review
- **XSS**: React escapes by default — flag any `dangerouslySetInnerHTML` usage

### 7.4 Universal Security (see `design/references/security-checklist.md`)

- **Authorization**: state the full chain for any Server Action/route that touches another
  user's data — session check alone is not enough; add `resource.ownerId === session.userId`
  (or role check) before the mutation, not just before rendering
- **Secrets**: confirm no API key/DB credential is read into a Server *Component's* return
  value (it serializes to the client) — secrets belong in Server Actions/route handlers only,
  sourced from env vars
- **Business security**: for any state-changing Server Action on a financial/limited resource,
  name the concurrency control (Prisma transaction + row lock, or optimistic `updatedAt`/version
  check) and, if it's a payment/transfer-like action, the idempotency mechanism
- **CSRF**: Server Actions carry Next.js's built-in Origin-check CSRF protection — state that
  this is relied on rather than a custom token scheme, unless the feature needs cross-origin
  form posts (rare) in which case state the exception
- **Error handling**: confirm the Server Action's error union (§8.1) never surfaces a
  Prisma/driver error message — map to a generic message client-side, log the detail
- **Security testing**: test plan covers unauthenticated (no session), unauthorized (wrong
  owner), expired session, and — for the draft-leak concern in §7.1 — a direct id guess against
  unpublished content

---

## 8. Error Handling

### 8.1 Server Action Error Contract
See §4.2 — result union, not thrown exceptions, for expected errors. Reserve thrown
exceptions for truly unexpected failures, and still catch at the Action boundary.

### 8.2 Error → UI Mapping

| Error Case | `fieldErrors` / `error` | UI Behavior |
|-----------|------------------------|-------------|
| Validation failure | `fieldErrors: { field: message }` | Inline field error, form data preserved |
| Business rule violation (e.g. duplicate) | `error: message` | Toast/banner, form data preserved |
| Not found (edit/delete stale id) | `error: "not found"` | Redirect or banner |
| Unauthorized/session expired | N/A — redirect via route guard | Redirect to login |

---

## 9. Performance Design

### 9.1 Caching / Revalidation
- `revalidatePath("/route")` after each mutation that affects that route's list/detail view
- Note any route relying on the Next.js fetch/data cache and its invalidation trigger

### 9.2 Query Efficiency
- Use Prisma `select`/`include` to fetch only needed fields — avoid over-fetching on list views
- Flag any N+1 risk (e.g. looping a query per row) — prefer a single query with `include`

### 9.3 Pagination / Ordering
- Default page size: [N]; max: [N]
- `order` field gap handling — see §3.2

### 9.4 Universal Performance (see `design/references/performance-checklist.md`)

- **Performance baseline**: state expected concurrent readers/RPS and P95 latency target — mark `[PERF TARGET NEEDED]` if the SRS doesn't specify one
- **Transaction scope**: any multi-step Prisma write (`$transaction`) states that no external HTTP call happens inside it — Next.js Server Actions make this easy to accidentally do since the transaction and the call are just sequential lines in one function
- **Timeout**: any external API this Server Action calls states connect/read/overall timeout, and retry (if any) states bound + backoff + jitter
- **Memory**: any list/export route that could return a large row count uses `select`/`include` narrowing (§9.2) plus a hard cap — never an unbounded `findMany()`
- **Cache stampede**: if §9.1's revalidation strategy relies on Next.js's data cache for a hot route, state whether a stampede on revalidation (many concurrent requests missing the cache at once) is a concern for this route's traffic level

---

## 10. Distributed & Async Design

> Full checklist: `design/references/distributed-systems-checklist.md`. This app is a single
> deployable talking to one Postgres DB via Prisma — most distributed-systems concerns (data
> ownership across services, Saga, message ordering) don't apply here. Fill this section only
> if this module does one of: calls an external system whose response can be lost on timeout
> (payment gateway, third-party API), receives a webhook, or queues work for a background
> worker. Otherwise state "N/A — single service, no external async dependency" and skip to Test Plan.

### 10.1 Idempotency (if this Server Action can be submitted twice, or receives a webhook)

- **Idempotency key**: [client-generated key on the mutation form | webhook's own event ID] checked before applying the effect — a second submission/delivery with the same key is a no-op, not a duplicate write
- **Webhook signature/replay**: if receiving a webhook, state that the signature is verified and the event ID is deduplicated before processing

### 10.2 Unknown Result (if this Server Action calls an external system, e.g. a payment gateway)

- A timeout/network error from the external call does **not** set the record to a terminal
  `FAILED` state — it goes to `PENDING`/`UNKNOWN`, resolved by [a status-check call | the
  provider's webhook | a reconciliation script] — never a blind retry that could double-charge

---

## 11. Test Plan

### 11.1 Data-Access Unit Tests (`lib/{module}.test.ts`)

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `get_published_only` | Draft + published rows exist | Draft excluded |
| `get_by_id_not_found` | Invalid id | Returns null |
| `prev_next_with_gap` | Middle row deleted | Neighbors still resolve correctly |

**Note**: if these tests run against a real dev database (common when there's no
separate test DB), state that explicitly and specify the `beforeEach`/`afterEach`
cleanup strategy — and warn that running the suite wipes seed data other manual testing
depends on.

### 11.2 Server Action Tests

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `create_success` | Valid input, valid session | `{success: true}`, row persisted |
| `create_validation_error` | Missing required field | `{success: false, fieldErrors}` |
| `create_no_session` | No/expired session | Rejected before write |

### 11.3 Component Tests
- Note the test environment directive needed (e.g. jsdom vs. node) if any library used
  by a Server Component or its dependencies does an `instanceof` check that fails under
  a browser-like realm.

### 11.4 SRS Traceability

| SRS Requirement | Implemented In |
|----------------|---------------|
| FR-01: [requirement] | Server Action: [name], Route: [path] |
| FR-02: [requirement] | Prisma field: [field] |
| BR-01: [business rule] | Server Action validation logic |
```

---

## NAMING CONVENTIONS (MODE C)

Discover exact conventions from CLAUDE.md — below are typical patterns:

- SDS path: Glob `docs/04-sds/` (or project equivalent) → compute next M-XX
- Module ID: `M-XX` (project-specific numbering)
- Data-access module: `lib/{module}.ts` (reads), `lib/admin-{module}.ts` (writes) or similar read/write split
- Server Action file: colocated `actions.ts` next to the route, or `app/actions/{name}.ts` for standalone actions
- Prisma model: PascalCase; fields camelCase

---

## ARCHITECTURE RULES (MODE C)

**Layer boundaries (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|---------------|
| Prisma schema | — | Application code |
| `lib/*.ts` (data-access) | Prisma client, other `lib/*.ts` | `app/**` (no upward imports) |
| Server Component (`page.tsx`) | `lib/*.ts` | Prisma client directly (route through data-access) |
| Server Action (`actions.ts`) | `lib/*.ts`, auth helpers | — |
| Client Component (`"use client"`) | Server Actions (as function references), UI-only lib code | Prisma client, DB credentials, server-only secrets |

**Why route Server Components through `lib/*.ts` instead of calling Prisma directly**:
same reason MODE B keeps handlers out of the database — a shared, named function is
where query-layer filtering (draft leak prevention), ownership boundaries, and test
coverage all live. A component that queries Prisma inline duplicates that logic per
call site and is easy to get wrong once, silently.

**Split ownership on shared models**: when two features share a Prisma model, document
in the SDS which fields each one may write (§2.1) and enforce it in code review, not
just in comments — a write to a field owned by another feature is a design defect even
if the schema technically allows it.

**SDS Traceability Comment (required in generated code):**
```typescript
// Traceability: SDS M-XX Section Y.Z [Action/Function Name]
export async function createVideoAction(...) { ... }
```

**SDS Design Principle:**
Design from the Prisma model (Entity) outward → don't design the route/page first and only think about the data model afterward.
