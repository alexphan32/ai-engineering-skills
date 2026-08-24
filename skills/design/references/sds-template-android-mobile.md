# SDS Template J: Android Mobile Feature (Kotlin)

> Reference for `design` skill — loaded on demand when creating MODE J SDS documents.
>
> **First, confirm the project's UI toolkit** (`build.gradle`/`build.gradle.kts`): Jetpack Compose
> (`androidx.compose.*` / `compose-bom`) vs. the legacy View system (`ViewBinding`/`DataBinding`,
> `Fragment`/`Activity` XML layouts). Some codebases mix both during a migration — state which one
> this feature's screen uses, don't assume Compose from training-data recency bias. Also confirm
> Hilt (`com.google.dagger:hilt-android`) is the DI framework in use before drafting `@HiltViewModel`
> wiring — a project on manual DI or Koin needs the equivalent stated instead.

---

## TEMPLATE J: Android Mobile Feature SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: {tech_stack — Kotlin version, Compose BOM or View system, Hilt/Koin/manual DI, min/target SDK from build.gradle.kts}

---

## 1. Module Overview

### 1.1 Description
[Describe what this feature does and where it sits in the app's navigation graph]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Module Type**: [Screen / Feature Module / Shared Component]
**Scale Tier**: N/A in the backend sense — this feature is a client screen, not a deployed
service. Note here only if this feature introduces a disproportionate architectural layer for
its complexity (e.g. adding a domain/use-case layer for a single trivial CRUD screen) — state the
justification either way in Section 4.

### 1.3 Package Layout
```
app/src/main/java/{basePackage}/feature/{feature}/
├── data/
│   ├── repository/{Feature}RepositoryImpl.kt   # implements domain-facing interface
│   ├── remote/{Feature}ApiService.kt           # Retrofit/Ktor interface
│   ├── remote/dto/{Feature}Dto.kt              # wire DTOs — never exposed past the repository
│   ├── local/{Feature}Dao.kt                   # Room DAO (only if local caching is used)
│   └── local/{Feature}Entity.kt                # Room entity (only if local caching is used)
├── domain/                                      # OPTIONAL — see Section 4
│   ├── model/{Feature}.kt                      # domain model — no Retrofit/Room/Android imports
│   ├── repository/{Feature}Repository.kt        # interface the ViewModel depends on
│   └── usecase/{Action}{Feature}UseCase.kt      # only if domain complexity justifies it
├── presentation/
│   ├── {Feature}ViewModel.kt                    # @HiltViewModel, exposes StateFlow
│   ├── {Feature}UiState.kt                      # sealed interface: Loading/Empty/Error/Success
│   └── {Feature}Screen.kt                       # @Composable (or Fragment + XML for View system)
└── di/{Feature}Module.kt                        # Hilt @Module binding Repository impl -> interface
```

**Screens**: [List screens/composables this feature adds]
**Backend endpoints consumed**: [List — see Section 3]
**Dependencies**: [M-01 Auth module for token, shared `core/network` module, etc.]

---

## 2. Architecture Context

| Component | Status | Reason |
|-----------|--------|--------|
| `{Feature}Repository` | New | No existing repository owns this data |
| `{Feature}Dao` (Room) | New/N/A | [state whether local caching is needed and why] |
| `AuthInterceptor` | Existing | Reused from `core/network`, not duplicated |

---

## 3. Backend API Contract

> Every endpoint this feature calls, taken from the real backend SDS — **never invent the shape**.
> If the backend SDS doesn't exist yet, write `[NEEDS BACKEND SDS]` literally and stop guessing.

| Method | Path | Auth | Request | Response | Source |
|--------|------|------|---------|----------|--------|
| GET | /api/v1/[resource] | Bearer | — | `[Resource]Dto[]` | SDS M-YY §4.3, or `[NEEDS BACKEND SDS]` |
| POST | /api/v1/[resource] | Bearer | `[Resource]RequestDto` | `[Resource]Dto` | SDS M-YY §4.3, or `[NEEDS BACKEND SDS]` |

```kotlin
// data/remote/dto/[Feature]Dto.kt
// Traceability: Backend SDS M-YY §4.2, or [NEEDS BACKEND SDS]
data class [Feature]Dto(
    val id: String,
    val field: String,
    val createdAt: String
)
```

---

## 4. Data Layer Design

### 4.1 Repository (single source of truth)

The Repository is the **only** thing the ViewModel talks to — it decides whether data comes from
the network, the local Room cache, or both, and applies the caching/refresh policy. The
ViewModel never calls Retrofit/Room directly.

```kotlin
// domain/repository/[Feature]Repository.kt (or data/repository/ if no domain layer — Section 4.3)
interface [Feature]Repository {
    fun observe[Feature](id: String): Flow<[Feature]>
    suspend fun refresh[Feature](id: String)
    suspend fun create[Feature](input: [Feature]Input): Result<[Feature]>
}
```

```kotlin
// data/repository/[Feature]RepositoryImpl.kt
// Traceability: SDS M-XX Section 4.1
class [Feature]RepositoryImpl @Inject constructor(
    private val api: [Feature]ApiService,
    private val dao: [Feature]Dao,               // omit if no local caching (Section 4.2 = N/A)
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO
) : [Feature]Repository {

    override fun observe[Feature](id: String): Flow<[Feature]> =
        dao.observeById(id).map { it.toDomain() }   // Room as single source of truth for reads

    override suspend fun refresh[Feature](id: String) = withContext(dispatcher) {
        val dto = api.get[Feature](id)              // network call
        dao.upsert(dto.toEntity())                   // write-through into Room, UI updates via Flow
    }

    override suspend fun create[Feature](input: [Feature]Input): Result<[Feature]> =
        withContext(dispatcher) {
            runCatching {
                val dto = api.create[Feature](input.toRequestDto())
                dao.upsert(dto.toEntity())
                dto.toDomain()
            }
        }
}
```

**Caching/refresh policy**: [state it explicitly — e.g. "Room is authoritative for reads; a
`refresh[Feature]()` call on screen entry re-fetches from network and write-through updates Room;
staleness beyond `[N minutes]` triggers an automatic refresh" — or "network-only, no local cache,
because `[reason: data changes too fast / privacy-sensitive / one-shot screen]`"]

### 4.2 Room Entity + DAO (if local caching is used)

State N/A here if this feature has no local persistence — most simple network-backed screens
don't need one.

```kotlin
// data/local/[Feature]Entity.kt
@Entity(tableName = "[feature_table]")
data class [Feature]Entity(
    @PrimaryKey val id: String,
    val field: String,
    val fetchedAt: Long
)

// data/local/[Feature]Dao.kt
@Dao
interface [Feature]Dao {
    @Query("SELECT * FROM [feature_table] WHERE id = :id")
    fun observeById(id: String): Flow<[Feature]Entity>

    @Upsert
    suspend fun upsert(entity: [Feature]Entity)
}
```

### 4.3 Retrofit/Ktor Service Interface

```kotlin
// data/remote/[Feature]ApiService.kt
interface [Feature]ApiService {
    @GET("api/v1/[resource]/{id}")
    suspend fun get[Feature](@Path("id") id: String): [Feature]Dto

    @POST("api/v1/[resource]")
    suspend fun create[Feature](@Body request: [Feature]RequestDto): [Feature]Dto
}
```

---

## 5. Domain Layer

State one of:
- **N/A — CRUD complexity doesn't justify a use-case layer.** [one-line reason, e.g. "this screen
  is a single read + single write with no cross-cutting business rule; the Repository interface
  is exposed to the ViewModel directly"]
- **Included.** [one-line reason, e.g. "submitting this form requires validating against two other
  in-flight requests and computing a derived total — that orchestration doesn't belong in the
  ViewModel or the Repository, so a use case owns it"]

```kotlin
// domain/usecase/Submit[Feature]UseCase.kt — only if included
class Submit[Feature]UseCase @Inject constructor(
    private val repository: [Feature]Repository
) {
    suspend operator fun invoke(input: [Feature]Input): Result<[Feature]> {
        // orchestration/business rule that doesn't belong in the ViewModel or Repository
        return repository.create[Feature](input)
    }
}
```

Domain model and use case files import no Retrofit/Room/Android framework types — verify before
finalizing this section.

---

## 6. ViewModel Design

**Rule**: the ViewModel MUST NOT hold an Android `Context`, `View`, or `Activity`/`Fragment`
reference — it outlives the config-change-destroyed Activity and leaking that reference is a
memory leak. It depends only on the Repository/use-case interface (wired by Hilt), never on
Retrofit/Room concrete types directly.

```kotlin
// presentation/[Feature]UiState.kt
sealed interface [Feature]UiState {
    data object Loading : [Feature]UiState
    data object Empty : [Feature]UiState
    data class Error(val message: String) : [Feature]UiState
    data class Success(val data: [Feature]) : [Feature]UiState
}

// presentation/[Feature]ViewModel.kt
// Traceability: SDS M-XX Section 6
@HiltViewModel
class [Feature]ViewModel @Inject constructor(
    private val repository: [Feature]Repository        // or the use case, per Section 5
) : ViewModel() {

    private val _uiState = MutableStateFlow<[Feature]UiState>([Feature]UiState.Loading)
    val uiState: StateFlow<[Feature]UiState> = _uiState.asStateFlow()

    fun onScreenEntered(id: String) {
        viewModelScope.launch {
            repository.observe[Feature](id)
                .catch { e -> _uiState.value = [Feature]UiState.Error(e.message ?: "unknown") }
                .collect { data -> _uiState.value = [Feature]UiState.Success(data) }
            repository.refresh[Feature](id)   // trigger network refresh; Room Flow above emits the update
        }
    }

    fun onSubmit(input: [Feature]Input) {
        viewModelScope.launch {
            repository.create[Feature](input)
                .onFailure { e -> _uiState.value = [Feature]UiState.Error(e.message ?: "unknown") }
        }
    }
}
```

**UI states specified**:

| State | Trigger | UI renders |
|-------|---------|------------|
| Loading | Screen entry, before first emission | Spinner/skeleton |
| Empty | Successful fetch, zero results | Empty-state illustration + CTA |
| Error | Repository call throws / `Result.failure` | Error message + retry action |
| Success | Data available | [Feature] content |

---

## 7. UI Layer Design (Composable/View)

The UI layer observes `uiState` and renders — it holds **no** business logic. State flows down
ViewModel → UI; events flow up UI → ViewModel (button clicks, form input call ViewModel methods,
never mutate state directly).

```kotlin
// presentation/[Feature]Screen.kt
@Composable
fun [Feature]Screen(viewModel: [Feature]ViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        is [Feature]UiState.Loading -> LoadingIndicator()
        is [Feature]UiState.Empty -> EmptyState(onRetry = { viewModel.onScreenEntered(id) })
        is [Feature]UiState.Error -> ErrorState(state.message, onRetry = { viewModel.onScreenEntered(id) })
        is [Feature]UiState.Success -> [Feature]Content(
            data = state.data,
            onSubmit = viewModel::onSubmit    // event flows up
        )
    }
}
```

If this project uses the legacy View system instead: `Fragment` observes `uiState` via
`viewLifecycleOwner.lifecycleScope.launch { viewModel.uiState.collect { render(it) } }` and a
`render()` function toggles View visibility per state — same one-way data flow, no business logic
in the Fragment.

---

## 8. Navigation

**Architecture**: single-Activity, [Navigation component with `NavHost`/`NavGraph` XML |
Compose Navigation with `NavHost`/`composable()` routes].

| Destination | Route | Arguments | Entered from |
|-------------|-------|-----------|----------------|
| `[Feature]Screen` | `feature/{id}` | `id: String` | [caller screen] |

Deep link handling (if applicable): [state the intent-filter/URI pattern and how the argument is
validated before use — see Client Security Design, Section 10].

---

## 9. Accessibility Design

- **TalkBack support**: every interactive element (`Button`, `IconButton`, clickable `Card`) has
  a `contentDescription` (Compose) or `android:contentDescription` (View) — decorative-only
  images set `contentDescription = null` explicitly so TalkBack skips them
- **Touch target sizing**: interactive elements meet the 48dp minimum touch target
  (`Modifier.size(minimum = 48.dp)` or equivalent) even when the visual icon is smaller
- **Focus order**: [state the traversal order for screen-reader focus if the layout isn't
  top-to-bottom, left-to-right]
- **Dynamic text scaling**: text uses `sp` (not `dp`) so it respects the user's font-scale setting

---

## 10. Client Security Design

> Client-relevant subset of `design/references/security-checklist.md` only — the server-side
> subset (SQL injection, rate limiting) is the backend SDS's concern, not this one.

- **Token storage**: [`EncryptedSharedPreferences` | Android Keystore-backed encryption] for the
  auth token — never `SharedPreferences` in plaintext
- **Certificate pinning**: [state whether the SRS requires it; if so, name the pinning config
  (OkHttp `CertificatePinner`) and pin rotation plan] — or "N/A, not required by SRS"
- **Deep link / intent validation**: any argument arriving via a deep link or `Intent` extra is
  validated/sanitized before use (never trusted as-is — a malicious app can craft an intent)
- **Sensitive data in logs**: no token/PII logged via `Log.d`/`Log.i` in release builds — confirm
  via a lint rule or `Timber` tree that no-ops in release

---

## 11. Client Performance Design

> Client-relevant subset of `design/references/performance-checklist.md` only.

- **Recomposition scope**: state-reading composables are scoped as narrowly as possible;
  `remember`/`key` used for expensive computations and to give a stable identity to list items
- **Stable lambdas**: callbacks passed to child composables are hoisted/remembered
  (`remember { { viewModel.onSubmit(it) } }` or a method reference) so an unstable lambda doesn't
  force every child to recompose
- **List rendering**: `LazyColumn`/`LazyRow` (not `Column` + `forEach`) for any list that can grow
  beyond a handful of items
- **Image loading**: Coil (`AsyncImage`) with memory + disk caching enabled; explicit `size()`/
  `Scale` to avoid decoding a full-resolution bitmap for a thumbnail slot
- **Startup cost**: [state whether this screen is reachable from cold start / app's first screen,
  and if so, the target time-to-first-frame]

---

## 12. Data Integrity

State "N/A" unless this feature uses Room for offline-first sync (writes made offline, synced
later). If offline-first:

- **Conflict resolution rule**: [e.g. last-write-wins by `updatedAt`, or a stated merge rule —
  never silently overwrite without a rule]
- **Sync trigger**: [WorkManager periodic/one-time sync job, or app-foreground trigger]
- **Local write markers**: a `syncStatus` column (`PENDING`/`SYNCED`/`FAILED`) on the entity so a
  failed sync is retryable and visible

---

## 13. Operations Readiness

**N/A — not a deployed service.** A mobile feature isn't a process with liveness/readiness
probes. Note crash-reporting wiring only if the SRS mentions it: [e.g. "Firebase Crashlytics
non-fatal logging on `refresh[Feature]()` failure, tagged with `feature=[feature]`"] — otherwise
state "no additional crash-reporting hook beyond the app-wide default."

---

## 14. Test Plan

### 14.1 ViewModel Unit Tests (JUnit + a fake Repository, no real network/DB)

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `onScreenEntered_success` | Fake repository emits data | `uiState` becomes `Success` |
| `onScreenEntered_empty` | Fake repository emits empty list | `uiState` becomes `Empty` |
| `onScreenEntered_error` | Fake repository throws | `uiState` becomes `Error` with message |
| `onSubmit_success` | Fake repository returns `Result.success` | `uiState` reflects updated data |
| `onSubmit_failure` | Fake repository returns `Result.failure` | `uiState` becomes `Error`, input not lost |

### 14.2 Compose/Espresso Instrumented Tests (one per UI state)

| Test Case | UI State | Assertion |
|-----------|----------|-----------|
| Loading renders | `Loading` | Progress indicator node exists |
| Empty renders | `Empty` | Empty-state text + retry button exist |
| Error renders | `Error` | Error message + retry button exist, retry triggers `onScreenEntered` again |
| Success renders | `Success` | Content matches fake data, submit button forwards `onSubmit` event |

### 14.3 SRS Traceability

| SRS Requirement | Implemented In |
|-------------------|------------------|
| FR-01: [requirement] | ViewModel method: [name], Screen: `[Feature]Screen` |
| BR-01: [business rule] | Repository/use-case logic |

---

## 15. Design Decisions & Alternatives

Per `.claude/skills/design/references/decision-records.md` §2 — record any costly-to-reverse
choice (e.g. Compose vs. legacy View for this screen, Room vs. DataStore for local cache,
BLoC-equivalent state shape) with alternatives considered and why this one won.

## 16. Risks & Trade-offs

[State risks — e.g. "no offline support; screen unusable without connectivity" — and whether
that's accepted or deferred.]

## 17. Implementation Mapping

| SDS Section | Implementation File |
|--------------|---------------------|
| §6 ViewModel | `presentation/{feature}/{Feature}ViewModel.kt` |
| §4 Data layer | `data/repository/{Feature}RepositoryImpl.kt` |
| §5 Domain (if present) | `domain/{feature}/{Feature}UseCase.kt` |

## 18. Implementation Readiness

**Status**: [READY | PARTIALLY_READY | BLOCKED]
[State any `[NEEDS BACKEND SDS]`/`[NEEDS SPEC CLARIFICATION]`/`[A11Y TARGET NOT STATED]` items and
what `/implement` can start on now vs. what's blocked.]
```

---

## NAMING CONVENTIONS (MODE J)

Discover exact conventions from CLAUDE.md/the project's existing feature modules — below are
typical patterns:

- SDS path: `docs/04-sds/M-XX-module-name.md`
- Package: `{basePackage}.feature.{feature}.{layer}` lowercase
- ViewModel: `{Feature}ViewModel`, always `@HiltViewModel`
- UI state: `{Feature}UiState` sealed interface with `Loading`/`Empty`/`Error`/`Success`
- Repository interface: `{Feature}Repository`; implementation: `{Feature}RepositoryImpl`
- Use case: `{Verb}{Feature}UseCase` with `operator fun invoke(...)`
- Room entity: `{Feature}Entity`; DAO: `{Feature}Dao`
- Retrofit/Ktor service: `{Feature}ApiService`
- DTO: `{Feature}Dto` / `{Feature}RequestDto` — never reused as the domain model
- Composable screen: `{Feature}Screen`; content composable: `{Feature}Content`
- Test class: `{ClassUnderTest}Test` (unit), `{ClassUnderTest}Test` under `androidTest/` (instrumented)

---

## LAYERING RULES (MODE J)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|----------------|
| domain (model, repository interface, use case) | Kotlin stdlib, coroutines | Retrofit, Room, `android.*`, Compose |
| data (repository impl, DAO, API service) | domain, Retrofit, Room, DTOs | ViewModel, Composable |
| presentation (ViewModel) | domain (repository interface/use case), `androidx.lifecycle.ViewModel`, coroutines | `android.content.Context`, `android.view.View`, `Activity`, `Fragment`, Retrofit, Room directly |
| presentation (Composable/View) | ViewModel (via `hiltViewModel()`/DI), UI state | domain business logic, Retrofit, Room |

**ViewModel Design:**
- Exposes `StateFlow`/`LiveData` only — never a mutable field a Composable can write to directly
- Never holds a `Context`/`View`/`Activity`/`Fragment` reference (memory leak: the ViewModel
  survives a config-change-destroyed Activity via `ViewModelStore`, so a held Activity reference
  keeps the destroyed Activity alive)
- Never calls Retrofit/Room directly — always through the Repository interface, so the ViewModel
  is testable with a fake Repository and has no dependency on a real network/DB in unit tests

**Repository Pattern:**
```kotlin
// Repository is the single source of truth per data type — it decides local-vs-remote,
// caching, and refresh policy; callers (ViewModel, use case) never see Retrofit/Room directly
interface [Feature]Repository {
    fun observe[Feature](id: String): Flow<[Feature]>
}
```

**SDS Traceability Comment (required):**
```kotlin
// Traceability: SDS M-XX Section Y.Z [Operation Name]
override suspend fun create[Feature](input: [Feature]Input): Result<[Feature]> { ... }
```

**SDS Design Principle:**
Design from the Repository outward (Repository → optional Domain use case → ViewModel → UI →
Navigation) — Google's recommended app architecture's inside-out discipline, same as MODE B/D's
Entity-first ordering adapted to a client app's data/API layer instead of a server's persistence
layer. Don't design the Composable/screen first and only think about where its data comes from
afterward.
