# SDS Review — Output Format

> Loaded during Step 5 SUMMARY. Full output template for SDS review reports.

---

## Output Template

```
UNDERSTAND:
- Module: [Module ID - Module Name]
- Level: [Level in pipeline]
- Purpose: [brief summary]
- Upstream Dependencies: [modules this depends on]
- Downstream Consumers: [modules that consume this]
- Related SRS Sections: [SRS references]

STRUCTURE:
- Module shape: [API/full-stack | data-pipeline]
- Scale Tier stated: [Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed / NOT STATED] — [one-line reason if stated]
- ✅/❌ Module Overview
- ✅/❌ Input Specifications
- ✅/❌ Input Validation Rules
- ✅/❌ Output Specifications
- ✅/❌ Processing Logic
- ✅/❌ Configuration Parameters
- ✅/❌ Performance Requirements
- ✅/❌ Error Handling
- ✅/❌ Dependencies
- ✅/❌/N/A Security Design (required if API/full-stack; for data-pipeline, N/A is acceptable only if secrets/untrusted-input/logging are still addressed elsewhere)
- ✅/❌/N/A Performance Design (required if API/full-stack; for data-pipeline, N/A is acceptable only if complexity/large-input handling are still addressed elsewhere)
- ✅/❌/N/A Distributed & Async Design (required if the module crosses a service boundary, uses messaging, or calls an external system; N/A is acceptable only for a genuinely synchronous single-service module)
- ✅/❌/N/A Data Integrity (required if the module owns persistent state; N/A is acceptable only for a module with no new/changed table, collection, or durable output)
- ✅/❌/N/A Operations Readiness (required if the module deploys as its own service/process; N/A is acceptable only for a pure library/shared-code module)
- Missing Sections: [list if any]

VALIDATE:
Section: [Section Name]
- Issue: [problem description]
- Criterion: [Completeness/Clarity/Consistency/Feasibility/Testability/Interface/Traceability/Security/Performance/Distributed/DataIntegrity/OperationsReadiness]
- Analysis: [detailed analysis]
- Severity: [blocking/high/medium/low]
- Impact: [consequence if not fixed]
- Suggestion: [improvement proposal]

[Repeat for each issue found]

TRACE:
- SRS Coverage: [X/Y requirements traced]
- Orphan Requirements: [requirements not traced to SRS]
- Unused Outputs: [outputs not consumed by downstream]
- Missing Requirements: [SRS requirements not covered]

SUMMARY:
- Total Issues: [count]
- By Severity: blocking: X, high: Y, medium: Z, low: W
- By Criterion:
  - Completeness: X issues
  - Clarity: Y issues
  - Consistency: Z issues
  - Feasibility: W issues
  - Testability: V issues
  - Interface: U issues
  - Traceability: T issues
  - Security: S issues
  - Performance: P issues
  - Distributed: D issues
  - Data Integrity: I issues
  - Operations Readiness: O issues
- Readiness Assessment: [ready to implement / needs revision / incomplete]
- Blocking Issues: [must fix before implementation]
- Recommended Actions: [prioritized action items]
```

## Good vs Bad Examples

### Bad (not specific, not actionable):
"Input specification is incomplete"

### Good (specific, actionable, with severity):

**Section**: Input Specifications (M-04-risk.md:25-40)

**Issue**: Missing validation rules for RiskVector input from M-02

**Criterion**: Completeness

**Analysis**:
- M-04 receives RiskVector from M-02 Asset Technical Analyzer
- SDS only states "receives RiskVector dict" but doesn't specify:
  - Required fields in RiskVector (trend_strength, volatility_level, support_distance, etc.)
  - Data types for each field (float vs int vs enum)
  - Valid ranges (trend_strength: 0-1? -1 to 1?)
  - Behavior on missing fields (raise error vs use default vs skip calculation)
- Downstream code won't know how to validate input

**Severity**: Blocking

**Impact**:
- Implementation will lack input validation → runtime errors when M-02 changes output format
- Testing cannot write clear test cases (don't know valid/invalid inputs)
- Integration issues when M-02 and M-04 implemented by different developers

**Suggestion**:
Add "Input Validation Rules" section with table:

```markdown
### Input: RiskVector (from M-02)

| Field | Type | Range | Required | Default | Validation |
|-------|------|-------|----------|---------|------------|
| trend_strength | float | -1.0 to 1.0 | Yes | N/A | Raise ValueError if out of range |
| volatility_level | VolatilityLevel (enum) | LOW/MEDIUM/HIGH | Yes | N/A | Raise TypeError if not enum |
| support_distance | float | 0.0 to 1.0 | No | 0.5 | Clip to [0,1] if out of range |
...

Validation Logic:
- Missing required fields → raise InvalidRiskVectorError with specific field name
- Invalid types → raise TypeError with expected vs actual type
- Out of range values → clip to valid range + log warning for non-critical fields
```

### Good distributed/async finding (names the invariant violated, not just "missing idempotency"):

**Section**: Distributed & Async Design (M-07-fund-transfer.md:120-131)

**Issue**: §10.5 states "on Core Banking timeout, mark transaction FAILED and notify user" —
this violates the unknown-result/timeout≠failure invariant

**Criterion**: Distributed

**Analysis**:
- A timeout on the Core Banking debit call means the *response* was lost — Core Banking may
  have already applied the debit successfully
- Designing "timeout → FAILED" means the user could be told their transfer failed while their
  account was actually debited, and any retry/resubmission the user triggers based on that
  FAILED status would risk a second, real debit
- §10.5 also doesn't state an idempotency key on the Core Banking call, so even a deliberate
  retry has no way to be a safe no-op if the first attempt actually succeeded

**Severity**: Blocking

**Impact**:
- Implemented as spec'd, a Core Banking timeout under load could both incorrectly tell a
  customer their transfer failed AND risk double-debiting them on retry — this is exactly the
  failure mode enterprise banking distributed-systems review exists to catch before
  implementation, not after an incident

**Suggestion**:
Replace §10.5 with:
```text
On TimeoutError calling Core Banking:
  transaction.status = UNKNOWN
  schedule a status-inquiry call to Core Banking (or nightly reconciliation)
  do NOT notify the user of failure until the status is resolved

Core Banking call includes idempotencyKey = transaction.id, so a resolved retry
is a safe no-op if Core Banking already applied the original debit.
```
