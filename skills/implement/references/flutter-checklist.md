# Implement Skill — Flutter (Dart) Reference Material

> Load this when implementing in a Flutter codebase. It complements
> `verification-checklist.md` — that file's language-agnostic checklist (linting, testing,
> secrets scan, docs) still applies; this file adds the traps specific to this stack.
>
> **First, identify the state-management library.** Check `pubspec.yaml` for
> `flutter_bloc`/`bloc` vs. `flutter_riverpod`/`riverpod` vs. plain `provider`. The SDS (§5) should
> already name the choice per feature — don't assume one from memory or from a different Flutter
> project you've seen before, and don't "helpfully" convert a Riverpod feature to BLoC (or vice
> versa) mid-implementation.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### 1. Problem: local `setState` used for state that's actually shared across screens

```dart
// order_list_screen.dart
class _OrderListScreenState extends State<OrderListScreen> {
  List<Order> _orders = [];   // fetched here, mutated here

  Future<void> _refresh() async {
    final orders = await orderRepository.fetchAll();
    setState(() => _orders = orders);
    // when the user navigates to OrderDetailScreen and cancels an order there,
    // this list has no way to learn about it — it goes stale until a manual pull-to-refresh
  }
}
```

**Why**: `StatefulWidget`'s local `setState` only notifies that one widget's subtree. Once a
piece of state needs to be read or mutated from more than one screen/widget — or needs to survive
a widget being rebuilt/disposed and recreated — `setState` silently becomes the wrong tool: there
is no cross-widget invalidation, no single source of truth, and no way for a sibling screen to
react to a change.

**Fix**: lift the state into the BLoC/provider the SDS named for this feature. `setState` stays
valid only for state genuinely local and disposable with the widget (a text field's focus, an
animation controller's value, whether a dropdown is expanded).

```dart
class OrderListScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return BlocBuilder<OrderBloc, OrderState>(
      builder: (context, state) => switch (state) {
        OrderLoaded(orders: final orders) => OrderListView(orders: orders),
        // cancelling in OrderDetailScreen dispatches an event the same OrderBloc
        // instance handles, so every listening screen rebuilds with the new state
        _ => const OrderListLoading(),
      },
    );
  }
}
```

---

### 2. Problem: a widget calling `dio`/`http` directly instead of through a repository

```dart
class OrderListScreen extends StatelessWidget {
  Future<void> _load() async {
    final response = await Dio().get('https://api.example.com/orders'); // networking
    final orders = (response.data as List)                              // + parsing
        .map((j) => Order.fromJson(j)).toList();                        // + mapping,
    // all inside a widget — untestable without a real network call, and if two widgets
    // both need "orders", this logic gets copy-pasted instead of shared
  }
}
```

**Why**: this is the same "business logic in the transport/UI layer" trap the design skill
flags at design time (`design/SKILL.md` MODE L Prohibited list) — a widget that talks to `Dio`
directly can't be unit-tested without a real or heavily-mocked HTTP client, can't share caching
or error-mapping logic with any other screen, and breaks the domain→data→state→widget layering
the SDS specified.

**Fix**: the widget only reads BLoC/provider state and dispatches events/calls methods; the
repository (behind the domain interface) owns the `Dio`/`http` call and maps errors to a typed
failure.

```dart
class OrderListScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    context.read<OrderBloc>().add(OrderRequested()); // widget only dispatches
    return BlocBuilder<OrderBloc, OrderState>(...);   // and renders
  }
}
// OrderBloc -> OrderRepository (interface) -> OrderRepositoryImpl -> Dio
```

---

### 3. Problem: domain/use-case code importing Flutter widget types

```dart
// domain/repositories/order_repository.dart
import 'package:flutter/material.dart'; // <- domain layer importing Flutter

abstract class OrderRepository {
  Future<List<Order>> fetchAll();
  Widget buildErrorDialog(BuildContext context); // domain method returning a Widget
}
```

**Why**: the domain layer's entire value is being independent of Flutter/dio/drift so it can be
unit-tested with zero widget/plugin bindings and reused if the UI framework ever changes. One
`Widget`/`BuildContext` import anywhere under `domain/` collapses that boundary — every consumer
of the domain layer now transitively depends on Flutter, and a domain unit test needs
`flutter_test`/widget bindings instead of plain `dart test`.

**Fix**: keep `domain/` to pure Dart (entities, repository interfaces, failures, use cases). Any
UI concern (dialogs, snackbars, widget-specific formatting) lives in `presentation/`.

```dart
// domain/repositories/order_repository.dart — no Flutter import
abstract class OrderRepository {
  Future<List<Order>> fetchAll();
}
// presentation/widgets/order_error_view.dart owns the error Widget
```

---

### 4. Problem: unnecessary widget rebuilds from missing `const` or misplaced state

```dart
class OrderScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return BlocBuilder<OrderBloc, OrderState>(
      builder: (context, state) {
        return Column(                    // whole subtree rebuilds on every OrderState change
          children: [
            OrderHeader(),                 // no `const` — rebuilt every time even though
            Divider(),                     // it never reads `state`
            Expanded(child: OrderList(orders: state.orders)),
          ],
        );
      },
    );
  }
}
```

**Why**: `BlocBuilder`/`Consumer` rebuilds its entire `builder` closure on every emitted
state/notified value. A widget subtree placed inside that closure without a `const` constructor
(or without being extracted so it sits outside the builder) rebuilds every time too, even when
none of its own inputs changed — on a screen with frequent state emissions (e.g. a live-updating
list) this shows up as visible jank.

**Fix**: give every widget that has no runtime-varying constructor arguments a `const`
constructor, and scope the `BlocBuilder`/`Consumer` to the narrowest subtree that actually needs
the new state (SDS §9 "Widget rebuild scope").

```dart
class OrderScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const OrderHeader(),   // const — never rebuilt by BlocBuilder below
        const Divider(),
        Expanded(
          child: BlocBuilder<OrderBloc, OrderState>(
            builder: (context, state) => OrderList(orders: state.orders),
          ),
        ),
      ],
    );
  }
}
```

---

### 5. Problem: platform-channel calls with no error handling for native-side failures

```dart
Future<String> getDeviceId() async {
  final result = await platform.invokeMethod('getDeviceId'); // no try/catch
  return result as String;                                    // crashes the Dart isolate
}                                                               // if native throws or returns null
```

**Why**: `MethodChannel.invokeMethod` throws a `PlatformException` (native-side error) or a
`MissingPluginException` (channel/method not registered on this platform, e.g. called on a
platform the plugin doesn't support) — both are normal, expected failure modes for a call that
crosses into native code, not programmer errors. An uncaught throw here surfaces as an
unhandled exception at the call site, and if nothing above the call catches it, the app crashes.

**Fix**: wrap every `invokeMethod` call and map both exception types to a typed failure the
caller can render or retry.

```dart
Future<String?> getDeviceId() async {
  try {
    final result = await platform.invokeMethod<String>('getDeviceId');
    return result;
  } on PlatformException catch (e) {
    // native side reported a specific failure (permission denied, hardware unavailable, etc.)
    log('getDeviceId failed: ${e.code} ${e.message}');
    return null;
  } on MissingPluginException {
    // channel not implemented on this platform (e.g. web, or a platform the plugin skips)
    return null;
  }
}
```

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — Flutter specifics slot in as follows:

### **P0 - Critical**
- No `domain/` file imports `flutter`, `dio`, `http`, `drift`, or `hive`
- No widget calls `Dio`/`http` directly — every network call goes through the repository the SDS
  named
- Every `MethodChannel.invokeMethod` call is wrapped for `PlatformException`/`MissingPluginException`
- Every `@Published`-equivalent state mutation (BLoC `emit`, Riverpod state assignment) matches
  the state shape the SDS §5 designed — no ad-hoc state added mid-implementation

### **P1 - High**
- No cross-screen/shared state implemented with a `StatefulWidget`'s local `setState` — lifted
  into the BLoC/provider instead
- `const` constructor present on every widget whose constructor arguments don't vary at runtime
- `BlocBuilder`/`Consumer`/`Selector` scoped to the narrowest subtree needing the new state, not
  wrapping an entire screen when only one child actually reads it

### **P2 - Medium**
- `bloc_test` (BLoC) or `ProviderContainer` overrides (Riverpod) used for state-management unit
  tests, with a fake/mock repository — no real `Dio`/drift/hive in a unit test
- Widget tests (`flutter_test`) cover every screen state the SDS §6 specified (loading, empty,
  error, success) — not just the happy path

### **P3 - Low**
- List virtualization (`ListView.builder`/`SliverList`) confirmed for any list that can grow
  beyond a screenful
- Image loading uses a cached/async loader with a placeholder, not a synchronous decode

---

## VERIFICATION CHECKLIST (Flutter additions)

Run these in addition to the general checklist:

### 1. Code Quality
```bash
flutter analyze
dart format --set-exit-if-changed lib/ test/
```
- [ ] No `domain/**` file imports `package:flutter/*`, `package:dio/*`, `package:drift/*`, or
  `package:hive/*` — `grep -rl "^import 'package:flutter" lib/**/domain/` should return nothing

### 2. Correctness
- [ ] Every screen's `build()` method contains no `await`ed network/DB call and no business rule
  — only state-to-widget mapping and event dispatch
- [ ] State-management layer (BLoC/provider) is the only place that calls the repository —
  `grep -rn "Repository()\." lib/**/presentation/` (constructing/calling a repository straight
  from presentation, bypassing DI) should return nothing unexpected
- [ ] Every entity with a status/lifecycle field is only mutated through a defined transition
  (event handler / provider method), not a direct field assignment scattered across the codebase

### 3. Security
- [ ] Auth/session token stored via `flutter_secure_storage`, never `shared_preferences`/a plain
  file — `git grep -n "shared_preferences" -- '*.dart'` then check none of the hits store a token
- [ ] Every deep-link/platform-channel payload is validated before being used to navigate to a
  privileged screen or passed to native code — not trusted as-is
- [ ] No secret/API key hardcoded in source: `git grep -iE "(password|secret|api_key|token)\s*=\s*['\"]" -- '*.dart'`
- [ ] Certificate pinning present for high-value calls (payments) if the SDS specified it

```bash
git grep -n "shared_preferences" -- '*.dart'
git grep -iE "(password|secret|api_key|token)\s*=\s*['\"]" -- '*.dart'
```

### 4. Testing
```bash
flutter test
flutter test integration_test/   # if configured
```
- [ ] BLoC tests use `bloc_test` with a mocked repository; Riverpod tests use `ProviderContainer`
  with `overrideWith` on the repository provider — neither hits a real `Dio`/drift/hive instance
- [ ] A widget test exists for each screen state the SDS designed (loading/empty/error/success),
  not only the success path
- [ ] Platform-channel-dependent code has a test (or a documented manual QA step) covering the
  `PlatformException`/`MissingPluginException` path, since these can't run in a plain unit test
  without mocking the channel

### 5. Performance
- [ ] Every widget with no runtime-varying constructor args is `const`
- [ ] `BlocBuilder`/`Consumer`/`Selector` wraps the narrowest subtree needed, verified by reading
  the widget tree around each one — not assumed from the builder's placement
- [ ] Any list that can exceed a screenful uses `ListView.builder`/`SliverList`, not a `Column`
  or plain `ListView` with a fully materialized children list
- [ ] Image widgets use an async/cached loader with a placeholder, not `Image.memory`/
  `Image.file` decoding synchronously on the UI thread for a large asset

```bash
grep -rn "class .*extends StatelessWidget\|class .*extends State<" lib/ | wc -l
grep -rLn "const " lib/**/widgets/*.dart   # widgets with zero const usage — candidates to check
```

### 6. Platform Channels (if this feature calls native code)
- [ ] Every `invokeMethod` call is wrapped in `try`/`catch` for both `PlatformException` and
  `MissingPluginException`
- [ ] A method missing on one platform (e.g. web) degrades to a stated fallback, not an uncaught
  crash — confirmed by checking the platform this feature actually ships to per the SRS

```bash
grep -rn "invokeMethod" lib/ | wc -l
grep -B2 "invokeMethod" lib/**/*.dart | grep -c "try"
```

---

## TROUBLESHOOTING

**A list screen redraws its entire content on every state emission, visible as jank on scroll:**
Check whether `BlocBuilder`/`Consumer` wraps the whole screen instead of just the list, and
whether sibling widgets (header, footer) are missing `const`. Move the builder down to wrap only
the list, and add `const` to everything above/below it that doesn't read state.

**A value updated on one screen doesn't show up on another screen showing the same data:**
Look for a `StatefulWidget` holding that value in local `setState` instead of the shared
BLoC/provider — each screen's `State` object has its own copy, so neither can see the other's
update. Lift the value into the BLoC/provider the SDS named.

**`flutter test` passes but the app crashes in the field when calling a native feature:**
The test suite almost certainly doesn't exercise the real platform channel. Check the
`invokeMethod` call site for a missing `try`/`catch` around `PlatformException`/
`MissingPluginException`, and add a mocked-channel test that forces that path.

**A domain/use-case unit test needs `flutter_test`/widget bindings to even compile:**
Something under `domain/` imports `package:flutter/...` (often `foundation.dart` for
`@immutable` or `ValueGetter`) or a `dio`/`drift` type. Move that import's need into `data/` or
drop it — the domain layer should compile and test under plain `dart test`.

**Two developers implement the same feature with different state-management libraries:**
The SDS §5.1 should have already named BLoC or Riverpod for this feature with a reason — check
it before writing state-management code, and don't default to whichever library you personally
prefer if the SDS named the other one.
