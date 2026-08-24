# EXPLORE — Full Workflow

Step-by-step detail for MODE: EXPLORE (document an existing architecture). Loaded once EXPLORE
is the confirmed mode — see `SKILL.md`'s HOW TO USE for mode detection and the condensed step
list.

---

## 1. SCAN — Discover project structure

**Purpose:** Understand the project from zero — don't assume any structure beforehand

**A. Identify project root and language:**
```
# Find project indicators at root
Glob: CLAUDE.md, README.md, README.*, CONTRIBUTING.md
Glob: package.json, go.mod, pyproject.toml, setup.py, Cargo.toml, pom.xml, build.gradle
Glob: *.sln, *.csproj (C#), requirements.txt, poetry.lock
Glob: angular.json (Angular), pubspec.yaml (Flutter), Podfile/*.xcodeproj/Package.swift (iOS),
      build.gradle.kts + AndroidManifest.xml (Android)

→ Read the most relevant file to get: project name, language, framework, overview
```

For the exact signal → stack mapping (which manifest field/dependency confirms which framework,
not just which file exists) and per-stack entry-point/structure detail, reuse `discovery`'s
`references/stack-signatures.md` rather than re-deriving it here — this step's job is broader
project inventory (docs, entry points, and stacks like C# that discovery's table doesn't cover),
not a second signal table.

**B. Discover source code roots:**
```
# Common source roots — check each one for existence
Glob: src/*/, lib/*/, app/*/, packages/*/,  cmd/*/, internal/*/
Glob: *.py, *.ts, *.go, *.java (at root to detect monorepo)

→ Determine: number of source directories, whether it's a monorepo
```

**C. Discover documentation:**
```
Glob: docs/*/, documentation/*/, .docs/*/
Glob: docs/**/*.md, wiki/**/*.md (if it exists)

→ Determine output directory: where do docs already exist? → create 02-architecture/ inside it
   If docs/ doesn't exist yet → default to creating docs/02-architecture/
```

**D. Discover production entry points:**
```
# Scripts / executables / pipeline files
Glob: scripts/*.py, scripts/*.sh, scripts/*.ts
Glob: cmd/*/main.go, bin/*, Makefile
Glob: *.pipeline.*, *pipeline*.py, main.py, app.py, server.py, index.ts

→ Find the file that calls the most internal modules (= production pipeline/entry)
```

**E. Check existing architecture docs:**
```
→ If the output directory already exists and has content → read README.md to learn the current state
```

**Deliverable:** Project inventory:
```
Project: [name from root files]
Language/Framework: [detected]
Source roots: [list]
Module count: [N modules/components]
Entry points: [list]
Output directory: [path]
Existing docs: [yes/no]
```

**MUST NOT assume:**
- Module names or count
- Specific directory structure
- Programming language
- File naming convention

---

## 2. DEEP_DIVE — Read each module/component in detail

**Purpose:** Extract public API, data models, and key logic from each module

**A. Discover modules from source roots (discovered in SCAN):**
```
# For each source root found:
Glob: {source_root}/*/          → list subdirectories = candidates for modules
Glob: {source_root}/*/*.{ext}   → list files in each subdirectory
```

**B. Find each module's entry point (adapt by language):**

| Language | Entry point candidates |
|----------|----------------------|
| Python | `orchestrator.py`, `main.py`, `service.py`, `__init__.py` (if it has exports) |
| TypeScript/JS | `index.ts`, `index.js`, `main.ts`, `app.ts` |
| Go | `*.go` in the package with `func main()` or `handler*.go` |
| Java/Kotlin | `*Application.java`, `*Controller.*`, `*Service.*` |
| Rust | `main.rs`, `lib.rs`, `mod.rs` (in each module directory) |
| General | File with the most imports from other submodules |

```
# Grep to find public functions/exports
Grep: "^def " or "^class " in .py
Grep: "^export " or "^export default" in .ts/.js
Grep: "^func " in .go
Grep: "^public " or "@RestController" in .java
Grep: "^pub fn \|^pub struct \|^pub enum \|^pub trait " in .rs
```

**C. Find data models:**
```
# Common data model patterns
Grep: "TypedDict\|dataclass\|@dataclass" in .py
Grep: "interface \|type \w+ =\|type \w+ {" in .ts
Grep: "type \w+ struct" in .go
Grep: "@Entity\|@Table\|class \w+Model\|class \w+DTO" in .java
Grep: "^pub struct \|^pub enum \|^#\[derive(" in .rs   # Rust: structs, enums with derives

→ Read files containing these definitions
```

**D. Find configuration:**
```
# Config patterns
Glob: config.py, settings.py, *_enums.py, *_config.py, constants.py
Glob: config.ts, config.js, constants.ts, *.config.ts
Glob: config.go, config.yaml, config.json, .env.example
Glob: application.properties, application.yml (Java)
Glob: config.rs, settings.rs, constants.rs, Cargo.toml (Rust — check [features], [dependencies])

→ Read to extract: key constants, thresholds, feature flags
```

**E. Read production pipeline/entry:**
```
→ Read the main entry points found in SCAN step D
→ Trace: which module calls which module, in what order
→ Document data flow: input → transform → output at each step
```

**F. Useful grep patterns (adapt paths according to discovered source roots):**
```
# Find module imports to understand dependencies
Grep: "^from {source_root}" or "^import {source_root}" (Python)
Grep: "^import.*from '\.\." or "require\(" (TS/JS)
Grep: "\"github.com/.*/..." (Go)

# Find DB/persistence layer
Grep: "collection=\|db\.\|\.save\(\|\.insert\(" trong source
Grep: "INSERT INTO\|CREATE TABLE\|mongoose.model\|@Repository"
```

**Deliverable:** Per-module summary card:
```
Module: [name]
Directory: [path]
Entry point: function/class signature
Key data structures: [names + where defined]
Config: [config file → key constants]
Dependencies: [other modules it imports]
```

---

## 3. SYNTHESIZE — Synthesize information

**Purpose:** Build a complete mental model of the architecture

**A. Dependency graph:**
- Map dependencies: module X requires output Y from module Z
- Check import statements in entry points
- Verify with the production pipeline (call order = dependency order)

**B. Data flow trace:**
- Trace each variable through the pipeline:
  - Input: what → function/method → output: what
  - What transform occurs between modules
- Document the type of intermediate data

**C. Detect cross-cutting patterns (from actual code, don't assume):**
Find recurring patterns in the code:
- Recurring naming conventions (e.g., every module has `orchestrator.py`, or every handler has `*Handler.ts`)
- Config centralization pattern (config in one place vs. scattered)
- Data model patterns (TypedDict, interfaces, structs, classes)
- Persistence patterns (repository, active record, direct DB calls)
- **Topology/domain/communication signals** (feeds an UPGRADE assessment even when not explicitly
  asked for): is this actually a modular monolith, a big-ball-of-mud monolith, or microservices?
  Is there a recognizable DDD tactical pattern in use, or an anemic model? Is communication
  synchronous only, or is there an event bus/broker? Note it — don't judge it here, VALIDATE §D
  in EXPLORE and MODE: UPGRADE are where it becomes a finding.

**D. Technology rationale:**
- Read CLAUDE.md/README/docs to find documented rationale
- If no explicit rationale is found → write "inferred from codebase" instead of fabricating

**Deliverable:** Architecture mental model (draft outline for 7 docs)

---

## 4. DOCUMENT — Write documentation

**Purpose:** Create 7 files in the output directory (discovered/configured in SCAN)

**File structure:**
```
{output_dir}/
├── README.md                   # Index, navigation, validation checklist
├── 01-system-overview.md       # Philosophy, goals, non-goals, high-level diagram
├── 02-module-architecture.md   # Module map, roles, dependency graph (Mermaid)
├── 03-data-flow.md             # Pipeline trace, intermediate variables, code snippets
├── 04-data-models.md           # Key data structure definitions with field descriptions
├── 05-tech-stack.md            # Stack table + rationale
└── 06-configuration-system.md  # Config pattern + override mechanism + examples
```

**Per-file content guidelines:** → Read `references/document-templates.md` for the detailed template for each file.

**Writing rules:**
- Every claim has `(source: path/to/file:line_number)` at the end of the sentence
- Mermaid diagrams: use `graph TD` or `flowchart TD`
- Code snippets: always include a language tag and source comment
- Don't write "likely", "probably", "might" — only write what has been read and verified
- `{project_name}` = taken from root docs/package files, don't hardcode

---

## 5. VALIDATE — Check for completeness

**Purpose:** Ensure documentation is accurate and complete

**Mandatory checklist:**

**Coverage:**
- [ ] All modules discovered in SCAN are present in `02-module-architecture`
- [ ] All public functions/classes are listed with the correct signature
- [ ] Every data model in `04-data-models` has field names verified against actual code

**Accuracy:**
- [ ] Function/class signatures match actual entry point files
- [ ] Field names in data models match actual model files
- [ ] DB collection/table names match actual code (if applicable)
- [ ] No field/function names are fabricated

**Navigability:**
- [ ] README.md has a navigation table
- [ ] Cross-references between documents work
- [ ] Mermaid syntax is valid (no syntax errors)

**Anomalies — document if discovered during code reading:**

While doing SCAN and DEEP_DIVE, if anything unusual is found, record it in the "Issues Discovered" section of README.md:
- **Missing dependencies**: Package imported in source but not present in requirements.txt / go.mod / package.json
- **Dead code references**: Legacy/deprecated code still referenced from production entry points
- **Doc-code gap**: Project documentation (CLAUDE.md, README) describes something different from the actual code structure
- **Circular imports**: Module A imports B and B imports A
- **TODO/FIXME at large scale**: Grep to check `TODO|FIXME|HACK` — if there are many, note it
- **Architecture anti-patterns** (from SYNTHESIZE §C): a distributed monolith (`references/microservices.md` §4), a shared database across "microservices," an anemic domain model dressed in DDD naming (`references/domain-driven-design.md` §4), or event-driven machinery with no async/decoupling need it's serving (`references/event-driven-architecture.md` §6) — these are architecturally significant, not incidental

If there are no anomalies → remove the "Issues Discovered" section from README.md.

**Validation actions:**
- Grep some function names from the documentation → verify they exist in actual code
- Re-read the README.md validation checklist and tick off items

**Deliverable:** Update the validation checklist in README.md (tick items that have been verified)

---

## UPDATE MODE

When the output directory **already exists** (docs aren't fresh):

1. **Read README.md** → check "Last Updated", modules covered, validation checklist state
2. **Re-run SCAN** → compare modules discovered with modules in 02-module-architecture.md
3. **Identify delta**:
   - New modules not yet in the docs
   - Functions/signatures that have changed
   - Sections in the docs that no longer reflect the actual code
4. **Update only outdated sections** — don't rewrite the entire file unless necessary
5. **Update README.md**: "Last Updated" date + re-tick the validation checklist

**Ask the user first** if: the output directory has a lot of custom content of unclear origin (it may be manually written docs that shouldn't be overwritten).
