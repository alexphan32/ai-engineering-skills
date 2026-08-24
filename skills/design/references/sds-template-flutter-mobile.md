# SDS Template L: Flutter Mobile Feature

> Reference for `design` skill — loaded on demand when creating MODE L SDS documents. This is a
> "Client UI" sibling mode: same inside-out discipline as the REST API modes (data layer first,
> screen last) and the same family as MODE J (Android) / MODE K (iOS), adapted to Flutter's
> layered Clean Architecture (domain / data / presentation) and Dart's lack of a single blessed
> state-management library — this template's job is landing a feature's design inside that
> layout, not re-deciding whether BLoC or Riverpod wins app-wide (that's a per-feature call made
> in Section 6, not decided here).

---

## TEMPLATE L: Flutter Mobile Feature SDS

```markdown
# M-XX: [Feature Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: Dart, Flutter, {state-management library — discover from `pubspec.yaml`;
> `flutter_bloc` and/or `flutter_riverpod`/`provider` may coexist in one app, chosen per feature}

---

## 1. Feature Overview

### 1.1 Description
[What this screen/feature does, in the app's context]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Scale Tier**: N/A in the backend sense — a client feature has no deployment tier. Instead state
whether this feature's domain complexity justifies BLoC's explicit event/state modeling over a
simpler Riverpod/Provider CRUD-style provider, or vice versa, in one line (full reasoning in
Section 6.1). [DESIGN DECISION]: [BLoC | Riverpod | Provider] because [reason].

### 1.3 Architecture Layer
```
lib/features/{feature}/
├── domain/
│   ├── entities/{feature}.dart            # plain Dart class, no Flutter/dio imports
│   └── repositories/{feature}_repository.dart  # abstract interface
├── data/
│   ├── datasources/{feature}_remote_datasource.dart  # dio/http
│   ├── datasources/{feature}_local_datasource.dart    # drift/hive, if caching is needed
│   └── repositories/{feature}_repository_impl.dart
└── presentation/
    ├── bloc/{feature}_bloc.dart            # or providers/{feature}_provider.dart
    ├── bloc/{feature}_event.dart
    ├── bloc/{feature}_state.dart
    ├── pages/{feature}_page.dart
    └── widgets/{feature}_*.dart
```

**Dependencies**: [M-01 Auth feature for token, etc.]

---

## 2. Architecture Context

[**[TOOL ACTION]** Glob `lib/features/*/domain/` and read existing entities/repository interfaces
before duplicating one. State: is this a new feature folder, or does it extend an existing one?
What's reused (shared `ApiClient`, entity, local-cache wrapper) vs. newly introduced here?]

---

## 3. Backend API Contract

> **[NEEDS BACKEND SDS]** if the backend feature this screen depends on has no SDS yet — never
> invent an endpoint's request/response shape. Glob the backend's `docs/04-sds/` first.

| Method | Path | Auth | Request | Response | Used By |
|--------|------|------|---------|----------|---------|
| GET | /api/v1/[resource] | Bearer | — | `{data: [...], pagination}` | List load |
| POST | /api/v1/[resource] | Bearer | `{field}` | `{data: {...}}` | Create action |

**Error shapes this feature must handle**: [400 validation, 401 expired token, 403 forbidden, 404,
409 conflict, 5xx] — map each to a UI state in Section 6.

---

## 4. Domain Layer Design

### 4.1 Entity

```dart
// lib/features/{feature}/domain/entities/{feature}.dart — no Flutter, dio, or http imports
class {Feature} {
  final String id;
  final String field;
  final DateTime createdAt;
  const {Feature}({required this.id, required this.field, required this.createdAt});
}
```

**Confirmed**: no `package:flutter/*`, `package:dio/*`, or `package:http/*` import — testable and
reusable outside of a widget tree.

### 4.2 Repository Interface

```dart
// lib/features/{feature}/domain/repositories/{feature}_repository.dart
abstract class {Feature}Repository {
  Future<{Feature}> get{Feature}(String id);
  Future<List<{Feature}>> list{Feature}s({int page, int pageSize});
  Future<{Feature}> create{Feature}(Create{Feature}Input input);
}

class Create{Feature}Input {
  final String field;
  const Create{Feature}Input({required this.field});
}
```

**Why an interface here**: presentation depends on this abstraction, not on
`{Feature}RepositoryImpl` — a fake in-memory implementation is what Section 14's BLoC/provider
unit tests and widget tests use, with no `dio`/`drift` involved.

---

## 5. Data Layer Design

### 5.1 Repository Implementation

```dart
// lib/features/{feature}/data/repositories/{feature}_repository_impl.dart
class {Feature}RepositoryImpl implements {Feature}Repository {
  final {Feature}RemoteDataSource remote;
  final {Feature}LocalDataSource? local; // only if this feature caches locally
  {Feature}RepositoryImpl({required this.remote, this.local});

  @override
  Future<{Feature}> get{Feature}(String id) async {
    // decides caching/refresh policy — BLoC/provider never calls remote/local directly
    final cached = await local?.get{Feature}(id);
    if (cached != null && !cached.isStale) return cached.toEntity();
    final fresh = await remote.get{Feature}(id); // dio/http call lives only here
    await local?.save{Feature}(fresh);
    return fresh.toEntity();
  }
}
```

**Caching policy**: [network-only | cache-then-network | `drift`/`hive` as local source of truth
with background sync] — state which, and the staleness/refresh trigger.

### 5.2 Remote / Local Data Sources

`{Feature}RemoteDataSource` wraps `dio`/`http` calls to the endpoints in Section 3 and maps JSON
to a `{Feature}Dto`; it is the *only* place this feature calls the network. `{Feature}LocalDataSource`
(only if this feature persists locally) wraps `drift`/`hive` reads/writes:

| Table/Box | Fields | Notes |
|-----------|--------|-------|
| `{feature}_table` (drift) or `{feature}Box` (hive) | `id, field, syncedAt` | [N/A if no local persistence] |

State "N/A — network-only, no local persistence" if this feature has no `drift`/`hive` source.

---

## 6. State Management Design

### 6.1 BLoC vs. Riverpod/Provider — per-feature choice

[DESIGN DECISION]: this feature uses **[BLoC | Riverpod | Provider]** because [one-line
domain-complexity reason — e.g. "multiple interdependent async triggers and explicit event
history matter for debugging → BLoC" vs. "simple CRUD screen, one async read + one write → a
Riverpod provider is sufficient ceremony"]. This is a per-feature judgment call, not a
single app-wide mandate — a different feature in the same app may choose differently.

### 6.2a If BLoC: Events and States

```dart
// {feature}_event.dart / {feature}_state.dart
sealed class {Feature}Event {}
class {Feature}Requested extends {Feature}Event {
  final String id;
  {Feature}Requested(this.id);
}

sealed class {Feature}State {}
class {Feature}Loading extends {Feature}State {}
class {Feature}Empty extends {Feature}State {}
class {Feature}Success extends {Feature}State {
  final {Feature} data;
  {Feature}Success(this.data);
}
class {Feature}Error extends {Feature}State {
  final String message;
  final bool retryable;
  {Feature}Error(this.message, {required this.retryable});
}

// {feature}_bloc.dart
class {Feature}Bloc extends Bloc<{Feature}Event, {Feature}State> {
  final {Feature}Repository repository; // interface, never RepositoryImpl directly
  {Feature}Bloc(this.repository) : super({Feature}Loading()) {
    on<{Feature}Requested>((event, emit) async {
      emit({Feature}Loading());
      try {
        emit({Feature}Success(await repository.get{Feature}(event.id)));
      } catch (e) {
        emit({Feature}Error(e.toString(), retryable: true));
      }
    });
  }
}
```

### 6.2b If Riverpod: Provider

```dart
// {feature}_provider.dart
final {feature}RepositoryProvider = Provider<{Feature}Repository>(
  (ref) => {Feature}RepositoryImpl(remote: ..., local: ...),
);

final {feature}Provider = FutureProvider.family<{Feature}, String>((ref, id) =>
    ref.watch({feature}RepositoryProvider).get{Feature}(id)); // AsyncValue gives loading/error/data for free
```

**Every screen state named explicitly** — loading / empty (no data, not an error) / error
(retryable vs. not) / success — with what triggers each transition, regardless of which library.

**Required**: no `dio`/`http`/`drift`/`hive` call anywhere in the BLoC/provider — it depends on
`{Feature}Repository` (the interface), never on `{Feature}RepositoryImpl` or a data source
directly. State flows down to the widget tree (`BlocBuilder`/`ref.watch`), events/actions flow up
(widget → `bloc.add(...)` / a provider method) — no widget mutating state directly.

---

## 7. Widget Tree Design

### 7.1 Page / Screen

```dart
// lib/features/{feature}/presentation/pages/{feature}_page.dart
class {Feature}Page extends StatelessWidget {
  const {Feature}Page({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context) => BlocBuilder<{Feature}Bloc, {Feature}State>(
    builder: (context, state) => switch (state) {
      {Feature}Loading() => const LoadingIndicator(),
      {Feature}Empty() => const EmptyStateView(),
      {Feature}Error(message: final m, retryable: final r) => ErrorStateView(
          message: m, onRetry: r ? () => context.read<{Feature}Bloc>().add({Feature}Requested(id)) : null),
      {Feature}Success(data: final d) => {Feature}Content(data: d),
    },
  );
}
```

**Required**: business/validation logic never lives inside `build()` — it only maps a state to
widgets and forwards taps to `bloc.add(...)`/a provider method. Any conditional business rule (not
"which widget to show for this UI state") belongs in the BLoC, provider, or repository layer.

### 7.2 `setState` scope

`StatefulWidget`'s local `setState` is reserved for state that is genuinely local to that one
widget (e.g. a text field's obscure-password toggle, a expand/collapse animation flag) — never for
state shared across screens or that another widget needs to read; that state is lifted into the
BLoC/provider layer from Section 6.

---

## 8. Navigation / Routing

| From | To | Trigger | Params |
|------|----|---------|--------|
| [PageA] | [PageB] | [button tap] | `{featureId}` |

**Router**: [`go_router` | `Navigator 2.0` | named routes — discover from `pubspec.yaml`/existing
`lib/router/` or `lib/app_router.dart`]. State whether this feature's routes are declared there or
introduce a new route file, and whether any route requires auth guarding (redirect to login if the
token is missing/expired).

---

## 9. Accessibility Design

- **Screen reader labels**: every interactive widget wrapped in (or already carrying) a
  `Semantics` widget/`semanticLabel` — icon-only buttons and images need an explicit label;
  purely decorative images use `excludeSemantics: true`.
- **Minimum tap target size**: interactive widgets are at least 48x48 logical pixels (Material
  guidance) — verify any custom `GestureDetector`-wrapped icon meets this, not just default
  `IconButton`/`ElevatedButton` sizing.
- **Dynamic text/contrast**: verified against the app's minimum supported text-scale factor and
  contrast requirement if the SRS states one — otherwise mark `[A11Y TARGET NOT STATED]`.

---

## 10. Client Security Design

> Full checklist: `.claude/skills/design/references/security-checklist.md` — the client-relevant
> subset only. Server-side items (SQL injection, rate limiting) are N/A here; they belong to the
> backend feature's own SDS.

- **Token storage**: `flutter_secure_storage` (Keychain-backed on iOS, Keystore-backed on
  Android) — never plain `shared_preferences` for an access/refresh token or any other secret.
- **Certificate pinning**: [applied via `dio`'s `HttpClientAdapter`/`http_certificate_pinning` |
  N/A — reason] for this feature's API calls, if the SRS/compliance posture requires it.
- **Deep link validation**: if this feature is reachable via a deep link/universal link, its
  parameters are validated before acting on them — a deep link is untrusted external input.
- **Sensitive data on screen**: [field] is masked or excluded from screenshots/app-switcher
  preview if it's a balance/PII field the SRS flags as sensitive.

---

## 11. Client Performance Design

> Full checklist: `.claude/skills/design/references/performance-checklist.md` — the client-relevant
> subset. Server load/RPS is N/A; this is about render/rebuild cost on-device.

- **Rebuild scope**: `const` constructors used on every widget subtree that doesn't depend on
  changing state; any widget that must react to BLoC/provider state is scoped as narrowly as
  possible (`BlocBuilder`/`Consumer` wraps only the widget that needs to rebuild, not the whole
  page) — name any widget where this scoping was a deliberate design choice.
- **List performance**: `ListView.builder`/`GridView.builder` (lazy) for any list that can grow
  past a screen's worth of rows — never a `Column` of items built eagerly from a full list.
- **Image caching**: `Image.network`'s built-in cache or `cached_network_image` with a stated
  placeholder/error image — no unbounded full-resolution image load for a thumbnail-sized widget.

---

## 12. Data Integrity

N/A — this feature has no local source-of-truth needing sync-conflict handling, unless Section 5.3
states `drift`/`hive` as an offline-first cache with background sync. If it does: state the
conflict-resolution rule (last-write-wins / server-wins / merge) here.

---

## 13. Operations Readiness

N/A — not a deployed service. Note crash-reporting/Sentry wiring here only if the SRS explicitly
calls for it.

---

## 14. Test Plan

### 14.1 BLoC / Provider Unit Tests (fake Repository)

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `loading then success` | Repository returns data | State transitions Loading → Success |
| `loading then error` | Repository throws | State transitions Loading → Error(retryable) |
| `retry triggers reload` | Retry event/action after error | Repository call re-invoked |

### 14.2 Widget Tests (per UI state)

| Test Case | Expected |
|-----------|----------|
| Loading state renders indicator | `LoadingIndicator` found in widget tree |
| Empty state renders empty view | `EmptyStateView` found, no crash |
| Error state renders retry action | Retry button visible and wired to the retry event |
| Success state renders content | `{Feature}Content` receives and displays `data` |

### 14.3 SRS Traceability

| SRS Requirement | Implemented In |
|-----------------|-----------------|
| FR-01: [requirement] | Bloc/Provider: [name], Page: [{Feature}Page] |
| FR-02: [requirement] | Repository: [method] |

---

## 15. Design Decisions & Alternatives

Per `.claude/skills/design/references/decision-records.md` §2 — record any costly-to-reverse
choice (e.g. BLoC vs. Riverpod for this feature, `drift` vs. `hive` for local cache, network-only
vs. offline-first) with alternatives considered and why this one won.

## 16. Risks & Trade-offs

[State risks — e.g. "no offline support; feature unusable without connectivity" — and whether
that's accepted or deferred.]

## 17. Implementation Mapping

| SDS Section | Implementation File |
|--------------|---------------------|
| §6 State management | `presentation/bloc/{feature}_bloc.dart` or `presentation/providers/{feature}_provider.dart` |
| §5 Repository impl | `data/repositories/{feature}_repository_impl.dart` |
| §4 Domain | `domain/entities/{feature}.dart`, `domain/repositories/{feature}_repository.dart` |

## 18. Implementation Readiness

**Status**: [READY | PARTIALLY_READY | BLOCKED]
[State any `[NEEDS BACKEND SDS]`/`[NEEDS SPEC CLARIFICATION]`/`[A11Y TARGET NOT STATED]` items and
what `/implement` can start on now vs. what's blocked.]
```

---

## NAMING CONVENTIONS (MODE L)

- SDS path: `docs/04-sds/M-XX-module-name.md`
- Feature folder: `lib/features/{feature}/` (lowercase, snake_case)
- Entity: `{feature}.dart`, PascalCase class name
- Repository interface: `{feature}_repository.dart`; implementation: `{feature}_repository_impl.dart`
- Remote/local data sources: `{feature}_remote_datasource.dart` / `{feature}_local_datasource.dart`
- BLoC: `{feature}_bloc.dart` + `{feature}_event.dart` + `{feature}_state.dart`
- Riverpod provider: `{feature}_provider.dart`
- Page: `{feature}_page.dart`; reusable sub-widgets: `{feature}_*.dart` under `presentation/widgets/`

## LAYER RULES (MODE L)

| Layer | Can import | Cannot import |
|-------|-----------|-----------------|
| Domain (`entities/`, `repositories/` interfaces) | Dart stdlib only | `package:flutter/*`, `package:dio/*`, `package:http/*`, `drift`, `hive` |
| Data (`datasources/`, `repositories/` impl) | Domain layer, `dio`/`http`, `drift`/`hive` | Presentation layer, `package:flutter/*` |
| Presentation — state management (BLoC/provider) | Domain layer (repository interface) | Data layer's concrete implementation, `package:flutter/material.dart` widget types beyond what the library itself requires |
| Presentation — widgets | State-management layer, domain entities (for typing) | Data layer directly (`dio`, `drift`, `hive`), no `dio`/`http` call from a widget |

**Entity Design:**
- Plain Dart classes/records, no Flutter or persistence-library annotations
- Immutable (`final` fields, `const` constructor) — a `copyWith` if the entity needs partial updates
- No widget-building or navigation methods on a domain entity

**SDS Traceability Comment (required):**
```dart
// Traceability: SDS M-XX Section Y.Z [Bloc/Provider/UseCase Name]
Future<void> _onFeatureRequested(...) async { ... }
```

**SDS Design Principle:**
Design from the domain (entity + repository interface) outward → don't design the widget tree
first and only think about where the data comes from afterward.
