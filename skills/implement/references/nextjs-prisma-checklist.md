# Implement Skill — Next.js + Prisma Reference Material

> Load this when implementing in a Next.js (App Router) + Prisma codebase. It complements
> `verification-checklist.md` — that file's language-agnostic checklist (linting, testing,
> secrets scan, docs) still applies; this file adds the traps specific to this stack.
>
> **First, verify versions.** Next.js and Prisma have both shipped breaking changes across
> major versions recently (Next.js: `middleware.ts` → `proxy.ts`, Edge runtime dropped from
> middleware; Prisma: generator name, datasource URL location, mandatory driver adapters).
> Check `node_modules/next/dist/docs/` and the installed Prisma version's docs/changelog
> before writing code that assumes an older API shape — this is the single most common
> source of wasted implementation time in this stack.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ Server Action that throws for expected errors

```typescript
export async function createVideoAction(input: CreateVideoInput) {
  if (!input.title) {
    throw new Error("Title is required"); // surfaces as an error boundary,
  }                                        // and wipes the form on failure
  return db.video.create({ data: input });
}
```

### ✅ Server Action returning a result union

```typescript
type ActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string; fieldErrors?: Record<string, string> };

export async function createVideoAction(
  input: CreateVideoInput
): Promise<ActionResult<Video>> {
  if (!input.title) {
    return { success: false, error: "validation failed", fieldErrors: { title: "Required" } };
  }
  try {
    const video = await db.video.create({ data: input });
    return { success: true, data: video };
  } catch (err) {
    console.error("createVideoAction failed", err);
    return { success: false, error: "Could not create video" };
  }
}
```

**Why this is better:** the client component can distinguish "expected validation failure —
keep what the user typed" from "truly unexpected failure", and never has to unmount the
form to show an error.

---

### ❌ Public read with no query-layer status filter (draft leak)

```typescript
export async function getVideoById(id: string) {
  return db.video.findUnique({ where: { id } }); // returns drafts too — anyone
}                                                  // who guesses/enumerates an id can read them
```

### ✅ Filtering at the query layer

```typescript
export async function getVideoById(id: string) {
  return db.video.findFirst({ where: { id, status: "PUBLISHED" } });
}
```

**Why this is better:** the visitor-facing route can never leak an unpublished row by id,
regardless of what the UI does or doesn't render — the guarantee lives in the query, not
in a component-level check that's easy to forget on a new route.

---

### ❌ `order ± 1` adjacency lookup on a table with hard deletes

```typescript
const next = await db.video.findFirst({ where: { order: current.order + 1 } });
// returns null once the row that used to sit at order+1 is deleted — even though
// a "next" video still exists further down
```

### ✅ Nearest-neighbor lookup

```typescript
const next = await db.video.findFirst({
  where: { order: { gt: current.order } },
  orderBy: { order: "asc" },
});
```

---

### ❌ Cookie delete with mismatched path

```typescript
cookies().delete(SESSION_COOKIE_NAME); // defaults to path: "/" —
// if the cookie was SET with path: "/admin", the browser won't remove it;
// the user stays logged in after "logout"
```

### ✅ Delete with the same path the cookie was set with

```typescript
cookies().delete({ name: SESSION_COOKIE_NAME, path: SESSION_COOKIE_OPTIONS.path });
```

**Why this is better:** a browser only overwrites/removes a cookie when the delete's `path`
matches the one it was set with exactly. This applies to `NextResponse.cookies.delete`
too, not just `cookies().delete`.

---

### ❌ Refreshing a sliding-session cookie unconditionally on every Server Action

```typescript
export async function updateVideoAction(input: UpdateVideoInput) {
  await refreshSessionCookie(); // runs on EVERY call, including a failed validation —
  // and a Server Action that mutates a cookie makes Next.js re-render the current route
  // in the same response ("seeded navigation"), remounting the form and wiping user input
  ...
}
```

### ✅ Coalesce the refresh — only re-issue once meaningfully stale

```typescript
export async function updateVideoAction(input: UpdateVideoInput) {
  const session = await getSessionFromCookies();
  if (needsSessionRefresh(session)) {
    await refreshSessionCookie(); // only once past the halfway point to expiry
  }
  ...
}
```

**Why this is better:** a normal save-then-fix-and-retry cycle never touches the cookie, so
a failed save never remounts the form. If you also need `useActionState` +
`<form action={fn}>` for a mutating action, know that this remount risk exists
independent of the coalescing — verify the current framework behavior in
`node_modules/next/dist/docs/` before wiring a form that way when the action also
touches cookies.

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — Next.js + Prisma specifics slot in as
follows:

### **P0 - Critical**
- Query-layer filtering for anything that must not leak unpublished/private data
- Auth/session check in every mutating Server Action, not just the route guard
- Server Action input validation (the trust boundary for writes — client-side validation is not enough)
- Ownership boundaries respected on shared Prisma models (don't write a field another feature owns)

### **P1 - High**
- Server Action error contract (`{success, data|error, fieldErrors?}`) — not thrown exceptions for expected failures
- Cookie `path` consistency between set and delete
- Rendering mode (`force-dynamic`/revalidation) set correctly for DB-backed routes with no dynamic segment

### **P2 - Medium**
- Tests for data-access functions (including the DB-sharing caveat below) and Server Actions
- `revalidatePath`/`revalidateTag` after mutations that affect other views

### **P3 - Low**
- Query `select`/`include` narrowing to avoid over-fetching
- N+1 query cleanup

---

## VERIFICATION CHECKLIST (Next.js + Prisma additions)

Run these in addition to the general checklist:

### 1. Code Quality
```bash
npx tsc --noEmit
pnpm lint   # or npm/yarn equivalent — eslint-config-next
```
- [ ] No `any` introduced where the Prisma-generated type already covers it
- [ ] Imports from the generated Prisma client match the configured output path (varies by Prisma version — check `prisma.config.ts` / `schema.prisma` generator block, don't assume `@prisma/client`)

### 2. Correctness
- [ ] Every DB-backed page/route with no dynamic segment has an explicit rendering-mode opt-out if it needs fresh data
- [ ] Every "prev/next"/positional lookup handles gaps (nearest-neighbor, not `±1`)
- [ ] Shared-model writes only touch fields this feature owns

### 3. Security
- [ ] Every public read that must hide unpublished/draft/private rows filters at the query layer, verified by reading the actual `where` clause — not assumed from the UI
- [ ] Every Server Action that mutates another user's/owner's resource checks `resource.ownerId === session.userId` (or role) before writing — not just that a session exists
- [ ] Cookie delete calls pass the same `path` the cookie was set with
- [ ] No secret/credential field is selected into a Server Component's return value if the component ships it to the client
- [ ] Any raw SQL (`$queryRaw`/`$executeRaw`) is parameterized, not string-interpolated
- [ ] A state-changing Server Action on a financial/limited resource implements the concurrency-control/idempotency mechanism the SDS named (transaction + row lock, or optimistic version check)
- [ ] The Server Action's error union never surfaces a raw Prisma/driver error message to the client

```bash
git grep -iE "(password|secret|api_key|token)\s*=" -- '*.ts' '*.tsx'
git grep -inE "console\.(log|debug|warn|error)\(.*\b(password|token|otp)\b" -- '*.ts' '*.tsx'
```

Full checklist (SSRF, file upload, secrets storage, dependency scan, mandatory security test
cases): `references/security-implementation-checklist.md`.

### 4. Testing
```bash
pnpm test
```
- [ ] If tests share a real dev database (no separate test DB), cleanup hooks (`beforeEach`/`afterEach`/`afterAll`) are present and the project's re-seed step is run afterward before manual testing
- [ ] Component tests that need a browser-like DOM declare it explicitly (e.g. a `// @vitest-environment jsdom` docblock) rather than relying on a global default, since some server-side libraries fail under that realm
- [ ] Server Action tests cover: success, validation failure (check `fieldErrors` shape), missing/expired session, unauthorized (wrong owner → error result, not a thrown exception)

### 5. Performance
- [ ] `select`/`include` narrowed to what the page actually renders on list views
- [ ] No query issued inside a loop where a single `include`/`in` query would do
- [ ] Mutations that affect other cached views call `revalidatePath`/`revalidateTag`
- [ ] No `prisma.$transaction([...])`/interactive transaction calls an external `fetch`/API client inside its callback
- [ ] Any external `fetch` this Server Action makes passes an `AbortController`-based timeout — `fetch` has no default timeout
- [ ] Any list/export route that could return a large row count has a hard cap on `take`, not just a default

```bash
# query-in-loop candidates
grep -n -B2 "prisma\.\w*\.find" -- '*.ts' | grep -B2 "for (\|while (\|forEach\|\.map("
```

Full checklist (connection-pool sizing, cache stampede, memory streaming, anti-pattern sweep):
`references/performance-implementation-checklist.md`.

### 6. Distributed & Async (only if this Server Action calls an external system or receives a webhook)
- [ ] A Server Action calling a payment gateway/external API treats a timeout as `UNKNOWN`/`PENDING`, not `FAILED` — a blind retry on timeout could double-charge if the provider actually succeeded
- [ ] A webhook route handler verifies the provider's signature and dedupes by the webhook's own event ID before applying an effect — a webhook redelivery must be a no-op, not a duplicate write
- [ ] A mutation with a client-supplied idempotency key actually checks it server-side before writing, not just accepts and ignores it

Most modules in this app are plain single-service CRUD and this section is N/A. Full checklist:
`references/distributed-systems-implementation-checklist.md`.

---

## TROUBLESHOOTING

**Server Action "works" but the form loses input on a failed submit:**
Check whether the action throws for that error path (should return a result union
instead), and whether it touches `cookies()` unconditionally (should coalesce via a
`needsSessionRefresh`-style check). Both cause a remount via seeded navigation.

**A route's data looks frozen / doesn't reflect the latest DB write:**
Check whether the route has a dynamic segment or an explicit dynamic-rendering opt-out.
No dynamic segment + no opt-out = Next.js may have prerendered it at build time.

**Logout doesn't actually log the user out:**
Check the cookie's `path` option where it was set vs. where it's deleted — a mismatch is
the most common cause, and it fails silently (no error, cookie just isn't removed).

**A library throws inside a component test but works at runtime:**
Check the test environment. Vitest's default is often `"node"`, not `"jsdom"` — a
library doing an `instanceof` check (e.g. a JWT/crypto library) can fail under jsdom's
separate realm, or vice versa depending on which environment the library assumes.

**An API you're calling doesn't exist / behaves differently than expected:**
Don't debug in the dark — read `node_modules/next/dist/docs/` (or the equivalent for
Prisma) for the installed version first. This is faster than trial-and-error against
training-data assumptions that may predate the installed major version.
