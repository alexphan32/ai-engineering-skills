# Frontend Architecture Patterns

Stack-specific application of the axes decided in `architecture-selection.md`. These patterns are
about internal code organization within one frontend deployable — they don't change based on
Tier, but domain complexity (Axis 2) does affect how much state-management/abstraction is
justified. Detect the stack from `angular.json` / `package.json`'s `dependencies` before assuming.

## 1. Angular

**Default structure — feature-based, not layer-based:**

```text
src/app/
├── core/            # singleton services, guards, interceptors — imported ONCE in the root
├── shared/          # reusable dumb components/pipes/directives used by 2+ features
└── features/
    └── orders/       # one feature = one bounded context, self-contained
        ├── components/
        ├── services/
        └── orders.routes.ts   # lazy-loaded
```

- **`core/` vs `shared/`**: `core/` holds app-wide singletons (auth service, HTTP interceptor,
  route guards) that must exist exactly once — importing it a second time is a bug, not a
  convenience. `shared/` holds stateless, reusable presentational pieces with no app-specific
  singleton state.
- **Standalone components over NgModule ceremony** for new code on a recent Angular version —
  fewer indirection layers, same feature-folder organization still applies.
- **Smart/container vs. presentational component split**: a feature's top-level component
  fetches data and manages state; the components it composes receive data via `@Input`/`@Output`
  and hold no business logic. This keeps presentational components trivially reusable and testable.
- **State management**: a service exposing a `BehaviorSubject`/signal is enough for most features.
  Reach for a store library (NgRx et al.) only when state is genuinely shared across many unrelated
  parts of the tree and its transitions are complex enough that tracing them by hand is error-prone
  — the same over-engineering judgment call as Axis 2, applied to frontend state instead of backend
  domain logic.
- **Reactive discipline**: prefer the `async` pipe or `takeUntilDestroyed()` over manual
  `.subscribe()` + manual unsubscribe — the latter is the most common source of Angular memory
  leaks.
- **Lazy-load feature routes** so the initial bundle doesn't grow with every unrelated feature.

**Anti-patterns**: business logic inside a component instead of a service (untestable without a
DOM); a `SharedModule` that imports and re-exports everything, defeating lazy-loading and hiding
real dependencies; manual subscription management instead of the `async` pipe; a feature reaching
into another feature's internal service instead of going through its public exports — same rule as
`modular-monolith.md` §2, at frontend-feature scale.

## 2. React

**Default structure — feature-sliced, not type-sliced:**

```text
src/
├── app/             # providers, routing, app-wide setup
├── shared/          # cross-cutting UI kit, utilities, types used by 2+ features
└── features/
    └── orders/
        ├── components/
        ├── hooks/         # feature-specific logic, including data-fetching hooks
        ├── api/           # this feature's API calls
        └── types.ts
```

Avoid the classic type-sliced structure (`components/`, `containers/`, `reducers/`, `actions/`
each holding every feature's files) — it's the same package-by-layer anti-pattern
`modular-monolith.md` §4 calls out for backends, and it produces the same result: every feature
change touches four unrelated top-level directories.

- **Separate server state from client state.** Data fetched from an API (with caching,
  revalidation, loading/error states) is a different problem from UI state (a modal being open, a
  form's current values) — use a dedicated data-fetching library (React Query, SWR, or the
  framework's built-in equivalent) for the former, and `useState`/`useReducer`/a lightweight store
  (Zustand, Context) for the latter. Conflating them by hand-rolling fetch-and-cache logic inside
  Redux/Context is the most common React architecture mistake.
- **Local state first.** Start with `useState` in the component that needs it; lift state up only
  when a sibling actually needs it, and reach for Context only for truly cross-cutting concerns
  (theme, auth session) — Context is not a general state-management replacement, and overusing it
  causes broad, hard-to-trace re-renders.
- **Custom hooks for reusable logic**, not for reusable UI — a hook encapsulates behavior
  (`useOrderTotals`), a component encapsulates markup.
- **Next.js App Router note**: if the project is a Next.js full-stack app (Server Components,
  Server Actions, colocated backend), that's `design` skill's MODE C — this file's guidance covers
  a React SPA/CSR frontend's internal structure, not the full-stack data-access/mutation
  discipline MODE C's inside-out design already owns.

**Anti-patterns**: prop-drilling through more than 2–3 levels instead of composition or a scoped
Context; a single `utils.js`/`helpers.js` accumulating unrelated logic across features; hand-rolled
fetch-and-cache-in-Redux instead of a data-fetching library; a feature importing another feature's
internal component/hook directly instead of through its public exports.
