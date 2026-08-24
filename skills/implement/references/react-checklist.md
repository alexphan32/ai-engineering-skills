# Implement Skill — React (SPA) Reference Material

> Load this when implementing in a React SPA (CSR) codebase. It complements
> `verification-checklist.md` — that file's language-agnostic checklist (linting, testing,
> secrets scan, docs) still applies; this file adds the traps specific to this stack. It does not
> restate the generic security/performance checklists — only React-specific traps. For a Next.js
> App Router project, use MODE C's discipline instead — this file is for a client-rendered SPA.
>
> **First, confirm the data-fetching library already in use** (`package.json`): React Query,
> SWR, or a hand-rolled `fetch`-in-`useEffect` pattern. Introducing a second data-fetching
> approach for one feature, when the rest of the app already has one, is a needless inconsistency
> — migrate the pattern only with a stated reason, not silently for this feature alone.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ Hand-rolled fetch-and-cache inside `useState`/Context

```typescript
function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchOrders().then(data => { setOrders(data); setLoading(false); });  // no cache, no
  }, []);                                                                   // dedup across
}                                                                           // remounts, no
                                                                             // retry/staleness policy
```

### ✅ A data-fetching hook backed by a data-fetching library

```typescript
function useOrders(params: OrdersParams) {
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () => fetchOrders(params),
  });
}

function OrdersPage() {
  const { data, isLoading, isError, refetch } = useOrders({ status: 'open' });
}
```

**Why this is better:** React Query/SWR already solve caching, deduping concurrent requests,
staleness, retries, and refetch-on-focus — hand-rolling the same thing in `useState`/`useEffect`
reimplements it worse, and every feature that does it ends up with its own subtly different bugs.

---

### ❌ Prop-drilling through 4+ levels

```typescript
<OrdersPage>
  <OrdersToolbar onFilterChange={setFilter} />
  <OrdersList filter={filter}>
    <OrderRow filter={filter}>
      <OrderActions filter={filter} />  {/* filter threaded through 3 components that never use it */}
    </OrderRow>
  </OrdersList>
</OrdersPage>
```

### ✅ Composition, or a scoped context for the specific subtree that needs it

```typescript
const FilterContext = createContext<Filter | null>(null);

<FilterContext.Provider value={filter}>
  <OrdersList />  {/* only OrderActions, deep inside, actually reads useContext(FilterContext) */}
</FilterContext.Provider>
```

**Why this is better:** threading a prop through components that never use it just to reach a
distant descendant couples every intermediate component to a value it doesn't care about — a
scoped Context (or restructuring the composition) lets only the component that needs the value
read it.

---

### ❌ Missing/incorrect `useEffect` dependency array

```typescript
function OrderDetail({ orderId }: { orderId: string }) {
  const [order, setOrder] = useState<Order | null>(null);
  useEffect(() => {
    fetchOrder(orderId).then(setOrder);
  }, []);   // orderId omitted — navigating to a different order reuses the stale fetch
}
```

### ✅ Every value the effect reads is in the dependency array (or the fetch is a query hook instead)

```typescript
function OrderDetail({ orderId }: { orderId: string }) {
  const { data: order } = useQuery({
    queryKey: ['order', orderId],   // orderId in the key — a new id automatically refetches
    queryFn: () => fetchOrder(orderId),
  });
}
```

**Why this is better:** an incomplete dependency array is one of the most common React bugs —
the effect silently keeps using a stale closure value. Moving data-fetching into a query hook
sidesteps the whole class of bug; when a plain `useEffect` is still appropriate, the lint rule
`react-hooks/exhaustive-deps` should be on and heeded, not suppressed.

---

### ❌ Memoizing everything defensively, with no actual re-render problem

```typescript
const total = useMemo(() => a + b, [a, b]);          // trivial computation, no measured cost
const handleClick = useCallback(() => doThing(), []); // passed to a DOM element, not a memoized child
```

### ✅ Memoize where there's an actual expensive computation or a memoized child consuming it

```typescript
const total = a + b;   // cheap — just compute it inline, memoization overhead isn't worth it

const sortedRows = useMemo(() => rows.slice().sort(sortFn), [rows, sortFn]);  // genuinely
                                                                                // expensive sort

const handleRowClick = useCallback((id: string) => onSelect(id), [onSelect]);
<MemoizedRow onClick={handleRowClick} />   // passed to a React.memo'd child — this is where
                                             // a stable reference actually matters
```

**Why this is better:** `useMemo`/`useCallback` have their own overhead and reduce readability;
applying them everywhere "to be safe" without a measured re-render problem is the inverse
over-engineering mistake to under-memoizing. Reach for them when profiling (or an obvious
expensive computation) shows a reason, not by default.

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — React specifics slot in as follows:

### **P0 - Critical**
- No hand-rolled fetch-and-cache logic inside `useState`/`useEffect`/Context where the project
  already has a data-fetching library — server state goes through it
- Every `useEffect` that reads a prop/state value includes it in the dependency array (or the
  logic is moved into a query hook instead)
- No business logic (validation beyond form shape, ownership checks) inline in a component that
  should be in a hook/utility

### **P1 - High**
- Every list item rendered with `.map()` has a stable, unique `key` — never the array index for a
  reorderable/filterable list
- Prop-drilling past 2–3 levels is replaced with composition or a scoped Context
- Route-level components are code-split via `lazy()`, not bundled into the initial chunk

### **P2 - Medium**
- Hook unit tests (mocked API client / MSW) for each query/mutation state
- Component tests per screen state (Loading/Empty/Error/Success)
- Comments on non-obvious business rules in hooks/utilities

### **P3 - Low**
- `useMemo`/`useCallback` audit for a component with a profiler-confirmed re-render problem
- Virtualization (`react-window`/`react-virtual`) retrofit for a list that's grown beyond its
  originally-assumed size

---

## VERIFICATION CHECKLIST (React additions)

Run these in addition to the general checklist.

### 1. Code Quality
```bash
npx tsc --noEmit
npx eslint src --ext .ts,.tsx    # with react-hooks/exhaustive-deps enabled
```
- [ ] No `any` typing an API response/DTO — model the actual shape, even loosely
- [ ] `react-hooks/exhaustive-deps` warnings are resolved, not suppressed with a blanket
  `// eslint-disable-next-line`

### 2. Correctness
- [ ] Every component reads server data via the feature's data-fetching hook, never `fetch`/
  `axios` inline in a component body
- [ ] Every `useEffect` dependency array is complete for what the effect body actually reads —
  verified by reading the effect, not assumed

```bash
grep -rln "fetch(\|axios\." --include="*.tsx" src/features | grep -v "/api/"
```

### 3. Rendering & Keys
- [ ] Every `.map()` producing JSX has a stable, unique `key` — never `key={index}` on a list
  that can reorder, filter, or have items removed from the middle

```bash
grep -rn "\.map(" --include="*.tsx" src/features -A2 | grep "key={index}\|key={i}"
```

### 4. Testing
```bash
npx vitest run   # or: npm test
```
- [ ] Hook tests use a **mocked** API client or MSW, never a real network call
- [ ] Every screen state (Loading/Empty/Error/Success) has at least one test that drives the mock
  to produce it

### 5. Performance
- [ ] Route-level components are wrapped in `lazy()` + `Suspense`, confirmed in the router config
- [ ] A list that can grow unbounded is virtualized, not rendered in full via a plain `.map()`

```bash
grep -rn "React.lazy\|lazy(" --include="*.tsx" src/app | grep "{feature}"
```

---

## TROUBLESHOOTING

**A component shows stale data after a prop changes:**
Check the `useEffect` dependency array first — a value read inside the effect but missing from
the array is the most common cause. Moving the fetch into a query hook with the value in the
`queryKey` sidesteps this class of bug entirely.

**List items visually swap/glitch when the list is reordered or filtered:**
Check for `key={index}` on the `.map()` call — React reconciles by key, so an index key makes it
treat "the item now at position 2" as the same element even when the underlying data at that
position changed.

**A component re-renders far more than expected:**
Check for a new object/array/function literal created inline on every render and passed as a
prop to a `React.memo`'d child (defeats the memoization), or a Context value object recreated on
every render of the provider (re-renders every consumer regardless of `memo`).

**A business rule behaves differently in a component test than it did manually in the app:**
The rule is likely implemented inline in the component rather than a hook/utility, so the
component test is exercising UI code that also happens to contain logic — move the rule into a
hook where a plain unit test (no React Testing Library harness) can cover it.
