# Implement Skill — iOS (Swift) Reference Material

> Load this when implementing an iOS mobile feature (MODE K — Swift, MVVM + SwiftUI/UIKit). It
> complements `verification-checklist.md` — that file's language-agnostic checklist (linting,
> testing, secrets scan, docs) still applies; this file adds the traps specific to this stack.
> It does not restate the generic `security-checklist.md`/`performance-checklist.md` content —
> only what's actually iOS-specific.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ Strong `self` capture in a long-lived closure

```swift
func loadProfile() {
    apiClient.fetchProfile { result in
        // strong capture of self inside a completion handler held by apiClient —
        // if apiClient outlives this ViewModel (e.g. the request is still in flight
        // when the user navigates away), self is kept alive too, and any UI update
        // below fires against a ViewModel nobody is showing anymore
        switch result {
        case .success(let profile): self.profile = profile
        case .failure(let error): self.error = error
        }
    }
}
```

### ✅ `[weak self]` in the closure, guard before using it

```swift
func loadProfile() {
    apiClient.fetchProfile { [weak self] result in
        guard let self else { return }
        switch result {
        case .success(let profile): self.profile = profile
        case .failure(let error): self.error = error
        }
    }
}
```

**Why this is better:** the completion handler no longer extends the ViewModel's lifetime past
when it should end, which avoids both a memory leak and a stale-state UI update firing after the
screen is gone. The same rule applies to a Combine `.sink { [weak self] in ... }` subscription
held in a `Set<AnyCancellable>` — any closure captured by something that outlives the immediate
call site needs `[weak self]`, not just network completion handlers.

---

### ❌ Mutating `@Published`/UI state off the main thread

```swift
func loadItems() {
    URLSession.shared.dataTask(with: url) { data, _, _ in
        let items = try? JSONDecoder().decode([Item].self, from: data ?? Data())
        self.items = items ?? [] // completion handler runs on a background queue —
                                 // this mutates a @Published property off the main thread
    }.resume()
}
```

### ✅ Hop back to the main actor before touching `@Published` state

```swift
@MainActor
final class ItemsViewModel: ObservableObject {
    @Published private(set) var items: [Item] = []

    func loadItems() async {
        guard let data = try? await URLSession.shared.data(from: url).0,
              let decoded = try? JSONDecoder().decode([Item].self, from: data) else { return }
        items = decoded // safe: this method runs on the main actor because the class is @MainActor
    }
}
```

**Why this is better:** SwiftUI/UIKit rendering asserts (or silently corrupts state) when a
`@Published`/UI property is written from a background thread. Marking the ViewModel `@MainActor`
(or wrapping the specific mutation in `await MainActor.run { ... }` / `DispatchQueue.main.async`
for a completion-handler-based API) guarantees every UI-facing write happens on the main thread.

---

### ❌ Force-unwrapping an expected-nil field

```swift
struct ProfileResponse: Decodable {
    let displayName: String
    let avatarURL: String?
}

let url = URL(string: profile.avatarURL!)! // avatarURL is legitimately nil for users
                                            // who haven't uploaded an avatar — this is
                                            // an expected case, not a programmer error,
                                            // and it crashes the app when it happens
```

### ✅ Model the absence explicitly

```swift
let avatarURL: URL? = profile.avatarURL.flatMap(URL.init(string:))
// View renders a placeholder image when avatarURL is nil — no crash, no force-unwrap
```

**Why this is better:** `!` is appropriate only for a genuine invariant the programmer can prove
holds (e.g. an array index known by construction to be valid) — not for a network response field
that is *documented* as optional. "This will never be nil in practice" is exactly the case that
eventually is nil, in production, for one user, at 2am.

---

### ❌ Core Data context touched from the wrong queue

```swift
func importRecords(_ records: [RecordDTO]) {
    for record in records {
        let entity = RecordEntity(context: mainContext) // called from a background
        entity.name = record.name                       // Task/URLSession callback —
    }                                                     // mainContext was created on
    try? mainContext.save()                              // the main thread/queue
}
```

### ✅ Use a background context scoped to its own queue, merge back

```swift
func importRecords(_ records: [RecordDTO]) async throws {
    let bgContext = persistentContainer.newBackgroundContext()
    try await bgContext.perform {
        for record in records {
            let entity = RecordEntity(context: bgContext)
            entity.name = record.name
        }
        try bgContext.save() // saves propagate to mainContext via
    }                          // NSPersistentContainer's automatic merge, or
}                               // an explicit NSManagedObjectContextDidSave observer
```

**Why this is better:** every `NSManagedObjectContext` (Core Data) or `ModelContext` (SwiftData)
is confined to the queue/actor it was created on — accessing one from a different thread is
undefined behavior that can corrupt the object graph or crash intermittently, not deterministically,
which makes it far harder to catch in testing than in production.

---

### ❌ A View/ViewController doing networking directly

```swift
struct ProfileView: View {
    @State private var profile: Profile?

    var body: some View {
        VStack { /* ... */ }
            .task {
                let (data, _) = try! await URLSession.shared.data(from: profileURL) // networking
                profile = try! JSONDecoder().decode(Profile.self, from: data)        // and business
            }                                                                        // logic live
    }                                                                                // in the View
}
```

### ✅ Delegate to a ViewModel

```swift
struct ProfileView: View {
    @StateObject var viewModel: ProfileViewModel

    var body: some View {
        VStack { /* renders viewModel.state */ }
            .task { await viewModel.load() }
    }
}
// ProfileViewModel owns the Repository call, decoding, and error handling — see
// sds-template-ios-mobile.md Section 5.
```

**Why this is better:** a View/ViewController that fetches and decodes its own data can't be
unit-tested without spinning up the network, and duplicates parsing/error-handling logic across
every screen that needs the same data. The ViewModel is the only place `try!`/force-unwraps like
the example above should never appear either — see the force-unwrap trap above.

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — iOS specifics slot in as follows:

### **P0 - Critical**
- No `!` force-unwrap on a value that is a normal, expected-nil case (optional network field,
  optional user input) — reserve `!` for a provable invariant only
- Every `@Published`/UI-facing mutation happens on the main thread/`@MainActor` — no background
  completion handler or `Task` writes UI state without hopping back first
- Every closure captured by a long-lived object (network completion handler, Combine
  subscription in a `Set<AnyCancellable>`, `NotificationCenter` observer block) captures
  `self` as `[weak self]`, with a `guard let self else { return }` before use
- Tokens/secrets stored in the Keychain — never `UserDefaults`, never a plain file

### **P1 - High**
- View/ViewController contains no networking or business logic — only renders ViewModel state
  and forwards user actions
- Core Data/SwiftData context accessed only from the thread/queue/actor it was created on;
  background imports use a dedicated background context, not the main context from a background task
- ViewModel constructed with an injected Repository **protocol** type, not a concrete
  `URLSession`/persistence type, and not a `Manager.shared` singleton reached into internally

### **P2 - Medium**
- XCTest coverage for the ViewModel with a fake Repository (success, empty, error states)
- UI test coverage for each screen state (loading, empty, error, loaded)
- Accessibility labels/hints on interactive elements; Dynamic Type-safe layout

### **P3 - Low**
- Image loading/caching tuned (memory vs. disk cache policy)
- List/`LazyVStack` cell-reuse verified for large collections

---

## VERIFICATION CHECKLIST (iOS additions)

Run these in addition to the general checklist:

### 1. Code Quality
```bash
xcodebuild -scheme {Scheme} -destination 'generic/platform=iOS Simulator' build
swiftlint lint         # if configured — otherwise skip
```
- [ ] No stray `print(...)` left in production code paths carrying tokens/PII

### 2. Correctness
- [ ] `grep -rn '!' --include='*.swift'` reviewed by hand for force-unwraps on genuinely optional
  data (network response fields, user input) — not just a blanket ban, a judgment pass
- [ ] Every `@Published`/UI mutation site traced back to confirm it runs on `@MainActor`/main queue
- [ ] Every closure held by a long-lived object (`URLSession` completion handler, Combine
  `.sink`, `NotificationCenter.addObserver`) captures `[weak self]`

### 3. Security
- [ ] Tokens/credentials stored via Keychain wrapper, not `UserDefaults` — verify by reading the
  actual storage call, not assuming from the variable name
- [ ] No sensitive field logged via `print`/`os_log` at a level that ships in a release build
- [ ] Certificate pinning implemented if the SDS's Client Security Design section required it

```bash
grep -rn "UserDefaults" --include='*.swift' | grep -iE "token|password|secret|credential"
grep -rn "print(" --include='*.swift'
```

### 4. Testing
```bash
xcodebuild test -scheme {Scheme} -destination 'platform=iOS Simulator,name={Simulator}'
```
- [ ] ViewModel tests inject a fake/mock Repository conforming to the same protocol — never hit
  the real network or a real Core Data store
- [ ] Every `ViewState`/UI-state case from the SDS (§5.2 of the SDS template) has a corresponding
  test: loading, empty, loaded, error
- [ ] UI tests cover each screen state, not just the happy path

### 5. Performance
- [ ] Any collection rendered in a `VStack` instead of `List`/`LazyVStack` is checked — unbounded
  growth in a plain `VStack` renders every row eagerly instead of reusing views
- [ ] `UITableView`/`UICollectionView` cells (if UIKit) use `dequeueReusableCell`, not a fresh
  instantiation per row
- [ ] Remote images load asynchronously (`AsyncImage` or an established caching loader) — no
  synchronous `Data(contentsOf:)` on a remote URL from the main thread

```bash
grep -rn "Data(contentsOf:" --include='*.swift'
```

### 6. Data Integrity (only if this feature uses Core Data/SwiftData)
- [ ] Every context (`NSManagedObjectContext`/`ModelContext`) access happens on the
  thread/actor it was created on — background writes use a dedicated background context
- [ ] Conflict/merge policy matches what the SDS's Data Integrity section specified — not left
  at the framework default without a stated reason

```bash
grep -rn "perform {" --include='*.swift'
grep -rn "newBackgroundContext" --include='*.swift'
```

---

## TROUBLESHOOTING

**A screen's state silently stops updating after the user navigates away and back:**
Check for a retained `[weak self]`-less closure from a still-in-flight network call from the
*previous* instance of the ViewModel — the old instance is being kept alive and racing the new
one, or the completion handler is firing against a ViewModel no view is observing anymore.

**"Publishing changes from background threads is not allowed" runtime warning/crash:**
A `@Published` property was mutated outside the main actor. Trace the call stack to the
completion handler/`Task` that set it and wrap the mutation in `@MainActor`/`DispatchQueue.main.async`,
or mark the owning method/class `@MainActor` as shown in the GOOD example above.

**Intermittent, non-reproducible Core Data crash or corrupted data:**
Almost always a context used from the wrong thread — grep for the `NSManagedObjectContext`
instance's creation site and confirm every read/write on it happens via `context.perform { }` /
on the queue it was created on, not assumed safe because "it usually works."

**A test that force-unwraps a decoded response passes locally but crashes in the field:**
The real API returned a legitimately-nil optional field that the test fixture always populated.
Add a test case with that field nil/missing and fix the force-unwrap at the source, per the
force-unwrap trap above — don't just patch the test fixture.

**SwiftUI Previews crash but the app runs fine on a simulator/device:**
Usually a ViewModel/Repository initializer that isn't given a fake/preview-safe dependency in
the `#Preview` block — confirm the Repository protocol has a preview/fake conformance available
rather than the preview trying to hit the real network.
