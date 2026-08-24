# SRS Template B: REST API Feature

> Reference for `spec` skill — loaded on demand when drafting MODE B SRS documents.

---

## TEMPLATE B: REST API Feature SRS

```markdown
# F-XX: [Feature Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0

---

## 1. Overview

### 1.1 Description
[Brief description of what this feature does, what problem it solves]

### 1.2 Business Objectives
- [Objective 1: measurable business goal]

### 1.3 Scope
**In Scope:**
- [Item 1]

**Out of Scope:**
- [Item 1]

---

## 2. Stakeholders & Actors

| Actor | Role | Permissions | Description |
|-------|------|-------------|-------------|
| [Actor 1] | Primary | [PERMISSION_1, PERMISSION_2] | [Description] |

**Cross-actor questions** (answer explicitly, don't leave implicit):
- Can an actor perform this action on their own resource where that would normally be
  disallowed (e.g. Maker approving their own transaction)? [YES/NO/OPEN QUESTION]
- Can an actor perform this action on another tenant's/user's resource? [YES/NO/OPEN QUESTION]

---

## 3. User Stories

### US-01: [Story Title]
**As a** [role]
**I want to** [action/goal]
**So that** [benefit/value]

**Priority**: High / Medium / Low
**Story Points**: [1/2/3/5/8]

---

## 4. Functional Requirements

> A complete FR states the mechanism-neutral flow, not just a restated User Story — see
> `references/functional-requirement-quality.md` for the quality bar and a worked example.

### FR-01: [Requirement Name]
**Trigger**: [What causes this to run] | **Precondition**: [What must already be true]
**Actor**: [Who/what initiates it]

**Main Flow**:
1. [Step 1]

**Outputs / Side Effects**: [Response, state transition, record created, event emitted, ...]

**Error & Exception Handling**:
- [Failure mode] → [what happens instead]

**Related US**: US-01 | **Related BR**: [BR-XX, or "none"] | **Related AC**: [AC-XX]
**Priority**: Must Have / Should Have / Nice to Have

---

## 5. Non-Functional Requirements

### NFR-01: Performance
- Response time: [e.g.: < 200ms for 95th percentile]
- Throughput: [e.g.: 100 requests/second]

### NFR-02: Security
- Authentication: [JWT required / public endpoint]
- Authorization: [roles allowed]
- Data sensitivity: [PII, financial data, etc.]

### NFR-03: Scalability
- [Expected load, growth rate]

### NFR-04: Compliance & Availability

> Answer explicitly — "not stated, treat as internal/low-stakes" is a valid, explicit answer.
> Don't invent a number if the user hasn't given one; mark `[OPEN QUESTION]` instead. These
> facts feed `/design`'s Scale Tier classification directly — a "yes" here on external-system
> integration or a stated compliance need means `/design` treats this as enterprise/distributed
> regardless of how small current traffic looks.

- **Audit requirement**: which actions (if any) must be logged for compliance/audit purposes
  beyond ordinary application logs (e.g. APPROVE, TRANSFER, CHANGE_PERMISSION)? [list, or "none
  stated"]
- **Data retention**: does this feature's data have a legally-required minimum retention period,
  or a stated deletion/anonymization requirement? [state it, or "not stated"]
- **Availability/uptime**: is there a stated uptime target, RTO, or RPO — or is this explicitly
  an internal tool where downtime is a minor inconvenience? [state it, or "not stated — internal
  tool"]

---

## 6. Business Rules

### BR-01: [Rule Name]
**Rule**: [Clearly describe the rule, using "must", "must not", "shall"]
**Rationale**: [Why this rule exists]
**Related FR**: FR-01

---

## 6a. Business Invariants

> A Business Rule gates one action. An Invariant is a property that must hold across **every**
> flow and state, forever — list it here, not mixed into Business Rules, so a later unrelated
> change can't quietly violate it.

### INVARIANT-01: [Name]
**Invariant**: [A property that must always hold, e.g. "A transaction MUST NOT be financially applied more than once"]
**Why it must never break**: [consequence if violated]

*(Leave this section explicitly empty with a one-line note if the feature has no cross-cutting invariant beyond its Business Rules — don't omit the heading.)*

---

## 6b. State Machine & Transition Matrix

> Only if the primary entity has a lifecycle (states beyond exists/deleted) — GATHER should
> have already flagged this. This is the **business** state machine (what's allowed, by whom,
> under what condition) — `/design` derives retry/compensation/unknown-result mechanics from it.

**States**: `[STATE_1] → [STATE_2] → ... → [TERMINAL_STATE]` (list every reachable state, including failure/rejection terminals)

| Current | Action | Actor | Condition | Next |
|---------|--------|-------|-----------|------|
| [STATE_1] | [action] | [actor] | [condition, or "none"] | [STATE_2] |

**Explicitly answer**: can a terminal state (REJECTED/COMPLETED/FAILED) transition anywhere else? [NO / describe the exception]

*(N/A — state this explicitly, don't omit the heading — if the entity has no lifecycle.)*

---

## 7. Acceptance Criteria

### AC-01: [For US-01 or FR-01]
**Given** [context/precondition]
**When** [action]
**Then** [expected outcome]

---

## 7a. Edge Cases

> Required categories — give each an explicit Yes/No/N/A + expected behavior, don't wait for
> the user to volunteer them (see spec skill ANALYZE step).

| Category | Applies? | Expected behavior |
|---|---|---|
| Duplicate request/submission | | |
| Empty / zero / negative / maximum input | | |
| Expired or stale resource | | |
| Concurrent action on the same resource | | |
| Actor acting on their own resource (where disallowed) | | |
| Permission changed mid-flow | | |
| Downstream timeout / downstream success with lost response | | |

---

## 8. Out of Scope

- [Feature X: reason for not including it]
- [Integration Y: will be handled in F-XX-other-feature]

---

## 9. Dependencies

| Dependency | Type | Team Controls It? | Description |
|------------|------|--------------------|-------------|
| F-XX: Feature Name | Feature | Yes | [Requires this feature to function] |
| Core Banking / Payment Gateway / etc. | External System | No | [What this feature needs from it, and what happens if it's slow/down] |

> The **Team Controls It?** column matters beyond documentation: a "No" here is one of the
> signals `/design`'s Scale Tier classification (`.claude/skills/architecture/references/system-scale-checklist.md`
> §0) uses to decide whether this feature needs enterprise/distributed-grade design (reconciliation,
> unknown-result handling) — flag every external dependency here, even ones that feel minor.

---

## 10. Assumptions & Open Questions

**Assumptions** (label every one — see `references/ambiguity-and-assumptions.md` § 2):

| # | Statement | Label | Risk if wrong |
|---|-----------|-------|---------------|
| A1 | [statement] | `[ASSUMPTION]` / `[DECISION]` | [low / escalated to Open Question below] |

**Open Questions:**

| # | Question | Owner | Due Date | Status | Blocking? |
|---|----------|-------|----------|--------|-----------|
| Q1 | [Question that needs clarification] | [Name/Team] | [Date] | Open | Yes/No |

---

## 11. Implementation Readiness

**Status**: `READY` / `PARTIALLY_READY` / `BLOCKED`

**Blocking Questions**: [list Q# from above marked Blocking = Yes, or "none"]

**Critical Assumptions**: [A# that were escalated or carry real risk if wrong, or "none"]

**Ready scope** (if `PARTIALLY_READY`): [which use cases/FRs `/design` can start on now]
```
