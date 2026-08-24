# SDS Template K: iOS Mobile Feature (Swift, MVVM)

> Reference for `design` skill — loaded on demand when creating MODE K SDS documents.
>
> **First, verify the Swift toolchain and UI framework.** Check `Package.swift`/the Xcode
> project's deployment target for the minimum iOS version, and whether the project uses SwiftUI,
> UIKit, or both — a SwiftUI-only design against a UIKit-only project produces code that doesn't
> compile into the existing screen. Also check whether networking already uses raw `URLSession`
> or a wrapper (Alamofire, Combine) — match the established idiom, don't introduce a second one.

---

## TEMPLATE K: iOS Mobile Feature SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: Swift {version}, {SwiftUI | UIKit} — iOS {minimum deployment target}+

---

## 1. Module Overview

### 1.1 Description
[Describe what this feature/screen does in the app]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Module Type**: [Screen / Screen Flow / Reusable Feature Component]
**Scale Tier**: N/A in the backend sense — this is a client feature. State only whether this
screen's domain complexity justifies Clean Architecture/VIPER or a unidirectional store (The
Composable Architecture) over plain MVVM, with a one-line reason
(`.claude/skills/architecture/references/mobile-patterns.md` §2). Default is plain MVVM.

**[DESIGN DECISION]** MVVM (default) | Clean Architecture/VIPER | Unidirectional store (TCA) —
[one-line domain-complexity justification]

### 1.3 File Layout

```
{ModuleName}/
├── Repository/{Entity}Repository.swift        # protocol — abstraction the ViewModel depends on
├── Repository/{Entity}RemoteDataSource.swift   # URLSession-backed concrete implementation
├── Repository/{Entity}LocalDataSource.swift    # Core Data/SwiftData-backed concrete implementation (if offline/caching)
├── Model/{Entity}.swift                        # Codable DTO / domain model
├── ViewModel/{Screen}ViewModel.swift            # ObservableObject, @Published state
├── View/{Screen}View.swift                      # SwiftUI View — or {Screen}ViewController.swift for UIKit
└── Navigation/{Feature}Coordinator.swift        # or NavigationStack/NavigationPath owner
```

**Entities/Models**: [List Codable models]
**Screens**: [List screens this SDS covers]
**Dependencies**: [M-01 Auth for token, etc.]

---

## 2. Architecture Context

**Layer order (inside-out — design in this sequence, don't start from the View):**

```
Repository/Service protocol  →  ViewModel  →  View/ViewController  →  Navigation flow
```

- **Repository/Service protocol**: abstracts networking (`URLSession`) and persistence (Core
  Data/SwiftData) behind a protocol. The ViewModel depends on the protocol only, never on a
  concrete `URLSession`/`NSManagedObjectContext` type — this is what keeps the ViewModel testable
  without hitting the network or disk.
- **ViewModel**: `ObservableObject` with `@Published` state in SwiftUI, or a plain class exposing
  state via Combine/delegate callback in UIKit. Owns all presentation logic — screen state
  transitions, formatting, validation. Holds no `UIView`/`UIViewController` reference.
- **View/ViewController**: renders the ViewModel's published state and forwards user actions
  (`func onTapSubmit()`) back to it. Contains no networking, no business logic, no direct
  Core Data/SwiftData access.
- **Navigation flow**: owned outside the View itself — a `NavigationStack`/`NavigationPath` bound
  to ViewModel-published state, or a Coordinator object — never a View reaching into another
  View's ViewModel to trigger a push/present.

**Why MVVM by default**: plain MVC degrades into "Massive View Controller" once a screen has
real logic (validation, multiple async states, navigation decisions) — MVVM's ViewModel gives
that logic a home that unit-tests without `UIKit`/`SwiftUI` imports. Clean Architecture/VIPER or
a Redux-style store (TCA) are justified only once §1.2's domain-complexity check says yes for
*this* screen (e.g. a multi-step wizard with cross-step validation, or heavy state shared across
several independent modules) — don't reach for either extreme as a default.

---

## 3. Backend API Contract

> Pull this from the real backend SDS for the endpoints this feature calls. If no backend SDS
> exists yet for one, write `[NEEDS BACKEND SDS]` literally — never invent the request/response
> shape from what "seems reasonable."

| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| GET | /api/v1/[resource] | Bearer | — (query params: `[param]`) | `[Entity]Response` |
| POST | /api/v1/[resource] | Bearer | `[Entity]Request` | `[Entity]Response` |

**[Entity]Request / [Entity]Response shape**: [NEEDS BACKEND SDS] or paste the actual JSON shape
from `M-XX` backend SDS Section 4.2, with the exact field names/types/nullability — a
Swift-side `Codable` model built from a guessed shape is a common source of silent decode
failures once the real API responds with a field this SDS didn't expect.

---

## 4. Repository/Service Design

### 4.1 Protocol

```swift
// Repository/[Entity]Repository.swift
// Traceability: SDS M-XX Section 4.1
protocol [Entity]Repository {
    func fetch[Entity](id: String) async throws -> [Entity]
    func fetch[Entity]List() async throws -> [[Entity]]
    func create[Entity](_ request: [Entity]Request) async throws -> [Entity]
}
```

### 4.2 Concrete Implementation (`URLSession`)

```swift
// Repository/[Entity]RemoteDataSource.swift
// Traceability: SDS M-XX Section 4.2
final class [Entity]RemoteDataSource: [Entity]Repository {
    private let session: URLSession
    private let baseURL: URL
    private let tokenProvider: TokenProviding // protocol — never reads Keychain directly here

    init(session: URLSession = .shared, baseURL: URL, tokenProvider: TokenProviding) {
        self.session = session
        self.baseURL = baseURL
        self.tokenProvider = tokenProvider
    }

    func fetch[Entity](id: String) async throws -> [Entity] {
        var request = URLRequest(url: baseURL.appendingPathComponent("api/v1/[resource]/\(id)"))
        request.setValue("Bearer \(try await tokenProvider.token())", forHTTPHeaderField: "Authorization")

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            throw [Entity]Error.requestFailed((response as? HTTPURLResponse)?.statusCode)
        }
        return try JSONDecoder.iso8601.decode([Entity].self, from: data)
    }
}

enum [Entity]Error: Error {
    case requestFailed(Int?)
    case decodingFailed
    case offline
}
```

**Errors are typed** (`[Entity]Error`), never a bare `Error` bag the ViewModel has to
string-match — the ViewModel's UI-state enum (§5.2) maps directly off these cases.

### 4.3 Persistence (Core Data/SwiftData) — only if this feature caches or works offline

```swift
// Repository/[Entity]LocalDataSource.swift
// Traceability: SDS M-XX Section 4.3
final class [Entity]LocalDataSource {
    private let modelContainer: ModelContainer // SwiftData — or NSPersistentContainer for Core Data

    func save(_ entity: [Entity]) throws { /* write on the context's own thread — see Section 11 */ }
    func load(id: String) throws -> [Entity]? { /* ... */ }
}
```

State explicitly whether this feature needs local persistence at all — write "N/A — remote-only,
no offline requirement" if not, rather than adding a Core Data/SwiftData layer nothing calls.

---

## 5. ViewModel Design

### 5.1 Published State

```swift
// ViewModel/[Screen]ViewModel.swift
// Traceability: SDS M-XX Section 5
@MainActor
final class [Screen]ViewModel: ObservableObject {
    @Published private(set) var state: ViewState = .idle
    @Published var [inputField]: String = ""

    private let repository: [Entity]Repository // protocol — never a concrete URLSession/DataSource type

    init(repository: [Entity]Repository) {
        self.repository = repository
    }
}
```

### 5.2 UI State — spec every case, not just the happy path

```swift
enum ViewState {
    case idle
    case loading
    case empty
    case loaded([Entity])
    case error([Entity]Error)
}
```

| State | Trigger | View Behavior |
|-------|---------|----------------|
| `.idle` | Initial, before first load | Blank/skeleton |
| `.loading` | `load()` called | Spinner, disable actions |
| `.empty` | Load succeeded, zero results | Empty-state illustration + CTA |
| `.loaded([Entity])` | Load succeeded, N results | Render list/detail |
| `.error([Entity]Error)` | Load/create threw | Error view with retry action, message mapped from the error case |

### 5.3 Intents (methods the View calls)

```swift
func load() async {
    state = .loading
    do {
        let items = try await repository.fetch[Entity]List()
        state = items.isEmpty ? .empty : .loaded(items)
    } catch let error as [Entity]Error {
        state = .error(error)
    } catch {
        state = .error(.requestFailed(nil))
    }
}
```

No force-unwrap (`!`) anywhere in this method for a value that's a normal, expected-nil case
(a missing optional field in the decoded response) — model it through `ViewState`/`[Entity]Error`
instead. Reserve `!`/`fatalError` for a genuine programmer invariant (e.g. an `IndexPath` known
by construction to be in range), and say so explicitly if this SDS uses one.

---

## 6. View/ViewController Design

```swift
// View/[Screen]View.swift
// Traceability: SDS M-XX Section 6
struct [Screen]View: View {
    @StateObject var viewModel: [Screen]ViewModel

    var body: some View {
        Group {
            switch viewModel.state {
            case .idle, .loading: ProgressView()
            case .empty: [Screen]EmptyView()
            case .loaded(let items): [Screen]ListView(items: items)
            case .error(let error): [Screen]ErrorView(error: error, onRetry: { Task { await viewModel.load() } })
            }
        }
        .task { await viewModel.load() }
    }
}
```

For a UIKit screen: `{Screen}ViewController` holds the same `[Screen]ViewModel` via
initializer injection, subscribes to `@Published`/Combine changes in `viewDidLoad`, and forwards
`IBAction`/target-action callbacks to ViewModel methods — it renders and forwards only, exactly
like the SwiftUI `View` above. State which of the two (SwiftUI View or UIKit ViewController) this
screen actually uses; don't spec both unless the feature genuinely hosts one inside the other.

---

## 7. Navigation Flow

- **Mechanism**: [`NavigationStack` + `NavigationPath` bound to ViewModel-published route state |
  Coordinator pattern | UIKit `UINavigationController` push/present driven by a delegate callback]
- **Entry point**: [where this screen is pushed/presented from]
- **Exit points**: [back, success → next screen, cancel → dismiss] — state which ViewModel event
  (a `@Published var route: Route?` or a delegate call) drives each transition; the View itself
  never decides where to navigate, it only reflects the ViewModel's navigation state.

```
[Screen A] --(tap item)--> [Screen B] --(save success)--> [Screen A] (pop)
                                    \--(cancel)--> [Screen A] (pop)
```

---

## 8. Accessibility Design

- **VoiceOver**: every interactive element has `.accessibilityLabel` (what it is) and, where the
  action isn't obvious from the label, `.accessibilityHint` (what happens on activation) —
  list the non-obvious ones here: `[element] → label: "...", hint: "..."`
- **Dynamic Type**: text uses `.font(.body)`/semantic text styles, not a fixed point size;
  layout uses `ScrollView`/adaptive stacks so a large Dynamic Type setting doesn't clip content
- **Minimum tap target**: every tappable control is at least 44×44 pt (Apple HIG minimum) —
  call out any control that visually looks smaller and needs a padded hit area
  (`.contentShape(Rectangle())` sized up, not just the visible glyph)

---

## 9. Client Security Design

> Client-relevant subset of `design/references/security-checklist.md` only — this is a client
> feature, not a service; skip server-side sections (SQL injection, `@Transactional` locking,
> etc.) entirely.

- **Token storage**: access/refresh tokens go in the **Keychain** (`kSecClassGenericPassword`
  or a wrapper) — never `UserDefaults`, never a plain file, since `UserDefaults` is unencrypted
  and readable via a jailbroken device or an unencrypted backup
- **Certificate pinning**: [state whether the SRS requires it for this feature's traffic; if
  yes, name the pinning mechanism (`URLSessionDelegate` + `SecTrust` evaluation, or a pinning
  library) — if the SRS doesn't call for it, state "N/A — not required by SRS"]
- **Sensitive data in memory/logs**: no token/PII in `print`/`os_log` at a level that ships to
  device logs in a release build; no sensitive field held in a `@Published` property that a
  screenshot/App-Switcher snapshot could expose (mark such a field `.privacySensitive()` or
  blur it in `sceneDidBecomeInactive` if the SRS flags it as sensitive)
- **Input validation**: request-side validation (§5.3) at the ViewModel boundary before it ever
  reaches the Repository — the Repository is not the place to first notice a malformed input

---

## 10. Client Performance Design

> Client-relevant subset of `design/references/performance-checklist.md` only — no server-side
> sections (connection pools, DB indexing) apply here.

- **List rendering**: `List`/`LazyVStack` for any collection that can grow beyond a screenful —
  never a plain `VStack` over an unbounded array, since that eagerly renders every row instead of
  reusing cells; for UIKit, confirm `UITableView`/`UICollectionView` cell reuse (`dequeueReusableCell`)
  rather than instantiating a fresh cell per row
- **Image loading/caching**: async image loading (`AsyncImage`, or a caching image loader already
  in the project) — never a synchronous `Data(contentsOf:)` load on the main thread for a remote
  image URL; state the cache eviction policy (memory-only vs. disk-backed) if this screen loads
  many images
- **Main-thread discipline**: confirm every `@Published` mutation happens on the main
  thread/`@MainActor` — the ViewModel class or its mutating methods are annotated `@MainActor`
  (as in §5.1), and no background `Task`/`URLSession` completion handler mutates `@Published`
  state without hopping back to the main actor first
- **Pagination**: if the list can grow large, state the paging strategy (cursor/offset param,
  triggered on `.onAppear` of the last visible row) rather than fetching the entire collection

---

## 11. Data Integrity

State **"N/A — no local persistence"** unless this feature uses Core Data/SwiftData for
offline-first behavior. If it does:

- **Context confinement**: every Core Data `NSManagedObjectContext`/SwiftData `ModelContext`
  access happens on the queue/actor it was created on — a background import context
  (`performBackgroundTask`) never has its objects touched from the main thread and vice versa;
  state which context this feature's writes/reads use
- **Conflict resolution**: [merge policy — e.g. `NSMergeByPropertyObjectTrumpMergePolicy`, or a
  last-write-wins/field-level merge rule for SwiftData sync] — state the rule for what happens
  when a local edit and a server-fetched update disagree on the same record
- **Sync trigger**: [on foreground, on pull-to-refresh, background `BGTaskScheduler` job] and
  what happens to a locally-queued write if the sync fails (retry policy, or surfaced as a
  `.error` state to the user)

---

## 12. Operations Readiness

State **"N/A — not a deployed service"** (this ships inside the app binary, not as a standalone
service with its own uptime/on-call concerns). Note only:

- **Crash reporting**: [name the crash-reporting SDK wiring — e.g. this screen's key user
  actions are wrapped with breadcrumbs] only if the SRS explicitly calls for crash/analytics
  instrumentation on this feature; otherwise state "N/A — not called out in SRS"

---

## 13. Test Plan

### 13.1 ViewModel Unit Tests (XCTest, fake Repository)

```swift
final class [Screen]ViewModelTests: XCTestCase {
    func test_load_success_setsLoadedState() async {
        let fake = Fake[Entity]Repository(result: .success([.stub]))
        let sut = [Screen]ViewModel(repository: fake)
        await sut.load()
        XCTAssertEqual(sut.state, .loaded([.stub]))
    }

    func test_load_emptyResult_setsEmptyState() async { /* ... */ }
    func test_load_failure_setsErrorState() async { /* ... */ }
}
```

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `test_load_success_setsLoadedState` | Repository returns items | `.loaded([items])` |
| `test_load_emptyResult_setsEmptyState` | Repository returns `[]` | `.empty` |
| `test_load_failure_setsErrorState` | Repository throws `[Entity]Error` | `.error(...)` |

### 13.2 UI Tests (one per screen state)

| Test Case | Setup | Assertion |
|-----------|-------|-----------|
| Loading state renders spinner | Stub Repository never resolves | `ProgressView` visible |
| Empty state renders CTA | Stub returns `[]` | Empty-state view visible |
| Loaded state renders list | Stub returns N items | N rows visible |
| Error state renders retry | Stub throws | Error view + retry button visible; tapping retry re-invokes `load()` |

### 13.3 SRS Traceability

| SRS Requirement | Implemented In |
|-------------------|------------------|
| FR-01: [requirement] | ViewModel method: `[name]`, Screen: `[Screen]View` |
| FR-02: [requirement] | Repository method: `[name]` |

---

## 14. Design Decisions & Alternatives

- **[DESIGN DECISION]** [decision] — chosen over [alternative] because [reason]
- **[ASSUMPTION]** [assumption made in absence of a stated requirement]

## 15. Risks & Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| [e.g. backend endpoint shape not finalized] | Repository/Model rework if it changes | Marked `[NEEDS BACKEND SDS]` in Section 3; ViewModel isolated behind the protocol so only the Repository implementation changes |

## 16. Implementation Mapping

| SDS Section | Files |
|-------------|-------|
| §4 Repository | `Repository/[Entity]Repository.swift`, `Repository/[Entity]RemoteDataSource.swift` |
| §5 ViewModel | `ViewModel/[Screen]ViewModel.swift` |
| §6 View | `View/[Screen]View.swift` |

## 17. Implementation Readiness

**Gate**: [READY | PARTIALLY_READY | BLOCKED]
**Reason**: [e.g. "READY — backend contract confirmed in M-YY; all UI states specified" or
"BLOCKED — Section 3 API contract marked [NEEDS BACKEND SDS], cannot finalize Repository/Model until resolved"]
**Open items before implementation**: [list any `[OPEN QUESTION]`/`[NEEDS SPEC CLARIFICATION]` items]
```

---

## NAMING CONVENTIONS (MODE K)

Discover exact conventions from the target project's CLAUDE.md/existing files — below are
typical Swift/iOS patterns:

- SDS path: same as other modes — `docs/04-sds/M-XX-module-name.md`
- Types: `PascalCase` (`UserProfileViewModel`, not `userProfileViewModel`)
- Properties/methods: `camelCase`
- Protocol naming: a noun/capability, not `-able` unless it genuinely describes a capability
  (`UserRepository`, not `UserRepositoryProtocol`; `Loadable` is fine for a capability protocol)
- ViewModel: `{Screen}ViewModel`, always `final class`, `ObservableObject`
- View: `{Screen}View` (SwiftUI) or `{Screen}ViewController` (UIKit)
- Repository concrete implementations: `{Entity}RemoteDataSource` / `{Entity}LocalDataSource`,
  both conforming to the same `{Entity}Repository` protocol
- Test class: `{TypeUnderTest}Tests`, test method: `test_{scenario}_{expectedOutcome}`

---

## LAYERING RULES (MODE K)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|----------------|
| Model (Codable/domain) | Foundation | SwiftUI, UIKit, URLSession call sites |
| Repository protocol | Model, Foundation | SwiftUI, UIKit |
| Repository concrete impl | `URLSession`, Core Data/SwiftData, Model | SwiftUI, UIKit, ViewModel |
| ViewModel | Repository **protocol** (never the concrete impl type), Model, Combine | SwiftUI `View` types, `UIViewController`, `URLSession` directly |
| View/ViewController | ViewModel only | Repository (protocol or concrete), `URLSession`, Core Data/SwiftData directly |

**ViewModel construction rule:**
- The ViewModel's initializer takes a `{Entity}Repository` **protocol** type, injected — never
  constructs a concrete `URLSession`/Core Data stack itself and never reaches a
  `Manager.shared` singleton for its dependencies. This is what makes `Fake{Entity}Repository`
  substitution in §13.1 possible without touching the network.

**View/ViewController rule:**
- Never call `URLSession`/Core Data/SwiftData directly from a View or ViewController body/lifecycle
  method — that's the exact "Massive View Controller" failure mode MVVM exists to avoid. All such
  calls route through the ViewModel → Repository protocol chain.

**SDS Traceability Comment (required):**
```swift
// Traceability: SDS M-XX Section Y.Z [Operation Name]
func load() async { ... }
```

**SDS Design Principle:**
Design from the Repository/Service protocol outward (Repository protocol → ViewModel →
View/ViewController → Navigation) — same inside-out discipline as the other modes. Don't start
from the View's visual layout and only think about where the data comes from afterward.
