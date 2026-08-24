# Mobile Architecture Patterns

Stack-specific application of the axes decided in `architecture-selection.md`. Detect the
platform from `build.gradle`/`build.gradle.kts` (Android), `*.xcodeproj`/`Podfile`/`Package.swift`
(iOS), or `pubspec.yaml` (Flutter) before assuming.

## 1. Android

**Recommended: MVVM with a layered structure** (Google's own recommended app architecture):

```text
UI layer        — Composable/View + ViewModel. ViewModel exposes StateFlow/LiveData; the UI
                   observes and renders, never holds business logic itself.
Domain layer     — (optional, add when Axis 2's domain-complexity questions justify it) use cases
                   that orchestrate one piece of business logic, callable from multiple ViewModels.
Data layer       — Repository (single source of truth per data type) → local (Room) + remote
                   (Retrofit/Ktor) data sources. The Repository decides caching/refresh policy;
                   ViewModels never call Retrofit/Room directly.
```

- **Unidirectional Data Flow**: state flows down (ViewModel → UI), events flow up (UI → ViewModel)
  — with Compose + `StateFlow`, this is the default; avoid two-way bindings that let the UI mutate
  ViewModel state directly.
- **ViewModel must not hold an Android `Context`, `View`, or `Activity`/`Fragment` reference** —
  causes memory leaks and untestable ViewModels; anything Android-framework-specific belongs in the
  UI layer or is injected as an abstraction the ViewModel can use in tests.
- **Single-Activity architecture** with the Navigation component (or Compose Navigation) for
  screen-to-screen flow, rather than an Activity per screen.
- **Dependency injection (Hilt)** to wire Repository/use-case implementations into ViewModels,
  keeping them swappable for tests.

**Anti-patterns**: business/networking logic inside an Activity/Fragment; a ViewModel calling
Retrofit directly instead of through a Repository (loses the single-source-of-truth/caching point
and makes the ViewModel untestable without a real network); a `Utils`/`Manager` god-object
accumulating unrelated static methods.

## 2. iOS

**Recommended: MVVM (or Clean Architecture/VIPER for high domain-complexity apps)**:

- Plain **MVC** is the platform default but degrades into "Massive View Controller" once a screen
  has real logic — networking, validation, and navigation all end up in the `UIViewController`
  because there's no other designated place for them.
- **MVVM** fixes this for most apps: `ViewModel` (an `ObservableObject` in SwiftUI, or a plain
  class bound via Combine/delegate in UIKit) owns presentation logic and exposes state; the
  View/ViewController only renders and forwards user actions.
- **Clean Architecture / VIPER**, or a Redux-style unidirectional store (e.g. The Composable
  Architecture) for SwiftUI, are justified once Axis 2's domain-complexity questions
  (`architecture-selection.md` §2) say yes for this app — extra layers (Interactor, Presenter,
  explicit Entity/UseCase types) pay off exactly where the business logic is genuinely complex, and
  are ceremony for a simple CRUD-style app.
- **Repository/Service layer** below the ViewModel abstracts networking (`URLSession`) and
  persistence (Core Data/SwiftData) — the ViewModel depends on a protocol, not a concrete
  networking type, so it stays testable without hitting the network.

**Anti-patterns**: a `UIViewController` containing networking calls, business rules, and UI layout
together; singletons (`Manager.shared`) used as an implicit global state bus instead of injected
dependencies; force-unwrapping (`!`) as a substitute for modeling optionality/failure explicitly in
the domain.

## 3. Flutter

**Recommended: layered/Clean Architecture with a dedicated state-management library**:

```text
lib/features/orders/
├── presentation/    # widgets + state management (BLoC/Riverpod/Provider)
├── domain/          # entities, use cases, repository interfaces — no Flutter/dio imports
└── data/            # repository implementations, remote (dio/http) + local (drift/hive) sources
```

- **BLoC** (event-in, state-out) is Flutter's most idiomatic pattern for screens with non-trivial
  state transitions — it makes every state change an explicit, testable event handler. **Riverpod**
  is a simpler, more ergonomic default for state that doesn't need BLoC's explicit event modeling
  (most CRUD-style screens) — pick per-feature based on Axis 2's domain-complexity answer, the same
  judgment call as everywhere else in this skill, not a single app-wide mandate.
- **Business logic never lives inside a widget's `build()` method** — a widget's job is to render
  state and forward user interaction to the state-management layer; anything else makes the widget
  untestable without pumping a full widget tree.
- **Repository abstraction between domain and data sources** — the domain layer depends on a
  repository *interface*; the concrete implementation (calling `dio`/a local DB) lives in the data
  layer, keeping domain/presentation testable with a fake repository.
- **Feature-based folders**, same rationale as `modular-monolith.md` §2 — a feature's presentation/
  domain/data pieces live together, not scattered across app-wide `widgets/`, `models/`,
  `services/` directories.

**Anti-patterns**: `StatefulWidget`'s local `setState` used for state that's actually shared across
screens (should be lifted into the state-management layer); a widget calling `dio`/`http` directly
instead of through a repository; domain/use-case code importing Flutter widget types, coupling
business logic to the UI framework.
