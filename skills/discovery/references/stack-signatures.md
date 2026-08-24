# Stack Signatures

Per-stack detail for the SCAN step: what confirms the stack beyond the manifest signal, where
the entry point lives, how the codebase is usually laid out, and what to actually open and read
before asserting behavior. This is orientation, not an exhaustive style guide — read just enough
to route correctly and avoid contradicting an existing convention.

---

## Angular (frontend)

- **Signal:** `angular.json` at root.
- **Version matters:** check `@angular/core` in `package.json` — v14+ commonly uses **standalone
  components** (`bootstrapApplication()`, no `AppModule`); older versions use **NgModules**
  (`app.module.ts`, `declarations`/`imports` arrays). Don't assume one pattern without checking.
- **Entry point:** `src/main.ts` → `src/app/app.config.ts` (standalone) or `src/app/app.module.ts`
  (NgModule-based).
- **Structure:** feature folders under `src/app/`, each typically pairing `*.component.ts` +
  `.html` + `.scss` + (optionally) `.spec.ts`; shared logic in `*.service.ts` (injected via
  constructor DI or the newer `inject()` function); routes in `app-routing.module.ts` or a
  standalone `app.routes.ts`.
- **State management:** check `package.json` for `@ngrx/store` (NgRx, Redux-style) vs. plain
  RxJS `BehaviorSubject`s in services vs. Angular Signals (`signal()`, v16+).
- **Read first:** the routing file (maps the app's surface area) and the service tied to the
  feature in question (usually where the actual business logic and HTTP calls live — components
  are mostly presentation).

## React (frontend, non-Next.js)

- **Signal:** `package.json` has `react` + `react-dom`, no `next` dependency, no `angular.json`.
- **Bundler/tooling:** `vite.config.ts`/`.js` (Vite), `react-scripts` in `package.json` scripts
  (Create React App, likely legacy), or a custom Webpack config — affects where env vars and
  path aliases are configured.
- **Entry point:** `src/main.tsx` (Vite) or `src/index.tsx` (CRA) → `src/App.tsx`.
- **Structure:** `src/components/` (presentational), often `src/pages/` or `src/views/` (routed
  screens), `src/hooks/` (custom hooks). Routing via `react-router-dom` — check `package.json`
  and look for `<Routes>`/`<Route>` or a router config object.
- **State management:** check `package.json` imports for Redux Toolkit, Zustand, Jotai, Recoil,
  or plain Context API (`createContext`/`useContext` in `src/context/`).
- **Data fetching:** look for `@tanstack/react-query` / SWR (cache-aware fetching) vs. raw
  `fetch`/`axios` in `useEffect` — changes where "loading/error state" logic actually lives.
- **Read first:** the router config (maps the app's surface area) and the component/hook nearest
  the feature in question.

## Next.js (frontend/full-stack)

- **Signal:** `package.json` has `next` as a dependency.
- **Router:** App Router (`app/` directory, `layout.tsx` + `page.tsx`, Server Components by
  default) vs. legacy Pages Router (`pages/` directory, `getServerSideProps`/`getStaticProps`) —
  a codebase mid-migration can have both; check which directory the feature actually lives in
  before assuming a convention.
- **Entry point:** App Router → `app/layout.tsx` + `app/page.tsx`; Pages Router → `pages/_app.tsx`.
- **Server vs. client:** Server Components can read the DB/backend directly and never ship JS to
  the browser; Client Components need an explicit `'use client'` directive at the top of the
  file — check for it before assuming a component can use hooks or browser APIs. Server Actions
  (`'use server'`) often replace API routes for mutations.
- **Data layer:** check `package.json` for `prisma` (schema at `prisma/schema.prisma`, client via
  `@prisma/client`) or `drizzle-orm` — this is where DB models/queries actually live (see
  `design`'s MODE C).
- **Read first:** the route segment's `page.tsx`/`layout.tsx` for the feature, then any
  co-located `actions.ts`/`route.ts`, then the Prisma schema if data is involved.

## Flutter (mobile, cross-platform)

- **Signal:** `pubspec.yaml` with a `flutter:` section.
- **Entry point:** `lib/main.dart` — look for the root `runApp(...)` widget and whatever wraps it
  (a `ProviderScope`, `MultiBlocProvider`, etc. reveals the state-management choice immediately).
- **Structure:** `lib/` typically split into `screens/` or `pages/` (full-screen widgets),
  `widgets/` (reusable UI), `models/` (data classes, often with `.g.dart` codegen from
  `json_serializable`), `services/` or `repositories/` (API/DB access).
- **State management:** check `pubspec.yaml` dependencies for `provider`, `flutter_riverpod`,
  `flutter_bloc`/`bloc`, or `get` (GetX) — each implies a different file-organization convention
  around the feature.
- **Platform folders:** `android/` and `ios/` exist even for a "Flutter-only" mental model —
  platform-specific config (permissions, signing) lives there, not in `lib/`.
- **Read first:** `lib/main.dart` for the app shell/DI setup, then the screen widget for the
  feature in question.

## Android (mobile, native)

- **Signal:** root `build.gradle`/`build.gradle.kts` + an `app/` module with
  `app/src/main/AndroidManifest.xml`.
- **Language:** check majority file extension under `app/src/main/java|kotlin/` — `.kt` (Kotlin,
  the modern default) vs. `.java` (older or legacy codebases). Mixed is common during migration.
- **UI toolkit:** Jetpack Compose (`@Composable` functions, no XML layouts for those screens) vs.
  the classic View system (`app/src/main/res/layout/*.xml` + `findViewById`/View Binding). Check
  `build.gradle` for `androidx.compose` dependencies to tell which one a given screen uses.
- **Entry point:** `AndroidManifest.xml` declares every `Activity`/`Service`/`BroadcastReceiver`
  and the launcher activity (`<intent-filter>` with `MAIN`/`LAUNCHER`) — start there to find the
  app's actual entry screen, not by guessing from filenames.
- **Architecture:** look for `ViewModel`/`Repository`/`UseCase` classes (MVVM/Clean Architecture,
  common in modern Android) vs. logic embedded directly in `Activity`/`Fragment` (older style).
- **DI:** check for Hilt/Dagger annotations (`@Inject`, `@Module`) or Koin — changes where a
  dependency is actually constructed.
- **Read first:** `AndroidManifest.xml`, then the `ViewModel`/`Activity` for the feature's screen.

## iOS (mobile, native)

- **Signal:** `*.xcodeproj`/`*.xcworkspace` at root, plus `Podfile` (CocoaPods) or a
  `Package.swift` (Swift Package Manager) for dependencies.
- **UI framework:** SwiftUI (`struct SomeView: View`, declarative, `@State`/`@Binding`/
  `@ObservedObject`) vs. UIKit (`.storyboard`/`.xib` files, `UIViewController` subclasses,
  imperative). Many apps mix both via `UIHostingController`.
- **Entry point:** SwiftUI apps use `@main struct AppName: App { ... }` (look for a `*App.swift`
  file); UIKit apps use `AppDelegate.swift`/`SceneDelegate.swift`.
- **Dependency manager:** `Podfile.lock` (CocoaPods), `Package.resolved` (SwiftPM), or
  `Cartfile.resolved` (Carthage, less common now) — tells you where third-party code and version
  pins actually live.
- **Structure:** no single enforced convention — look for `Views/`, `ViewModels/`, `Models/`,
  `Services/` folders (MVVM is the common pattern) grouped either by layer or by feature module.
- **Read first:** the app entry file, then the `View`/`ViewController` for the feature in
  question and its paired `ViewModel` if one exists.

## NestJS backend

- **Signal:** `package.json` has `@nestjs/core`, or a `nest-cli.json` at root.
- **Entry point:** `src/main.ts` (bootstraps `NestFactory.create(AppModule)`) →
  `src/app.module.ts` (root module wiring — shows every feature module the app actually loads).
- **Structure:** feature modules under `src/<feature>/`, typically pairing `*.module.ts` +
  `*.controller.ts` + `*.service.ts` + `*.dto.ts`, wired through Nest's dependency injection
  (`@Injectable()`, constructor injection) rather than manual instantiation.
- **ORM:** check `package.json` for `@nestjs/typeorm`/`typeorm` vs. `@prisma/client` — determines
  whether entities are `@Entity()` classes or a `prisma/schema.prisma` file drives the models.
- **Read first:** the feature's `*.module.ts` (shows what's wired together), then its
  `*.controller.ts`, then the `*.service.ts` it delegates to.

## Python backend — FastAPI

- **Signal:** `pyproject.toml`/`requirements.txt` lists `fastapi` (usually with `uvicorn`).
- **Entry point:** search for `FastAPI()` instantiation — commonly `main.py`, `app/main.py`, or
  `src/<package>/main.py`. That file usually also wires middleware and includes routers.
- **Structure:** routers/endpoints under `app/api/` or `app/routers/` (grouped by resource or
  version, e.g. `api/v1/users.py`); request/response schemas as Pydantic models in
  `app/schemas/`; DB models in `app/models/` (SQLAlchemy or SQLModel); dependency injection via
  `Depends(...)` parameters (auth, DB session, pagination are commonly injected this way).
- **Async vs. sync:** check whether route handlers are `async def` (non-blocking, expects
  async-safe DB drivers like `asyncpg`) or plain `def` (FastAPI runs these in a threadpool) — a
  blocking call inside an `async def` handler stalls the event loop, a real bug class to watch
  for once past discovery.
- **Read first:** the router file for the feature's resource, then its Pydantic schema (defines
  the actual contract) and the DB model it maps to.

## Rust backend

- **Signal:** `Cargo.toml` at root (or a workspace root) with a web framework in
  `[dependencies]` — `axum`, `actix-web`, `rocket`, or `warp`.
- **Workspace vs. single crate:** a `[workspace]` section in the root `Cargo.toml` means multiple
  crates (`members = [...]`) — identify which member crate actually owns the HTTP layer before
  assuming `src/main.rs` at root is it.
- **Entry point:** `src/main.rs` (binary crate) — look for the framework's app/router
  construction (`axum::Router::new()`, `App::new().service(...)` for actix-web, or `#[launch]`
  for Rocket).
- **Structure varies by framework convention:** handlers/routes often under `src/handlers/` or
  `src/routes/`; shared types/errors in `src/models/` or `src/error.rs`. Axum and actix-web don't
  enforce a folder layout — check for an existing pattern before adding a new one.
- **Async runtime:** check `Cargo.toml` for `tokio` (near-universal for these frameworks) vs.
  `async-std` — determines which async primitives (spawn, timers) are safe to use.
- **Error handling:** look for a custom `Error` enum implementing the framework's response-
  conversion trait (`IntoResponse` for axum, `ResponseError` for actix-web) — this is usually the
  single place that maps internal errors to HTTP status codes.
- **Read first:** the router/app-construction code in `main.rs`, then the handler for the
  feature's route.

## Go backend

- **Signal:** `go.mod` at root.
- **Framework:** check `go.mod` requires for `fiber` (`github.com/gofiber/fiber`),
  `gin-gonic/gin`, `labstack/echo`, or none (plain `net/http`) — this changes router and
  middleware conventions more than the folder layout does.
- **Entry point:** `main.go`, often under `cmd/<service>/main.go` in larger repos — look for the
  router/app construction (`fiber.New()`, `gin.Default()`, etc.).
- **Structure:** Clean Architecture is common — `internal/domain/` (entities, no framework
  imports), `internal/usecase/` or `internal/service/` (business logic), `internal/repository/`
  (MongoDB/Postgres access), `internal/handler/` or `internal/delivery/http/` (route handlers). A
  domain entity importing a DB/framework package is a violation of the existing pattern, not a
  fresh convention to extend.
- **Read first:** the handler for the feature's route, then the usecase/service it calls, then
  the repository interface it depends on (the interface, not the concrete DB implementation,
  unless storage behavior itself is in question).

## Spring Boot / JVM backend

- **Signal:** `pom.xml` (Maven) or `build.gradle`/`build.gradle.kts` (Gradle) with
  `spring-boot-starter*` dependencies, and no `AndroidManifest.xml`.
- **Version matters:** check the Spring Boot version (`<parent><version>` in `pom.xml`, or the
  `org.springframework.boot` plugin version in `build.gradle`) — Boot 3.x moved `javax.*` to
  `jakarta.*` across persistence, validation, and servlet APIs, and changed the Security config
  style. Assuming the wrong namespace produces dead-on-arrival code.
- **Entry point:** the `@SpringBootApplication`-annotated class, usually
  `src/main/java/.../Application.java`.
- **Structure:** layered — `controller/` (`@RestController`), `service/` (`@Service`, business
  logic), `repository/` (`@Repository`, often Spring Data JPA interfaces), `entity/` or `domain/`
  (`@Entity` JPA classes), `dto/` (request/response objects — should stay distinct from entities,
  never serialized directly).
- **Read first:** the controller for the feature's endpoint, then the service it delegates to,
  then the entity/DTO pair to confirm the actual response shape.

## Python data pipeline

- **Signal:** `pyproject.toml`/`requirements.txt` with no web framework (no fastapi/django/flask),
  and the project's own CLAUDE.md has a "Module Architecture" or "Data Pipeline" section — that
  CLAUDE.md is usually the real map here, more than any folder convention.
- **Entry point:** typically one orchestrator script (`main.py`, `pipeline.py`, or a
  project-specific name) that calls numbered/named modules in sequence — check CLAUDE.md or the
  orchestrator's own imports for the actual execution order; don't assume alphabetical or
  most-recently-modified order.
- **Structure:** modules are often organized by pipeline stage (ingest → transform → analyze →
  output) rather than by framework layer. Look for a shared config/enums file (thresholds,
  feature flags) that multiple modules import — that file is usually the one place calibration
  actually lives.
- **Storage:** check for a DB client (MongoDB via `pymongo`/`motor`, Postgres via
  `psycopg2`/`sqlalchemy`) to find where intermediate/final results persist — pipeline bugs are
  often visible in what's actually written to storage, not just in what the code appears to
  compute.
- **Read first:** CLAUDE.md's Module Architecture section first (it usually states the intended
  flow), then the specific module the request concerns, then its config/enums dependency if it
  has one.

## Script-based systems

- **Signal:** no framework manifest — a loose collection of `*.sh`, `*.ps1`, `*.py`, or `*.js`
  files, often at root or under `scripts/`, frequently triggered by cron, Windows Task Scheduler,
  or a CI workflow file rather than run interactively.
- **No enforced structure — find the real entry point first:** check `README`, a `Makefile`, a
  crontab entry, or `.github/workflows/*.yml` for what actually gets invoked and with what
  arguments; don't assume the largest or most-recently-modified file is the entry point.
- **Orchestration pattern:** look for one "main"/"orchestrator" script that calls the others in
  sequence (via subprocess calls, `source`/`.` includes, or shelling out) — that script is the
  actual map of the system, more than any individual script read in isolation.
- **State and side effects:** script systems often mutate shared state (files, a database, an
  external API) with few guardrails and no test suite — read a script fully, including error
  paths, before asserting what it does; a partial read of a script is more likely to be wrong
  than a partial read of a typical application module, because there's no framework enforcing
  structure to fall back on.
- **Read first:** whatever the scheduler/CI config actually invokes, then follow its calls into
  the other scripts in execution order.
