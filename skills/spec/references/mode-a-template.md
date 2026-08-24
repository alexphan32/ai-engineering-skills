# SRS Template A: Python Pipeline Module

> Reference for `spec` skill — loaded on demand when drafting MODE A SRS sections.

---

## TEMPLATE A: Python Pipeline Module SRS

```markdown
## M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Pipeline Level**: M-XX
> **Orchestrator Entry**: `{orchestrator_path}::{entry_function}()`

---

### Overview

**Purpose**: [Describe what this module does in the pipeline, what problem it solves]

**Pipeline Position**:
- Upstream: [M-XX, M-YY, ...]
- Downstream: [M-AA, M-BB, ...]

---

### Input Specifications

**Required DataFrame Columns:**

| Column | Type | Source Module | Description |
|--------|------|--------------|-------------|
| `[required_column]` | [type] | [M-XX] | [description] |

**Validation Rules:**
- Minimum rows required: [N]
- All required columns must be present (raise ValueError if missing)

---

### Output Specifications

**New Columns Added:**

| Column | Type | Description |
|--------|------|-------------|
| `{indicator}_{period}` | float64 | [description] |
| `{module}_score` | float64 | [description, range 0-100] |
| `{module}_signal` | str | [enum values: "BULLISH", "BEARISH", "NEUTRAL"] |

---

### Config Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `[threshold_name]` | float | [value] | [what it controls] |
| `[weight_name]` | float | [value] | [what it controls] |

**Config file**: `{config_file_path}` (discovered from project structure)

---

### Business Rules

**BR-01: [Rule Name]**
**Rule**: [Clearly describe the rule, using "must", "must not", "shall"]
**Rationale**: [Why this rule exists]

---

### Business Invariants

> A property that must hold across every call/row/run, forever — not just one rule for one
> case. E.g. "`{module}_score` MUST always be in [0, 100]" or "output row count MUST equal
> input row count". Leave explicitly "None beyond the Business Rules above" if there isn't one.

**INVARIANT-01: [Name]**
**Invariant**: [statement]

---

### Edge Cases

> Explicit Yes/No/N/A + expected behavior — don't wait for the user to volunteer these.

| Category | Applies? | Expected behavior |
|---|---|---|
| Empty / all-null input DataFrame | | |
| Fewer rows than minimum required | | |
| Duplicate rows (same key) | | |
| Extreme values (min/max of a config threshold) | | |
| Missing optional upstream column | | |

---

### Acceptance Criteria

**AC-01: Schema Completeness**
**Given** a valid DataFrame with required columns
**When** the module is called
**Then** all output columns listed above must be present in the returned DataFrame

**AC-02: Config Override**
**Given** a custom config dict with overridden thresholds
**When** the module is called with config parameter
**Then** the custom values must be used instead of defaults

**AC-03: Insufficient Data Handling**
**Given** a DataFrame with fewer than [N] rows
**When** the module is called
**Then** a ValueError must be raised with a descriptive message

---

### Dependencies

| Upstream Module | Columns Consumed |
|----------------|-----------------|
| [M-XX] | `[column_list]` |

---

### Assumptions & Open Questions

**Assumptions** (label per `references/ambiguity-and-assumptions.md` § 2):

| # | Statement | Label | Risk if wrong |
|---|-----------|-------|---------------|
| A1 | [statement] | `[ASSUMPTION]` / `[DECISION]` | |

**Open Questions:**

| # | Question | Owner | Status | Blocking? |
|---|----------|-------|--------|-----------|
| Q1 | [Question that needs clarification] | [Name] | Open | Yes/No |

---

### Implementation Readiness

**Status**: `READY` / `PARTIALLY_READY` / `BLOCKED`
**Blocking Questions**: [list Q# marked Blocking = Yes, or "none"]
**Critical Assumptions**: [A# with real risk if wrong, or "none"]
```
