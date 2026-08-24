# Document Templates

Per-file content guidelines for the 7 architecture files.
Use these as starting structure — fill every section from actual code, never fabricate.

---

## `README.md`

```markdown
# Architecture Documentation — {project_name}

## Overview
[1-paragraph summary — derived from CLAUDE.md/README/docs. Cite source.]

## Navigation
| Document | Contents |
|----------|----------|
| [01-system-overview.md](01-system-overview.md) | Philosophy, goals, high-level diagram |
| [02-module-architecture.md](02-module-architecture.md) | Module map, roles, dependencies |
| [03-data-flow.md](03-data-flow.md) | Pipeline execution trace |
| [04-data-models.md](04-data-models.md) | Key data structures |
| [05-tech-stack.md](05-tech-stack.md) | Technology decisions |
| [06-configuration-system.md](06-configuration-system.md) | Config pattern |

## Issues Discovered
[Only fill in if there are anomalies. Leave blank or remove this section if there are none.]

Examples of what to note here:
- Packages imported in source but missing from dependency files (requirements.txt, go.mod, package.json)
- Legacy/deprecated code still referenced from production entry points
- Inconsistencies between docs and actual code
- Circular import patterns

## Validation Checklist
- [ ] All modules discovered in SCAN are covered in 02-module-architecture
- [ ] All public function/class signatures verified against actual code
- [ ] Mermaid diagrams render correctly
- [ ] Cross-references between documents work
- [ ] No fabricated information (all claims have source refs)

## Last Updated
[Date] — Generated from source code at [git branch/commit if available]
```

---

## `01-system-overview.md`

```markdown
# System Overview

## Context
[Copied/summarized from project docs — taken from actual files, cite source]

## Core Philosophy
[From docs — quote directly with source reference. If no docs exist → write "inferred from codebase"]

## Goals
[System goals — from docs or inferred]

## Non-Goals
[Explicit non-goals if present in docs]

## High-Level Architecture
[Mermaid diagram — top-level component flow]

## Key Constraints
[Technical constraints: language version, DB, external services, etc.]
```

---

## `02-module-architecture.md`

```markdown
# Module Architecture

## Module Dependency Graph
[Mermaid flowchart — components → arrows → components]

## Module Inventory
| Module | Directory | Role | Primary Output | Key Entry Point |
|--------|-----------|------|----------------|-----------------|
[Filled from SCAN + DEEP_DIVE — actual discovered modules only]

## Module Details
[Per-module section: purpose, files, public API signature, inputs, outputs]

## Cross-Cutting Patterns
[Patterns detected from actual code — e.g., orchestrator pattern, repository pattern, fail-safe pattern]
```

---

## `03-data-flow.md`

```markdown
# Data Flow

## Execution Order
[Numbered list: 1. Input → ... → N. Output/Persistence]

## Step-by-Step Trace
[For each step: variable_in → function_name(args) → variable_out, with source ref]

## Code Snippets
[Actual code from pipeline entry point — copy with source comment]

## Intermediate Data Structures
[What data looks like between modules — column counts, key fields, types]
```

---

## `04-data-models.md`

```markdown
# Data Models

## Model Catalog
| Model | Type | Module | File |
|-------|------|--------|------|
[All key data structures with location]

## Key Models
[For each key model: field table with type + description + source ref]
```

---

## `05-tech-stack.md`

```markdown
# Technology Stack

## Stack Summary
| Technology | Version | Role | Rationale |
|------------|---------|------|-----------|
[Filled from project files — requirements.txt / package.json / go.mod / pom.xml / Cargo.toml]
[Version = actual version pinned in dependency file, not guessed]

## Key Decisions
[Decisions with rationale — from actual docs or "inferred from usage pattern", don't fabricate]
```

---

## `06-configuration-system.md`

```markdown
# Configuration System

## Pattern Overview
[How config works in this project — from actual code, not generic description]

## Config Files
| Component | Config File | Key Constants |
|-----------|-------------|---------------|
[Filled from DEEP_DIVE — actual files discovered]

## Override/Customization Mechanism
[How config can be customized at runtime — from actual code]

## Example
[Real config snippet from one component — copy actual code with source ref]
```
