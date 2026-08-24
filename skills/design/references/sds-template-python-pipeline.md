# SDS Template A: Python Data Pipeline

> Reference for `design` skill — loaded on demand when creating MODE A SDS documents.

---

## TEMPLATE A: Python Data Pipeline SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Module Level**: [discover from CLAUDE.md module map]
> **Related SRS**: {srs_file} § [Section]
> **Tech Stack**: {tech_stack — discover from CLAUDE.md or project config}

---

## 1. Module Overview

### 1.1 Purpose
[Describe what this module does in the pipeline, what problem it solves]

### 1.2 Pipeline Position
- **Level**: M-XX
- **Upstream dependencies**: [M-XX, M-YY, ...]
- **Downstream consumers**: [M-XX, M-YY, ...]
- **Orchestrator entry**: `{source_root}/{module}/orchestrator.py::{entry_func}()`

### 1.3 Scope
- **In Scope**: [List what this module computes]
- **Out of Scope**: [List what it deliberately does NOT compute]
- **Scale Tier**: [Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed — one-line reason. N/A only if this is purely a checkpointed-batch concern, see `.claude/skills/architecture/references/system-scale-checklist.md`]

---

## 2. Input Specifications

### 2.1 Required DataFrame Columns

| Column | Type | Source Module | Description |
|--------|------|--------------|-------------|
| `[column]` | [type] | [M-XX] | [description] |

### 2.2 Optional Columns

| Column | Type | Default if Missing | Description |
|--------|------|--------------------|-------------|
| `[column]` | [type] | `[value]` | [description] |

### 2.3 Validation Rules
- Minimum rows required: `[N]` (for rolling window calculations)
- Required columns must all be present (raise `ValueError` if missing)
- No all-NaN columns allowed

---

## 3. Output Specifications

### 3.1 New Columns Added to DataFrame

| Column | Type | Formula / Logic | Example Value |
|--------|------|----------------|---------------|
| `{indicator}_{period}` | float64 | `[formula]` | 45.3 |
| `{module}_score` | float64 | Weighted sum of sub-scores | 67.5 |
| `{module}_signal` | str | Enum from `{Module}Signal` | "BULLISH" |
| `[column]` | [type] | [logic] | [example] |

### 3.2 Orchestrator Signature

```python
def {entry_func}(
    df: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    [Describe what the function computes]

    Args:
        df: DataFrame with required upstream columns
        config: Optional overrides for thresholds/weights

    Returns:
        df with [N] new columns added
    """
```

---

## 4. Processing Design

### 4.1 Pipeline Steps

```
Step 1: Validate input (check required columns, min rows)
Step 2: Merge config (defaults + overrides)
Step 3: [Compute indicator group A]
Step 4: [Compute indicator group B]
Step 5: [Compute composite score]
Step 6: [Generate signal/classification]
Step 7: Return df with new columns
```

### 4.2 Scoring Logic

| Sub-score | Weight | Input Columns | Formula |
|-----------|--------|--------------|---------|
| `[sub_score_1]` | 0.35 | `[columns]` | [formula description] |
| `[sub_score_2]` | 0.30 | `[columns]` | [formula description] |
| `[sub_score_3]` | 0.20 | `[columns]` | [formula description] |
| `[sub_score_4]` | 0.15 | `[columns]` | [formula description] |
| **Total** | **1.00** | | |

### 4.3 Key Formulas

```python
# [Formula 1 name]  # SRS §X.Y
result_col = formula_description

# [Formula 2 name]  # SRS §X.Y
result_col = formula_description
```

### 4.4 Edge Cases
- Insufficient data (< min_rows): return df with NaN in output columns
- Division by zero: use `np.where(denominator != 0, numerator/denominator, 0)`
- All-NaN rolling window: fill with `[default value or NaN]`

---

## 5. Configuration Design

### 5.1 Config Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `[threshold_name]` | float | [value] | [what it controls] |
| `[weight_name]` | float | [value] | [what it controls] |
| `[period_name]` | int | [value] | Rolling window period |

### 5.2 Enums File
All defaults stored in: `{enums_file_path}` (discover from CLAUDE.md or Glob)

Config override pattern:
```python
from {enums_module} import {Module}Config

def get_merged_config(config: Optional[Dict] = None) -> Dict:
    defaults = {
        "[key]": {Module}Config.[KEY].value,
        ...
    }
    if config:
        defaults.update(config)
    return defaults
```

### 5.3 Security Considerations

Most MODE A modules process already-validated upstream DataFrames and have no auth/HTTP surface,
so this section is usually short — but don't skip it silently. State explicitly which apply:

- **Secrets**: if this module reads an API key, DB credential, or other secret (directly or via
  `{enums_file_path}`), it comes from an environment variable or secret manager — never a literal
  default value in the enums file. If this module has no secrets, state "N/A — no secrets."
- **Untrusted input**: if any input column originates outside this codebase's own upstream
  modules (an external API response, a user-uploaded file, a webhook payload rather than another
  M-XX module's output), treat it as untrusted at the boundary in §2.3 Validation Rules — the
  same "validate, don't trust" rule as an API's request body, not just a schema/type check.
- **Logging**: if the DataFrame carries PII or financial account data, state that step-level debug
  logging must not dump full rows — log shapes/counts/ids, not the sensitive column values.
- **Dependency security**: flag any new third-party library this module introduces for a
  vulnerability check in CI, same as any other module.

See `design/references/security-checklist.md` for the full stack-agnostic checklist if this module
is unusual for MODE A (e.g. it calls an external API, handles uploads, or manages credentials).

---

## 6. Module File Structure

Discover the exact layout from CLAUDE.md "Code Structure" section. Typical pattern:

```
{source_root}/{module}/
├── orchestrator.py    # Public API entry point
├── service.py         # Core business logic
├── validation.py      # Input DataFrame validation
├── models.py          # TypedDict, dataclasses for intermediate data
└── __init__.py        # Re-export public API

{enums_file_path}      # All thresholds, weights, period defaults
```

---

## 7. Error Handling

### 7.1 Input Errors (raise immediately)

| Condition | Error Type | Message |
|-----------|-----------|---------|
| Missing required column | `ValueError` | "Missing required column: {col}" |
| Insufficient rows | `ValueError` | "Need >= {N} rows, got {n}" |
| Wrong type | `TypeError` | "Column {col} must be numeric" |

### 7.2 Processing Errors (degrade gracefully)

| Condition | Behavior |
|-----------|---------|
| NaN in rolling window | Output NaN, continue processing |
| Division by zero | Output 0 or NaN as appropriate |
| Overflow/underflow | Clip to valid range |

---

## 8. Performance Design

### 8.1 Vectorization Rules
- All computations must be vectorized (pandas/numpy operations)
- No Python loops over DataFrame rows
- Use `.rolling()`, `.ewm()`, `.shift()` for time-series operations

### 8.2 Memory Notes
- Avoid in-place modifications to input df (use `.copy()` if mutating)
- Drop intermediate columns not needed in final output

### 8.3 Complexity & Large-Input Handling

State the time complexity of each processing step (§4.1) relative to row count — vectorized
pandas/numpy operations are typically O(N) per step, but a step that does a per-group Python loop
or a nested rolling computation can silently become O(N²). If this module can receive an unusually
large input (multi-year history, many symbols at once), state whether chunked/batched processing
is needed instead of a single in-memory transform — see
`design/references/performance-checklist.md` §1 and §15 for the full reasoning. Most MODE A
modules can state "N/A — bounded by upstream's row count, always vectorized" and move on.

If this module runs as a long batch job over a very large dataset (a backfill/migration-style
run, not a normal pipeline pass), state whether it checkpoints progress so a crash mid-run
resumes from the last checkpoint instead of restarting from zero — see
`design/references/distributed-systems-checklist.md` §18. Most MODE A modules are short enough
that this is N/A; state so explicitly if it doesn't apply.

---

## 9. Test Plan

### 9.1 Unit Tests

Discover test path convention from CLAUDE.md "Testing" section.

| Test Case | Input | Expected |
|-----------|-------|---------|
| `test_output_schema` | Valid input df | All output columns present |
| `test_config_override` | Custom threshold | Override applied correctly |
| `test_insufficient_data` | < min_rows | ValueError raised |
| `test_missing_column` | Drop required col | ValueError raised |
| `test_edge_case_nan` | NaN-heavy data | No crash, graceful NaN output |

### 9.2 Backtest Tests (if project has backtest infrastructure)

Discover backtest convention from CLAUDE.md or Glob `tests/backtest/`.

- Signal accuracy: win rate by signal class vs forward returns
- Threshold calibration: verify thresholds fire at appropriate frequency
- Score distribution: verify scores span full range, not compressed

### 9.3 Edge Cases
- Single-row DataFrame
- All-zero volume
- Price = 0 rows

---

## 10. Module Dependencies & SRS Traceability

### 10.1 Upstream Columns Consumed

| Column | Source Module | Used In Step |
|--------|--------------|-------------|
| `[column]` | M-XX | Step [N] |

### 10.2 SRS Traceability

| SRS Section | Requirement | Implemented In |
|-------------|-------------|---------------|
| § [X.Y] | [Requirement text] | service.py::[function], col: [column] |
| BR-XX | [Business rule] | validation.py::[function] |
```

---

## HOW TO USE THIS TEMPLATE

Before filling, discover from CLAUDE.md:
1. `{source_root}` — from "Code Structure" section (e.g., `src/v2`, `src`)
2. `{enums_file_path}` — Glob `**/*enum*.py` or read CLAUDE.md config pattern
3. `{enums_module}` — Python import path for enums
4. `{entry_func}` — from CLAUDE.md orchestrator pattern (e.g., `calculate_{module}_xxx`)
5. `{srs_file}` — Glob `docs/03-srs/*.md` (excluding `F-*.md`)
6. `{sds_path}` — Glob `docs/04-sds/` or `docs/*/sds/`
7. `{tech_stack}` — from CLAUDE.md "Tech Stack" or project config
8. `{test_path}` — from CLAUDE.md "Testing" section

## NAMING CONVENTIONS (MODE A)

Conventions are discovered from CLAUDE.md — below are examples, not rules:

- Module ID: `M-XX` (project-specific numbering)
- Module name: lowercase, hyphen-separated (`asset-analyzer`, `risk-engine`)
- Orchestrator function: project-specific pattern (discover from existing modules)
- Column naming: `{indicator}_{period}` (project convention)
- Enums file: discover via Glob — pattern varies by project

## PYTHON PIPELINE RULES (MODE A)

**Orchestration Pattern (typical, verify with CLAUDE.md):**
- Single public function as entry point
- Call `get_merged_config(config)` first to merge defaults + overrides
- Execute processing steps sequentially
- Return modified DataFrame (don't raise for missing optional cols)

**Forbidden (from CLAUDE.md principles — adapt per project):**
- ❌ God Modules: Mixing Data + Analysis + Reporting
- ❌ Circular Dependencies: Module A needs B, and B needs A
- ❌ Hidden Side Effects: Modifying global state or data owned by another module
- ❌ Creative Implementation: Adding logic not specified in SDS
- ❌ Duplicate Enums: Use shared enums from common module

**Required:**
- ✅ All output columns spec'd with type and formula
- ✅ All config keys have defaults
- ✅ Dependencies list exact upstream column names (verified from upstream SDS)
- ✅ Validation rules cover min_rows and required columns

**SDS Design Principle:**
Design from DataFrame I/O outward — don't design implementation before knowing input/output schema.
