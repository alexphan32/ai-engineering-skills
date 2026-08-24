# Implement Skill — Android (Kotlin) Reference Material

> Load this when implementing in an Android (Kotlin, MVVM + Jetpack Compose/View) codebase. It
> complements `verification-checklist.md` — that file's language-agnostic checklist (linting,
> testing, secrets scan, docs) still applies; this file adds the traps specific to this stack.
> It does not restate the generic security/performance checklists — only Android-specific traps.
>
> **First, confirm the UI toolkit and DI framework** (`build.gradle.kts`): Compose
> (`androidx.compose.*`) vs. the legacy View system, and Hilt vs. Koin vs. manual DI. Writing
> `@HiltViewModel` wiring against a Koin project (or vice versa) produces code that doesn't compile.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ ViewModel holding a Context/View/Activity/Fragment reference

```kotlin
class ProfileViewModel(
    private val context: Context      // leak: ViewModel outlives the Activity across
) : ViewModel() {                     // config-change destruction (rotation, theme change) —
                                       // this held reference keeps the destroyed Activity alive
    fun showToast(msg: String) {
        Toast.makeText(context, msg, Toast.LENGTH_SHORT).show()
    }
}
```

### ✅ ViewModel exposes state; the UI layer owns Context-dependent calls

```kotlin
@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val repository: ProfileRepository
) : ViewModel() {

    private val _events = MutableSharedFlow<ProfileEvent>()
    val events: SharedFlow<ProfileEvent> = _events.asSharedFlow()

    fun onSaveClicked() = viewModelScope.launch {
        val result = repository.saveProfile()
        _events.emit(if (result.isSuccess) ProfileEvent.ShowToast("Saved") else ProfileEvent.ShowToast("Failed"))
    }
}

// In the Composable/Fragment — Context-dependent work happens where Context legitimately lives:
val context = LocalContext.current
LaunchedEffect(Unit) {
    viewModel.events.collect { event ->
        if (event is ProfileEvent.ShowToast) Toast.makeText(context, event.message, Toast.LENGTH_SHORT).show()
    }
}
```

**Why this is better:** the ViewModel survives config changes by design (that's the whole point
of `ViewModelStore`); holding an Activity/Fragment/View/Context reference defeats that guarantee
and leaks the old Activity until GC eventually breaks the reference — often never, if the
ViewModel itself is retained for the process lifetime (e.g. `activityViewModels()` shared scope).

---

### ❌ ViewModel calling Retrofit/Room directly

```kotlin
class OrderViewModel(
    private val api: OrderApiService,     // ViewModel now depends on a concrete network type —
    private val dao: OrderDao             // untestable without a real network/DB, and any
) : ViewModel() {                         // caching/refresh policy is scattered across every ViewModel
    fun loadOrder(id: String) = viewModelScope.launch {
        val dto = api.getOrder(id)        // no local cache, no offline read, no single source of truth
        dao.insert(dto.toEntity())
    }
}
```

### ✅ ViewModel depends on the Repository interface only

```kotlin
@HiltViewModel
class OrderViewModel @Inject constructor(
    private val repository: OrderRepository   // interface — swappable for a fake in tests
) : ViewModel() {
    fun loadOrder(id: String) = viewModelScope.launch {
        repository.refreshOrder(id)   // Repository owns the network call + Room write-through
    }
}
```

**Why this is better:** the caching/refresh policy lives in exactly one place (the Repository),
the ViewModel becomes testable with a fake `OrderRepository` and no real network/DB, and swapping
the data source (e.g. adding an offline cache) never touches ViewModel code.

---

### ❌ Recomposition scope too broad — missing `remember`/`key`, unstable lambda

```kotlin
@Composable
fun OrderList(orders: List<Order>, viewModel: OrderViewModel) {
    LazyColumn {
        items(orders) { order ->
            // a new lambda instance is created on every recomposition of OrderList,
            // forcing OrderRow to recompose even when `order` itself hasn't changed
            OrderRow(order, onClick = { viewModel.select(order.id) })
        }
    }
}
```

### ✅ Stable keys and hoisted/remembered callbacks

```kotlin
@Composable
fun OrderList(orders: List<Order>, onOrderClick: (String) -> Unit) {
    LazyColumn {
        items(orders, key = { it.id }) { order ->     // stable key: reordering doesn't
            OrderRow(order, onClick = onOrderClick)    // recreate/recompose unrelated rows
        }
    }
}

@Composable
fun OrderRow(order: Order, onClick: (String) -> Unit) {
    val handleClick = remember(order.id) { { onClick(order.id) } }  // stable lambda identity
    Row(Modifier.clickable { handleClick() }) { Text(order.name) }
}
```

**Why this is better:** `key = { it.id }` lets Compose track item identity across list
mutations instead of recomposing by position; a remembered/hoisted lambda has a stable identity
across recompositions, so `OrderRow` skips recomposition when nothing it actually reads changed.

---

### ❌ Coroutine scope misuse — `GlobalScope`

```kotlin
class SyncViewModel : ViewModel() {
    fun startSync() {
        GlobalScope.launch {              // not tied to any lifecycle — keeps running after
            repository.syncAll()          // the ViewModel is cleared, the screen is gone,
        }                                 // or the app is backgrounded; leaks the coroutine
    }
}
```

### ✅ Lifecycle-scoped coroutines

```kotlin
class SyncViewModel : ViewModel() {
    fun startSync() {
        viewModelScope.launch {           // cancelled automatically in onCleared()
            repository.syncAll()
        }
    }
}

// In a Fragment/Activity for UI-scoped work instead of ViewModel-scoped:
viewLifecycleOwner.lifecycleScope.launch {
    repeatOnLifecycle(Lifecycle.State.STARTED) {
        viewModel.uiState.collect { render(it) }   // cancelled/restarted with STARTED lifecycle
    }
}
```

**Why this is better:** `viewModelScope`/`lifecycleScope` (with `repeatOnLifecycle` for Flow
collection) tie the coroutine's lifetime to the component that owns it — no manual cancellation
bookkeeping, and no work continuing silently after the screen is gone.

---

### ❌ Business/networking logic placed directly in an Activity/Fragment

```kotlin
class OrderFragment : Fragment() {
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        lifecycleScope.launch {
            val response = RetrofitClient.api.getOrder(orderId)   // direct network call from
            if (response.status == "PAID") {                      // the Fragment, plus a business
                binding.statusText.text = "Paid"                   // rule (status mapping) baked
            }                                                      // into the UI layer — untestable
        }                                                          // without instrumentation
    }
}
```

### ✅ Fragment renders; ViewModel/Repository own logic

```kotlin
class OrderFragment : Fragment() {
    private val viewModel: OrderViewModel by viewModels()

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state -> render(state) }
            }
        }
        viewModel.loadOrder(orderId)
    }

    private fun render(state: OrderUiState) { /* pure rendering, no business logic */ }
}
```

**Why this is better:** the status-mapping rule and the network call both move into the
ViewModel/Repository where they're unit-testable with a fake Repository; the
Fragment's only job is turning `uiState` into View updates.

---

### ❌ Missing Hilt scope causes duplicate Repository/Retrofit instances

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    fun provideRetrofit(): Retrofit =               // no @Singleton — Hilt creates a NEW
        Retrofit.Builder().baseUrl(BASE_URL).build() // instance at every injection site
}
```

### ✅ Scope annotation matches the installed component

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    @Singleton
    fun provideRetrofit(): Retrofit =
        Retrofit.Builder().baseUrl(BASE_URL).build()
}
```

**Why this is better:** `@InstallIn(SingletonComponent::class)` only controls *where* a binding is
allowed to live — it does not make Hilt reuse one instance. Without `@Singleton` on the
`@Provides`/`@Binds` function itself, Hilt constructs a fresh `Retrofit`/`Repository`/`Database`
at every injection point. For a `Repository` meant to be the single source of truth, that means
two screens can silently end up with two different instances holding two different in-memory
caches that never see each other's writes.

---

### ❌ A Utils/Manager god-object

```kotlin
object AppUtils {
    fun formatCurrency(amount: Long): String = ...
    fun isValidEmail(input: String): Boolean = ...
    fun uploadProfileImage(uri: Uri): Result<String> = ...
    fun logout() = ...
    // grows every time someone needs "a place to put a function"
}
```

### ✅ Split by responsibility, injected where used

```kotlin
class CurrencyFormatter { fun format(amountMinor: Long): String = ... }
class EmailValidator { fun isValid(input: String): Boolean = ... }
class ProfileImageRepository { suspend fun upload(uri: Uri): Result<String> = ... }
class SessionManager @Inject constructor(private val authApi: AuthApiService) {
    fun logout() = ...
}
```

**Why this is better:** a static `Utils`/`Manager` object accumulates unrelated responsibilities
over time and can't be substituted with a fake in a test — a Kotlin `object`'s functions are
called statically, so any test exercising code that calls `AppUtils.uploadProfileImage()` is stuck
making a real network call. Each responsibility as its own small, injectable class keeps the
dependency visible in the constructor and fakeable in a unit test.

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — Android specifics slot in as follows:

### **P0 - Critical**
- No `Context`/`View`/`Activity`/`Fragment` reference held by a ViewModel field
- ViewModel depends only on Repository/use-case interfaces — no direct Retrofit/Room calls
- No `GlobalScope.launch` for work that should be lifecycle-bound (`viewModelScope`/`lifecycleScope`)
- No business/networking logic inside an Activity/Fragment/Composable — it belongs in the
  ViewModel/Repository

### **P1 - High**
- Compose: stable `key` on every `LazyColumn`/`LazyRow` `items()` call over a mutable list
- Compose: lambdas passed to frequently-recomposing children are hoisted or `remember`ed
- Coroutine exception handling: a `Flow.catch`/`runCatching` around every repository call the
  ViewModel launches, mapped into the UI state's `Error` case — not left to crash the coroutine
- `viewModelScope`/`lifecycleScope` used consistently — no manual `Job()`/`CoroutineScope()`
  instance created and never cancelled

### **P2 - Medium**
- ViewModel unit tests (JUnit + fake Repository, no real network/DB) for each UI state
- Compose/Espresso instrumented test per UI state (Loading/Empty/Error/Success)
- KDoc/comments on non-obvious business rules in the Repository/use-case layer

### **P3 - Low**
- Recomposition count tuning via Compose Layout Inspector for a screen with a reported jank issue
- Room query/index tuning for a local cache that has grown large

---

## VERIFICATION CHECKLIST (Android additions)

Run these in addition to the general checklist.

### 1. Code Quality
```bash
./gradlew compileDebugKotlin
./gradlew lint            # or ktlintCheck/detekt, if configured
```
- [ ] No `!!` (non-null assertion) on a value that can genuinely be null at runtime (a normal
  failure case, not a real bug) — model it with a nullable type/sealed state instead

### 2. Correctness
- [ ] Every ViewModel constructor parameter is an interface (`Repository`/use-case), never a
  concrete Retrofit `ApiService`, Room `Dao`, or Android framework type
- [ ] No ViewModel field is typed `Context`, `View`, `Activity`, or `Fragment`
- [ ] Every `viewModelScope.launch { repository.foo() }` call has error handling that updates the
  UI state — verified by reading the actual `catch`/`try` block, not assumed

```bash
grep -rn "class .*ViewModel" --include="*.kt" -A5 app/src/main/java | grep -E "Context|: View\b|Activity|Fragment"
grep -rn "GlobalScope" --include="*.kt" app/src/main/java
```

### 3. Compose Performance (skip this section if the project uses the legacy View system)
- [ ] Every `items()` call inside a `LazyColumn`/`LazyRow` over a mutable/reorderable list passes
  a stable `key = { it.id }` — verified by reading the call, not assumed
- [ ] Lambdas passed to composables inside a hot recomposition path are `remember`ed or hoisted
  to a stable reference, not recreated inline on every parent recomposition
- [ ] `derivedStateOf` used (not a raw computed property read every recomposition) for a value
  computed from frequently-changing state but consumed by only part of the tree

```bash
grep -rn "items(" --include="*.kt" app/src/main/java | grep -v "key ="
```

### 4. Coroutines & Lifecycle
- [ ] No `GlobalScope.launch`/`GlobalScope.async` anywhere in ViewModel, Repository, or UI code
- [ ] Flow collection in a Fragment/Activity is wrapped in
  `repeatOnLifecycle(Lifecycle.State.STARTED)` (or `flowWithLifecycle`), not a bare
  `lifecycleScope.launch { flow.collect {} }` with no lifecycle gating
- [ ] Every `viewModelScope.launch` block that calls a suspending Repository method has a
  `catch`/`runCatching` path — an uncaught exception here crashes the app, not just that call

```bash
grep -rn "GlobalScope" --include="*.kt" app/src/main/java
grep -rn "lifecycleScope.launch" --include="*.kt" app/src/main/java | grep -v "repeatOnLifecycle"
```

### 5. Testing
```bash
./gradlew testDebugUnitTest
./gradlew connectedDebugAndroidTest    # if a device/emulator is available
```
- [ ] ViewModel unit tests use a **fake** Repository (a hand-written or `mockk`-mocked
  implementation of the interface), never a real Retrofit/Room instance
- [ ] Every UI state (Loading/Empty/Error/Success) has at least one ViewModel unit test that
  drives the fake Repository to produce it
- [ ] Instrumented tests (Compose UI test / Espresso) cover each UI state's rendering, not just
  the happy path

### 6. Manifest/Permissions Sanity
- [ ] Any new permission (`ACCESS_FINE_LOCATION`, `CAMERA`, etc.) declared in `AndroidManifest.xml`
  has a corresponding runtime permission request/rationale flow — a declared-but-unrequested
  permission crashes at the call site on API 23+

---

## TROUBLESHOOTING

**ViewModel-related memory leak reported by LeakCanary:**
Check for a held `Context`/`View`/`Activity`/`Fragment` field on the ViewModel first — this is
the single most common Android ViewModel leak. A `WeakReference` is not the fix; removing the
reference (and moving Context-dependent work to the UI layer) is.

**A ViewModel unit test needs a real device/emulator to pass:**
The ViewModel is calling Retrofit/Room directly instead of through the Repository interface —
route the call through the Repository and inject a fake implementation in the test instead.

**A Compose list scrolls janky or items visibly recompose/flash while scrolling:**
Check for a missing `key` on `items()` first, then check whether a lambda parameter passed into
the row composable is being recreated every recomposition (no `remember`) — both cause the whole
visible row to be treated as new content instead of being reused.

**Work continues (network call, sync) after the user has left the screen or the app is killed:**
Look for `GlobalScope.launch` — it has no owner to cancel it. Replace with `viewModelScope`
(cancelled in `onCleared()`) or `lifecycleScope` (cancelled with the lifecycle owner), or move
genuinely process-lifetime work into a `WorkManager` job instead.

**A business rule behaves differently in a widget test than it did manually in the app:**
The rule is likely implemented inline in the Activity/Fragment/Composable rather than in the
ViewModel/Repository, so the widget test is exercising UI code that also happens to contain logic
— move the rule into the ViewModel/Repository where a plain unit test (no UI harness) can cover it
directly.
