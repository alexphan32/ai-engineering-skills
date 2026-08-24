# Functional Requirement Quality Bar

> Reference for `spec` skill — load in DRAFT when writing FR-XX entries (MODE B), and in
> VALIDATE when checking whether an existing FR is complete enough to hand to `/design`.

## Why a one-line FR isn't enough

A User Story states *who wants what and why*. A Functional Requirement states *what the system
actually does about it* — mechanism-neutral, but concrete enough that two different engineers
would build the same behavior from it. An FR that's just a restated User Story ("System lets
the user transfer money") gives `/design` nothing to derive a flow from — it invents the main
flow and error handling itself, which is exactly the guessing this skill exists to prevent.

## Required fields

Every FR needs all of these, not just Description + Priority:

| Field | What it captures |
|---|---|
| **Trigger / Precondition** | What causes this to run, and what must already be true (e.g. "user is authenticated and has role MAKER") |
| **Actor** | Who/what initiates it — ties back to the Stakeholders & Actors table |
| **Main Flow** | Numbered steps of what happens, in order — mechanism-neutral (describes outcomes and decisions, not implementation: "validate transfer amount against account balance" not "call `validateBalance()`") |
| **Outputs / Side Effects** | What changes as a result — response returned, state transition, record created, event emitted, notification sent |
| **Error & Exception Handling** | For each failure mode in the Main Flow, what the system does instead — every step that can fail needs a stated alternative, not just the happy path |
| **Related US** | Traces to ≥1 User Story (already required) |
| **Related BR / AC** | Which Business Rules constrain this flow, and which Acceptance Criteria verify it |
| **Priority** | Must Have / Should Have / Nice to Have (already required) |

An FR missing Main Flow or Error Handling is not draftable as complete — either fill it in from
what the user already said, or mark the gap `[OPEN QUESTION]` per
`references/ambiguity-and-assumptions.md` rather than leaving it implicit.

## Worked example

```markdown
### FR-03: Reject Duplicate Transfer Submission

**Trigger**: User submits a transfer request (POST /transfers)
**Precondition**: User is authenticated; source account belongs to the user

**Actor**: Authenticated account holder

**Main Flow**:
1. Compute an idempotency key from (source account, destination account, amount, submitted-at
   minute).
2. Check whether a transfer with the same key was already accepted in the last 60 seconds.
3. If no match: proceed with the transfer (see FR-01).
4. If a match exists: reject this submission without creating a new transfer record.

**Outputs / Side Effects**:
- No match: new transfer record created, 201 response with transfer ID.
- Match found: no new record created, 409 response with the existing transfer's ID.

**Error & Exception Handling**:
- Idempotency check itself fails (DB unavailable) → fail closed: reject the submission with a
  503, do not silently allow a possible duplicate through.

**Related US**: US-04 (prevent accidental double-submission)
**Related BR**: BR-02 (a transfer MUST NOT be created twice for the same duplicate-key window)
**Related AC**: AC-05, AC-06
**Priority**: Must Have
```

Compare this to a thin FR ("System prevents duplicate transfers. Related US: US-04. Priority:
Must Have") — the thin version looks fine at a glance but leaves the actual duplicate-detection
window, the failure-mode behavior, and the response codes entirely to whoever writes the design,
which is precisely the ambiguity this skill exists to close before it reaches `/design`.

## Common mistake

**Restating the User Story as the FR.** If the FR's Main Flow could be deleted without losing
any information already in the US, the FR isn't done — it needs the actual steps, decisions, and
failure handling the US doesn't (and shouldn't) specify.
