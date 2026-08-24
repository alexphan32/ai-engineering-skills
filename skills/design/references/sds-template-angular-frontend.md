# SDS Template H: Angular Frontend Feature

> Reference for `design` skill — loaded on demand when creating MODE H SDS documents.
>
> **First, confirm the project's Angular version and component style** (`angular.json`/
> `package.json`): standalone components (Angular 14+, no `NgModule` boilerplate) vs. an
> `NgModule`-based codebase — match whichever the project already uses, don't default to
> standalone from training-data recency bias. Also confirm the state-management approach already
> in use (a plain service + `BehaviorSubject`/signal vs. NgRx/Akita) before proposing a new one.

---

## TEMPLATE H: Angular Frontend Feature SDS

```markdown
# M-XX: [Feature Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: {tech_stack — Angular version, standalone vs. NgModule, state approach, UI kit}

---

## 1. Module Overview

### 1.1 Description
[Describe what this feature does and where it sits in the app's navigation/feature tree]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Scale Tier**: N/A in the backend sense — this feature is a client screen, not a deployed
service. State instead whether it needs offline support or local-persistence sync (rare); if not,
say so explicitly rather than leaving Section 10/11 silently blank.

### 1.3 Architecture Layer
```text
src/app/
├── core/                        # singleton services, guards, interceptors (imported once)
├── shared/                      # reusable dumb components/pipes/directives (2+ features)
└── features/{feature}/
    ├── components/              # smart container + presentational components
    ├── services/                # this feature's state service(s)
    └── {feature}.routes.ts      # lazy-loaded route(s)
```

**Components**: [List container + presentational components]
**Routes**: [List route paths and their lazy-load boundary]
**Dependencies**: [e.g. `core/auth.service.ts` for session, `shared/ui-kit` for buttons/inputs]

---

## 2. Architecture Context

Classify every touched piece **Existing** / **Modified** / **New** / **External**:

| Component | Classification | Reason |
|-----------|-----------------|--------|
| [e.g. `OrdersStateService`] | New | No existing service owns this feature's state |
| [e.g. `core/auth.service.ts`] | Existing | Reused for session/token access, not modified |

---

## 3. Backend API Contract

> Read the actual backend SDS (or an existing API client in `core/api/` or `shared/api/`) before
> filling this in. Never invent an endpoint's request/response shape — mark
> `[NEEDS BACKEND SDS — M-YY not found]` and stop guessing if it doesn't exist yet.

| Endpoint | Method | Request Shape | Response Shape | Auth |
|----------|--------|----------------|------------------|------|
| `/api/v1/[resource]` | GET | Query params: [...] | `{ data: [...], meta: {...} }` | Bearer |
| `/api/v1/[resource]` | POST | `{ [field]: ... }` | `{ id, ...} ` or `{ error }` | Bearer |

**Error contract**: [state the shape the backend returns on 4xx/5xx — e.g.
`{ code, message, fieldErrors? }` — so the state service's error branch has something concrete to
map, not an assumed shape]

---

## 4. State Service Design

### 4.1 State Shape

```typescript
// features/{feature}/services/{feature}-state.service.ts
// Traceability: SDS M-XX Section 4.1
interface [Feature]State {
  status: 'idle' | 'loading' | 'success' | 'error';
  data: [Entity][] | null;
  error: string | null;
}
```

### 4.2 Service Responsibilities

- Calls the API client (never `HttpClient` directly from a component)
- Exposes state via a `BehaviorSubject<[Feature]State>` (or a signal, if the project already uses
  Angular signals) — components read via the `async` pipe or the signal directly, never a raw
  manual `.subscribe()`
- [List each state-mutating method and what triggers it]

### 4.3 Subscription/Cleanup Discipline

State every place a subscription is created and how it's torn down (`async` pipe preferred;
`takeUntilDestroyed()` for anything that must live in a constructor/`ngOnInit`). A method with no
stated cleanup path is a `[DESIGN GAP]`, not an implicit "Angular handles it."

---

## 5. Component Design

### 5.1 Smart Container Component

`{Feature}Component` — fetches/triggers state loading, holds no presentational markup logic
beyond composing the presentational components below, passes data down via `@Input`, receives
events via `@Output`.

### 5.2 Presentational Components

| Component | `@Input()`s | `@Output()`s | Notes |
|-----------|-------------|--------------|-------|
| `{Feature}ListComponent` | `items: [Entity][]` | `select: [Entity]` | No business logic, no service injection |
| `{Feature}FormComponent` | `initial: [Entity] \| null` | `submit: [FormValue]` | Validation rules stated in §5.3 |

### 5.3 Screen States (every screen must render all four explicitly)

| State | Trigger | Rendering |
|-------|---------|-----------|
| Loading | `status === 'loading'` | [e.g. skeleton/spinner] |
| Empty | `status === 'success' && data.length === 0` | [empty-state component + CTA] |
| Error | `status === 'error'` | [error message + retry action] |
| Success | `status === 'success' && data.length > 0` | [list/detail render] |

---

## 6. Routing / Lazy-Load Boundary

| Route | Path | Guard | Lazy-loaded from |
|-------|------|-------|--------------------|
| [Feature] list | `/[feature]` | [e.g. `authGuard`] | `features/{feature}/{feature}.routes.ts` |

State whether this route is added to an existing lazy-loaded feature route file or needs a new
one — don't add a route to the eagerly-loaded root routes without a stated reason.

---

## 7. Accessibility Design

- **Keyboard navigation**: [tab order through interactive elements; any custom focus management
  on state transitions — e.g. focus moves to the error message on load failure]
- **Screen reader**: [`aria-label`/`aria-live` regions for async state changes — a loading→error
  transition with no `aria-live="polite"` region is invisible to a screen-reader user]
- **Touch targets / contrast**: [minimum tap target size, contrast ratio if this introduces new
  custom-styled controls]

If the SRS states no explicit a11y target, mark `[A11Y TARGET NOT STATED — following WCAG 2.1 AA
as the project default]` rather than silently skipping this section.

---

## 8. Client Security Design

> Client-relevant subset of `references/security-checklist.md` only — the server-side subset
> (SQL injection, rate limiting) is the backend SDS's concern, not this one.

- **Token storage**: [where the access/refresh token lives — memory + httpOnly cookie is
  preferred over `localStorage` for XSS resistance; state which this project uses and why]
- **XSS**: [confirm no `[innerHTML]`/`bypassSecurityTrustHtml` binds unsanitized user-controlled
  content; Angular's default interpolation already escapes, call out any place that opts out]
- **Open redirect / deep-link validation**: [if this feature reads a redirect target from a query
  param, state the allowlist/validation — never navigate to an unvalidated absolute URL]

---

## 9. Client Performance Design

> Client-relevant subset of `references/performance-checklist.md` only.

- **Bundle/lazy-load**: confirm this feature's route is lazy-loaded, not pulled into the initial
  bundle
- **List rendering**: [`@for`/`*ngFor` with `trackBy`/`track` for any list of non-trivial size;
  virtual scrolling (`cdk-virtual-scroll-viewport`) if the list can grow unbounded]
- **Change detection**: [state whether this feature's components use `OnPush` — if not, state why
  default change detection is acceptable here]

---

## 10. Data Integrity

**N/A** unless this feature owns local persistent state (e.g. IndexedDB via a library) that must
stay consistent with the server. If N/A, say so explicitly.

## 11. Operations Readiness

**N/A** — a client app isn't a deployed service. If the SRS mentions crash/error monitoring (e.g.
Sentry), note the integration point here instead.

---

## 12. Test Plan

### 12.1 State Service Unit Tests (fake API client, no real HTTP)

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `loads successfully` | API client returns data | State becomes `success` with data |
| `loads empty` | API client returns `[]` | State becomes `success` with empty data |
| `loads error` | API client throws | State becomes `error` with message |
| `submit success` | API client resolves | State reflects updated data |
| `submit failure` | API client rejects | State becomes `error`, form input preserved |

### 12.2 Component Tests (per screen state)

| Test Case | State | Assertion |
|-----------|-------|-----------|
| Loading renders | `loading` | Spinner/skeleton element present |
| Empty renders | `success`, empty | Empty-state + CTA present |
| Error renders | `error` | Error message + retry action present, retry re-invokes load |
| Success renders | `success`, data | List/detail content matches fake data |

### 12.3 SRS Traceability

| SRS Requirement | Implemented In |
|-------------------|------------------|
| FR-01: [requirement] | Service method: [name], Component: `{Feature}Component` |
| BR-01: [business rule] | State service validation/guard logic |

---

## 13. Design Decisions & Alternatives

Per `.claude/skills/design/references/decision-records.md` §2 — record any costly-to-reverse
choice (e.g. `BehaviorSubject` vs. signals for this feature's state, standalone vs. `NgModule`,
whether NgRx is justified here) with alternatives considered and why this one won.

## 14. Risks & Trade-offs

[State risks — e.g. "no offline support; feature unusable without connectivity" — and whether
that's accepted or deferred.]

## 15. Implementation Mapping

| SDS Section | Implementation File |
|--------------|---------------------|
| §4 State service | `features/{feature}/services/{feature}-state.service.ts` |
| §5 Components | `features/{feature}/components/{feature}.component.ts` |
| §6 Routes | `features/{feature}/{feature}.routes.ts` |

## 16. Implementation Readiness

**Status**: [READY | PARTIALLY_READY | BLOCKED]
[State any `[NEEDS BACKEND SDS]`/`[NEEDS SPEC CLARIFICATION]`/`[A11Y TARGET NOT STATED]` items and
what `/implement` can start on now vs. what's blocked.]
```

---

## NAMING CONVENTIONS (MODE H)

Discover exact conventions from the project's existing feature folders/CLAUDE.md — below are
typical patterns:

- SDS path: `docs/04-sds/M-XX-module-name.md`
- Feature folder: `features/{feature}/` (kebab-case)
- State service: `{Feature}StateService`, file `{feature}-state.service.ts`
- Smart container component: `{Feature}Component`
- Presentational component: `{Feature}{Purpose}Component` (e.g. `OrderListComponent`)
- Route config: `{feature}.routes.ts`
- API client function: in `shared/api/{feature}.api.ts`, never inlined in the state service
- Test file: `{name}.spec.ts` colocated with the file under test

---

## LAYERING RULES (MODE H)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|----------------|
| Presentational component | `@Input()`/`@Output()`, `shared/ui-kit` | State service, `HttpClient`, `core/*` singletons |
| Smart container component | State service (injected), presentational components | `HttpClient` directly, another feature's internal service |
| State service | API client, `core/*` singletons (e.g. auth) | Component types, `shared/ui-kit` |
| API client (`shared/api/*`) | `HttpClient`, DTOs | State services, components |

**State Service Pattern:**
```typescript
// State lives behind a service — components never call HttpClient directly, and never
// mutate state from outside the service's own methods
@Injectable({ providedIn: 'root' })
export class [Feature]StateService {
  private readonly state$ = new BehaviorSubject<[Feature]State>({ status: 'idle', data: null, error: null });
  readonly state = this.state$.asObservable();

  load(): void { /* calls API client, updates state$ */ }
}
```

**Component Rule:**
- A component that injects `HttpClient` directly, or holds business/validation logic beyond
  form-shape validation, is a layering violation — move it into the state service.

**SDS Traceability Comment (required):**
```typescript
// Traceability: SDS M-XX Section Y.Z [Method Name]
load(): void { ... }
```

**SDS Design Principle:**
Design from the backend API contract outward (API contract → State service → Smart container →
Presentational components → Route) — the same inside-out discipline as the backend modes, adapted
to a client app. Don't design the component tree first and only think about where its data comes
from afterward.
