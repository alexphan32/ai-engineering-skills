# Implement Skill — Angular Reference Material

> Load this when implementing in an Angular codebase. It complements
> `verification-checklist.md` — that file's language-agnostic checklist (linting, testing,
> secrets scan, docs) still applies; this file adds the traps specific to this stack. It does not
> restate the generic security/performance checklists — only Angular-specific traps.
>
> **First, confirm the component style and state approach** (`angular.json`/`package.json`):
> standalone components vs. `NgModule`-based, and a plain service + `BehaviorSubject`/signal vs.
> NgRx/Akita. Writing standalone-component code against an `NgModule` project (or introducing
> NgRx where the project uses plain services) produces a mismatch with everything around it.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ Manual `.subscribe()` with no unsubscribe path

```typescript
export class OrderListComponent implements OnInit {
  orders: Order[] = [];

  constructor(private ordersService: OrdersStateService) {}

  ngOnInit(): void {
    this.ordersService.state$.subscribe(state => {   // never unsubscribed — this subscription
      this.orders = state.data ?? [];                 // outlives the component if it navigates away
    });                                                // before the observable completes
  }
}
```

### ✅ `async` pipe (or `takeUntilDestroyed()` when a manual subscription is unavoidable)

```typescript
export class OrderListComponent {
  readonly state$ = this.ordersService.state$;   // template subscribes via `async` pipe,
                                                   // and unsubscribes automatically on destroy
  constructor(private ordersService: OrdersStateService) {}
}
```
```html
<div *ngIf="state$ | async as state">
  <app-order-list [items]="state.data ?? []" />
</div>
```

**Why this is better:** the `async` pipe subscribes on render and unsubscribes on destroy
automatically — no manual lifecycle bookkeeping to forget. When a manual `.subscribe()` is
genuinely unavoidable (e.g. inside a non-template callback), use `takeUntilDestroyed()` instead of
a hand-written `ngOnDestroy` flag.

---

### ❌ Business logic inside a component instead of a service

```typescript
export class OrderFormComponent {
  submit(): void {
    if (this.form.value.total <= 0) { this.error = 'Invalid total'; return; }  // business rule
    this.http.post('/api/v1/orders', this.form.value).subscribe(...);          // + HTTP call,
  }                                                                             // both inline in
}                                                                               // the component
```

### ✅ Component delegates to the state service; the service owns the rule and the HTTP call

```typescript
export class OrderFormComponent {
  constructor(private ordersService: OrdersStateService) {}
  submit(): void { this.ordersService.create(this.form.value); }  // component just forwards intent
}

@Injectable({ providedIn: 'root' })
export class OrdersStateService {
  create(input: CreateOrderInput): void {
    if (input.total <= 0) { /* update state$ with a validation error */ return; }
    this.api.createOrder(input).subscribe(/* update state$ */);
  }
}
```

**Why this is better:** a component that owns business logic can't be reused by another
component/route, and can't be unit-tested without a DOM harness. The rule and the HTTP call both
belong in the service, where a plain unit test with a fake API client covers them.

---

### ❌ A `SharedModule` that imports and re-exports everything

```typescript
@NgModule({
  imports: [CommonModule, FormsModule, ReactiveFormsModule, HttpClientModule, RouterModule, /* ... */],
  exports: [CommonModule, FormsModule, ReactiveFormsModule, HttpClientModule, RouterModule, /* ... */],
})
export class SharedModule {}   // every feature module imports this one module for "convenience"
```

### ✅ Feature modules import only what they actually use; standalone components import directly

```typescript
@Component({
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],   // exactly what this component needs
  // ...
})
export class OrderFormComponent {}
```

**Why this is better:** a catch-all `SharedModule` defeats lazy-loading (every feature module now
transitively pulls in everything the shared module imports, even unused pieces) and hides which
feature actually depends on what — the same package-by-layer anti-pattern in module form.

---

### ❌ `OnPush`/change-detection mismatch — mutating an `@Input()` object in place

```typescript
@Component({ changeDetection: ChangeDetectionStrategy.OnPush })
export class OrderListComponent {
  @Input() items: Order[] = [];
  markFirstAsSelected(): void {
    this.items[0].selected = true;   // mutates in place — same array reference, OnPush sees no
  }                                   // change, this component never re-renders
}
```

### ✅ Replace the reference so `OnPush`'s reference-equality check detects the change

```typescript
markFirstAsSelected(): void {
  this.items = this.items.map((item, i) => i === 0 ? { ...item, selected: true } : item);
}
```

**Why this is better:** `OnPush` compares `@Input()` references, not deep contents — an in-place
mutation is invisible to it. Treating inputs as immutable and replacing the reference is what
makes `OnPush` (and the perf gain it's there for) actually work.

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — Angular specifics slot in as follows:

### **P0 - Critical**
- No manual `.subscribe()` in a component with no corresponding unsubscribe path (`async` pipe or
  `takeUntilDestroyed()`)
- No `HttpClient` call made directly from a component — routed through the state service
- No business/validation logic (beyond form-shape checks) written inside a component

### **P1 - High**
- Every list rendered with `*ngFor`/`@for` over a mutable collection has a `trackBy`/`track`
  expression
- `OnPush` components never mutate an `@Input()` in place — always replace the reference
- Route lazy-loading boundary confirmed (the feature isn't pulled into the eagerly-loaded bundle)

### **P2 - Medium**
- State service unit tests (fake API client, no real `HttpClient`) for each state transition
- Component tests per screen state (Loading/Empty/Error/Success)
- JSDoc/comments on non-obvious business rules in the state service

### **P3 - Low**
- Bundle-size analysis (`ng build --stats-json` + a visualizer) for a feature reported as
  disproportionately large
- Virtual scrolling (`cdk-virtual-scroll-viewport`) retrofit for a list that's grown beyond its
  originally-assumed size

---

## VERIFICATION CHECKLIST (Angular additions)

Run these in addition to the general checklist.

### 1. Code Quality
```bash
npx tsc --noEmit
ng lint    # or eslint, if configured
```
- [ ] No `any` typing an API response/DTO — model the actual shape, even loosely, so a schema
  change surfaces as a type error instead of a silent `undefined`

### 2. Correctness
- [ ] Every component that reads feature state does so via the state service, never `HttpClient`
  directly
- [ ] Every subscription in a component has a stated cleanup path (`async` pipe or
  `takeUntilDestroyed()`) — verified by reading the actual code, not assumed

```bash
grep -rn "\.subscribe(" --include="*.ts" src/app | grep -v "async\b"
grep -rln "HttpClient" --include="*.component.ts" src/app
```

### 3. Change Detection & Rendering
- [ ] Every `*ngFor`/`@for` over a mutable/reorderable list has `trackBy`/`track`
- [ ] `OnPush` components never mutate an `@Input()` object/array in place — inputs are treated as
  immutable and replaced on change
- [ ] A component subscribing to a hot-frequency observable outside the `async` pipe has a
  `distinctUntilChanged()`/`debounceTime()` if it doesn't need every emission

```bash
grep -rn "\*ngFor\|@for" --include="*.html" src/app | grep -v "trackBy\|track "
```

### 4. Testing
```bash
ng test
```
- [ ] State service unit tests use a **fake** API client (not a real `HttpClient`/`HttpTestingController`
  hitting a real backend)
- [ ] Every screen state (Loading/Empty/Error/Success) has at least one test that drives the fake
  API client to produce it

### 5. Performance
- [ ] This feature's route is confirmed lazy-loaded (check the route config, not just assumed)
- [ ] A list that can grow unbounded uses virtual scrolling, not a plain `*ngFor` over the full
  dataset

```bash
grep -rn "loadComponent\|loadChildren" --include="*.routes.ts" src/app | grep "{feature}"
```

---

## TROUBLESHOOTING

**A component's data silently stops updating after some navigations:**
Check for a manual `.subscribe()` with no unsubscribe path first — the observable is still
delivering to a destroyed component's callback, or (less obviously) a stale subscription is
holding a reference that prevents the expected new subscription from taking over.

**An `OnPush` component doesn't re-render after what looks like a state change:**
Check whether the `@Input()` was mutated in place instead of replaced — `OnPush` only re-renders
on a reference change, so `this.items[0].x = y` is invisible to it even though the array "changed."

**A feature's initial bundle is larger than expected:**
Check the route config for a missing `loadComponent`/`loadChildren` lazy boundary, or a
`SharedModule` re-exporting more than this feature actually uses — either pulls extra code into
the eagerly-loaded bundle.

**A business rule behaves differently in a component test than it did manually in the app:**
The rule is likely implemented inline in the component rather than the state service, so the
component test is exercising UI code that also happens to contain logic — move the rule into the
state service where a plain unit test (no `TestBed`/DOM harness) can cover it.
