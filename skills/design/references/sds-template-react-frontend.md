# SDS Template I: React SPA Frontend Feature

> Reference for `design` skill — loaded on demand when creating MODE I SDS documents.
>
> **First, confirm this is genuinely a client-rendered React SPA, not a Next.js App Router
> project** (`package.json` has `react` but not `next`) — a Next.js project is MODE C instead,
> which has its own colocated data-access/Server Action discipline. Also confirm which
> data-fetching library the project already uses (React Query, SWR, or a hand-rolled
> fetch-in-`useEffect` pattern to migrate away from) and which client-state approach (Context,
> Zustand, Redux) — match the existing choice, don't introduce a second one for this feature alone
> without a stated reason.

---

## TEMPLATE I: React SPA Frontend Feature SDS

```markdown
# M-XX: [Feature Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: {tech_stack — React version, data-fetching library, client-state library, router}

---

## 1. Feature Overview

### 1.1 Description
[Describe what this feature does and where it sits in the app's route tree]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Scale Tier**: N/A in the backend sense — this feature is a client screen, not a deployed
service. State instead whether it needs offline support or local-persistence sync (rare); if not,
say so explicitly rather than leaving Section 10/11 silently blank.

### 1.3 Architecture Layer
```text
src/
├── app/                          # providers, router setup, app-wide config
├── shared/                       # cross-cutting UI kit, utilities, types (2+ features)
└── features/{feature}/
    ├── components/               # composed components for this feature
    ├── hooks/                    # data-fetching + feature-specific logic hooks
    ├── api/                      # this feature's API call functions
    └── types.ts
```

**Components**: [List top-level + composed components]
**Hooks**: [List data-fetching hooks and their cache keys]
**Dependencies**: [e.g. `shared/api/http-client.ts`, `app/auth-context.tsx`]

---

## 2. Architecture Context

Classify every touched piece **Existing** / **Modified** / **New** / **External**:

| Component | Classification | Reason |
|-----------|-----------------|--------|
| [e.g. `useOrders` hook] | New | No existing hook owns this feature's data |
| [e.g. `app/auth-context.tsx`] | Existing | Reused for session/token access, not modified |

---

## 3. Backend API Contract

> Read the actual backend SDS (or an existing API client in `shared/api/`) before filling this
> in. Never invent an endpoint's request/response shape — mark
> `[NEEDS BACKEND SDS — M-YY not found]` and stop guessing if it doesn't exist yet.

| Endpoint | Method | Request Shape | Response Shape | Auth |
|----------|--------|----------------|------------------|------|
| `/api/v1/[resource]` | GET | Query params: [...] | `{ data: [...], meta: {...} }` | Bearer |
| `/api/v1/[resource]` | POST | `{ [field]: ... }` | `{ id, ... }` or `{ error }` | Bearer |

**Error contract**: [state the shape the backend returns on 4xx/5xx — e.g.
`{ code, message, fieldErrors? }` — so the hook's error branch has something concrete to map, not
an assumed shape]

---

## 4. Data-Fetching Hook Design

### 4.1 Hook Signature and Cache Key

```typescript
// features/{feature}/hooks/use-{feature}.ts
// Traceability: SDS M-XX Section 4.1
function use[Feature](params: [Feature]Params) {
  return useQuery({
    queryKey: ['[feature]', params],       // cache key — every param that changes the result belongs here
    queryFn: () => fetch[Feature](params), // calls the API function, never inlines fetch here
    staleTime: [duration],                  // how long cached data is considered fresh
  });
}
```

### 4.2 Cache Invalidation

| Mutation | Invalidates Query Key(s) | Trigger |
|----------|---------------------------|---------|
| `create[Feature]` | `['[feature]']` | On mutation success |
| `update[Feature]` | `['[feature]', id]` | On mutation success |

A mutation with no stated invalidation is a `[DESIGN GAP]` — state explicitly if it's meant to be
optimistic-update-only with no refetch.

---

## 5. Client/Local State Design

Separate **server state** (§4 — owned by the data-fetching hook, never duplicated into
`useState`) from **client state** (UI-only: a modal open/closed, a form's current values, a
selected tab):

| State | Type | Owner | Lifted To |
|-------|------|-------|-----------|
| [e.g. `isEditModalOpen`] | Client | `useState` in `{Feature}Page` | Not lifted — local to the page |
| [e.g. selected filter] | Client | `useState` | Lifted to `{Feature}Page` because both list and toolbar need it |

Reach for Context only for genuinely cross-cutting concerns (theme, auth session) already
established elsewhere in the app — introducing a new Context for this feature's own state is a
`[DESIGN DECISION]` that needs a stated reason, not a default.

---

## 6. Component Design

### 6.1 Component Composition

| Component | Props | Notes |
|-----------|-------|-------|
| `{Feature}Page` | — (route-level) | Composes the components below, owns client state from §5 |
| `{Feature}List` | `items: [Entity][]`, `onSelect: (item) => void` | No data-fetching, no business logic |
| `{Feature}Form` | `initial: [Entity] \| null`, `onSubmit: (values) => void` | Validation rules stated in §6.3 |

### 6.2 Custom Hooks (behavior, not markup)

`use[Feature]` — data fetching (§4). Any additional feature-specific behavior hook
(`use[Feature]Filters`, etc.) is listed here with what it encapsulates — a custom hook is for
reusable *logic*, not reusable UI.

### 6.3 Screen States (every screen must render all four explicitly)

| State | Trigger | Rendering |
|-------|---------|-----------|
| Loading | `query.isLoading` | [e.g. skeleton/spinner] |
| Empty | `query.isSuccess && data.length === 0` | [empty-state component + CTA] |
| Error | `query.isError` | [error message + retry action] |
| Success | `query.isSuccess && data.length > 0` | [list/detail render] |

---

## 7. Routing

| Route | Path | Guard | Loaded From |
|-------|------|-------|-------------|
| [Feature] list | `/[feature]` | [e.g. `<RequireAuth>`] | `features/{feature}/{Feature}Page.tsx`, code-split via `lazy()` |

---

## 8. Accessibility Design

- **Keyboard navigation**: [tab order through interactive elements; any custom focus management
  on state transitions — e.g. focus moves to the error message on load failure]
- **Screen reader**: [`aria-live` regions for async state changes — a loading→error transition
  with no `aria-live="polite"` region is invisible to a screen-reader user]
- **Touch targets / contrast**: [minimum tap target size, contrast ratio if this introduces new
  custom-styled controls]

If the SRS states no explicit a11y target, mark `[A11Y TARGET NOT STATED — following WCAG 2.1 AA
as the project default]` rather than silently skipping this section.

---

## 9. Client Security Design

> Client-relevant subset of `references/security-checklist.md` only — the server-side subset
> (SQL injection, rate limiting) is the backend SDS's concern, not this one.

- **Token storage**: [where the access/refresh token lives — memory + httpOnly cookie is
  preferred over `localStorage` for XSS resistance; state which this project uses and why]
- **XSS**: [confirm no `dangerouslySetInnerHTML` binds unsanitized user-controlled content; React
  escapes JSX text by default — call out any place that opts out]
- **Open redirect / deep-link validation**: [if this feature reads a redirect target from a query
  param, state the allowlist/validation — never navigate to an unvalidated absolute URL]

---

## 10. Client Performance Design

> Client-relevant subset of `references/performance-checklist.md` only.

- **Code-splitting**: confirm this feature's route component is loaded via `lazy()`, not pulled
  into the initial bundle
- **List rendering**: [a stable `key` per item — never array index for a reorderable/filterable
  list; virtualization (`react-window`/`react-virtual`) if the list can grow unbounded]
- **Re-render scope**: [state which components are memoized (`memo`/`useMemo`/`useCallback`) and
  why — memoizing everything by default is its own anti-pattern; state the actual re-render
  problem being solved, if any]

---

## 11. Data Integrity

**N/A** unless this feature owns local persistent state (e.g. IndexedDB) that must stay consistent
with the server. If N/A, say so explicitly.

## 12. Operations Readiness

**N/A** — a client app isn't a deployed service. If the SRS mentions crash/error monitoring (e.g.
Sentry), note the integration point here instead.

---

## 13. Test Plan

### 13.1 Hook Tests (mocked API client / MSW, no real HTTP)

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `loads successfully` | API returns data | `query.data` populated, `isSuccess` true |
| `loads empty` | API returns `[]` | `query.data` is `[]`, `isSuccess` true |
| `loads error` | API rejects | `query.isError` true, `query.error` set |
| `mutation success` | API resolves | Related query key invalidated/refetched |
| `mutation failure` | API rejects | Error surfaced, form input preserved |

### 13.2 Component Tests (per screen state, React Testing Library)

| Test Case | State | Assertion |
|-----------|-------|-----------|
| Loading renders | loading | Spinner/skeleton element present |
| Empty renders | success, empty | Empty-state + CTA present |
| Error renders | error | Error message + retry action present, retry re-invokes the query |
| Success renders | success, data | List/detail content matches mocked data |

### 13.3 SRS Traceability

| SRS Requirement | Implemented In |
|-------------------|------------------|
| FR-01: [requirement] | Hook: `use[Feature]`, Component: `{Feature}Page` |
| BR-01: [business rule] | Form validation / hook guard logic |

---

## 14. Design Decisions & Alternatives

Per `.claude/skills/design/references/decision-records.md` §2 — record any costly-to-reverse
choice (e.g. React Query vs. SWR, Context vs. a lightweight store for this feature's client
state) with alternatives considered and why this one won.

## 15. Risks & Trade-offs

[State risks — e.g. "no offline support; feature unusable without connectivity" — and whether
that's accepted or deferred.]

## 16. Implementation Mapping

| SDS Section | Implementation File |
|--------------|---------------------|
| §4 Data-fetching hook | `features/{feature}/hooks/use-{feature}.ts` |
| §6 Components | `features/{feature}/components/{Feature}Page.tsx` |
| §3 API functions | `features/{feature}/api/{feature}.api.ts` |

## 17. Implementation Readiness

**Status**: [READY | PARTIALLY_READY | BLOCKED]
[State any `[NEEDS BACKEND SDS]`/`[NEEDS SPEC CLARIFICATION]`/`[A11Y TARGET NOT STATED]` items and
what `/implement` can start on now vs. what's blocked.]
```

---

## NAMING CONVENTIONS (MODE I)

Discover exact conventions from the project's existing feature folders/CLAUDE.md — below are
typical patterns:

- SDS path: `docs/04-sds/M-XX-module-name.md`
- Feature folder: `features/{feature}/` (kebab-case)
- Data-fetching hook: `use{Feature}` (camelCase, `use` prefix required by the Rules of Hooks)
- Page/route component: `{Feature}Page`
- Composed component: `{Feature}{Purpose}` (e.g. `OrderList`, `OrderForm`)
- API function file: `features/{feature}/api/{feature}.api.ts`, never inlined in a component
- Test file: `{Name}.test.tsx` colocated with the file under test

---

## LAYERING RULES (MODE I)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|----------------|
| Presentational component | Props, `shared/ui-kit` | Data-fetching hooks, `fetch`/HTTP client directly |
| Page/container component | Data-fetching hooks, presentational components | HTTP client directly, another feature's internal hook |
| Data-fetching hook | API function, React Query/SWR | Component types |
| API function (`features/*/api/*`) | Shared HTTP client, DTOs | Hooks, components |

**Data-Fetching Hook Pattern:**
```typescript
// Server state lives behind a hook — components never call fetch/axios directly,
// and never hand-roll cache/loading/error state that a data-fetching library already owns
export function use[Feature](params: [Feature]Params) {
  return useQuery({ queryKey: ['[feature]', params], queryFn: () => fetch[Feature](params) });
}
```

**Component Rule:**
- A component that calls `fetch`/`axios` directly, or hand-rolls loading/error state instead of
  reading it off the query hook, is a layering violation — move it into a data-fetching hook.

**SDS Traceability Comment (required):**
```typescript
// Traceability: SDS M-XX Section Y.Z [Hook/Function Name]
export function use[Feature](...) { ... }
```

**SDS Design Principle:**
Design from the backend API contract outward (API contract → Data-fetching hook → Client state →
Component composition → Route) — the same inside-out discipline as the backend modes, adapted to
a client app. Don't design the component tree first and only think about where its data comes
from afterward.
