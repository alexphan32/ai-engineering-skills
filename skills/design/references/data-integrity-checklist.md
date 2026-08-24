# Data Integrity Checklist

Load this whenever a module owns persistent state — every MODE B/C/D/E module with a database
table, and any MODE A module that writes a durable output another system reads as fact. This is
different from the security checklist's Business Security section (§10 there): that section asks
"can a malicious or racing caller corrupt this data on purpose or by accident under load," this
one asks the broader question "does the *design itself* let the data become wrong even when every
caller behaves" — missing constraints, silent partial writes, unstated rounding, an audit trail
that exists in theory but was never given a concrete shape.

## Priority levels

Same convention as the other checklists: **[MUST]** blocks the SDS from being done for a module
this applies to, **[SHOULD]** needs an explicit reason if skipped, **[MAY]** is a recommendation.

## 1. Database Constraints as First Line of Defense [MUST]

Application-level validation is necessary but not sufficient — a second code path, a manual DB
fix, a future service sharing the table, or a bug in the validation logic itself can all bypass
app-level checks. The database's own constraints are what actually make an invariant impossible to
violate, not just unlikely to be violated:

```sql
CHECK (amount > 0)
CHECK (status IN ('DRAFT','PENDING','COMPLETED','FAILED'))
NOT NULL account_id
UNIQUE (tenant_id, external_reference)
FOREIGN KEY (account_id) REFERENCES account(id)
```

For every field the SDS states a business rule about ("amount must be positive," "email is
required," "reference number is unique per tenant"), state whether that rule is enforced at the
DB layer, the app layer, or both — "app layer only" is a valid answer for a low-stakes field, but
it must be a stated decision, not an unexamined gap. A financial amount, a state/status field, and
any uniqueness the business depends on should be DB-enforced whenever the engine supports it.

## 2. Referential Integrity [MUST]

State the foreign-key relationships this module's schema participates in, and the delete/update
behavior deliberately chosen for each — `RESTRICT`, `CASCADE`, or `SET NULL` have very different
consequences and "whatever the ORM defaults to" is not a design decision:

```text
Deleting an Account with existing Transactions:
  RESTRICT → deletion blocked while transactions exist (safest default for financial data)
  CASCADE  → deleting the account silently deletes its transaction history (rarely correct for
             an audited entity — flag if the design implies this)
  SET NULL → transactions become orphaned from any account (rarely correct either)
```

A schema design that's silent on this defaults to whatever the ORM/migration tool picks, which is
often the wrong choice for an audited or financial entity.

## 3. Duplicate Prevention via Uniqueness, Not Just a Pre-Check [MUST]

"Check if it exists, then insert if not" has a race window between the check and the insert —
two concurrent requests can both pass the check before either commits:

```text
vulnerable:                              required:
if not exists(ref):                      INSERT ... ON CONFLICT (ref) DO NOTHING
    insert(ref)                          -- or catch the unique-constraint violation and
                                          -- treat it as "already exists", not a 500 error
```

Every field the business requires to be unique (external reference, idempotency key, email,
account number) needs an actual DB uniqueness constraint — the check-then-insert pattern is a
performance optimization to avoid a wasted round-trip, never the correctness mechanism itself.

## 4. Atomicity of Multi-Step Writes [MUST]

When a single business operation touches more than one table/row, state which of those writes
must succeed or fail together. A design that writes to table A, then table B, as two independent
statements with no shared transaction risks a partial write if the process crashes or a later
statement fails after an earlier one committed:

```text
Transfer = debit(fromAccount) + credit(toAccount) + insert(transferRecord)
```

If all three must be atomic and share one database, state they're in one transaction (subject to
the Performance checklist's transaction-scope rule — short, deterministic, DB-only). If they span
services/databases, that's not an atomicity problem to solve with a bigger transaction — it's a
Saga/Outbox design, covered in `distributed-systems-checklist.md`.

## 5. Lost Update on a Single Database [MUST for any concurrently-updated row]

This is the same concern as `performance-checklist.md` §20 and `distributed-systems-checklist.md`
§12, restated here because it's easy to assume "we're not distributed, so this doesn't apply" —
it applies to any two requests hitting the same row, distributed or not:

```text
Request A: read balance=100         Request B: read balance=100
Request A: write balance=100-30=70  Request B: write balance=100-50=50   ← A's debit is lost
```

Name the mechanism (optimistic version column, `SELECT ... FOR UPDATE`, or a state machine that
makes the race safe by construction) for every row multiple requests can update concurrently.

## 6. Invariant Validation Before Persist [MUST]

Every business invariant the SRS states ("a transaction amount must be positive," "a COMPLETED
transaction cannot return to DRAFT") needs a stated enforcement point *before* the write — not an
assumption that the caller already validated it. State explicitly: which layer validates, what
happens on violation (reject with a specific error, not a generic 500), and whether the same
invariant is also expressed as a DB constraint (§1) as a second line of defense.

## 7. Soft Delete & Its Referential Consequences [SHOULD, MUST if this module ever deletes rows other data references]

If a row can be soft-deleted (`deleted_at`, `status = 'DELETED'`) or hard-deleted, state what
happens to:

- **Sequence/order fields**: if rows have an `order`/`position` column, deletion creates gaps —
  any "prev/next" or "nth item" logic must query nearest-neighbor, never assume contiguity
  (`order ± 1`).
- **Referencing rows**: does a child row become orphaned, get cascade-deleted, or get its FK set
  null? (Same question as §2, specifically for the delete-triggered case.)
- **Unique constraints**: does a soft-deleted row still occupy a unique slot (e.g. can a new user
  register with an email a soft-deleted user used)? State whether the unique constraint is scoped
  to `WHERE deleted_at IS NULL` (partial index) or applies globally.

## 8. Numeric & Financial Precision [MUST for any monetary/financial amount]

State the exact numeric type for every financial field — `DECIMAL(19,4)`/`NUMERIC` or an integer
minor-unit representation (cents), never a floating-point type (`float`, `double`, JS `number`)
for money, since binary floating point cannot represent most decimal fractions exactly and
accumulates rounding error across many operations. State the rounding rule (banker's rounding vs.
round-half-up) and where in the calculation chain rounding happens — rounding at each step vs.
rounding only the final result can produce different totals, and the SRS or a stated design
decision should say which is correct for this domain.

## 9. Audit Trail — Concrete Shape [MUST for the actions `security-checklist.md` §11 already
requires an audit log for]

The security checklist says *which* actions need an audit log (LOGIN, CREATE, UPDATE, DELETE,
APPROVE, REJECT, TRANSFER, CHANGE_PERMISSION, CHANGE_PASSWORD). This section defines *what an
audit entry must contain* — a log line that says "transaction updated" is not an audit trail:

```json
{
  "actor": "user123",
  "action": "TRANSACTION_APPROVED",
  "resource": "transaction:tx_789",
  "before": { "status": "PENDING_APPROVAL" },
  "after": { "status": "APPROVED" },
  "occurredAt": "2026-08-23T10:15:00Z",
  "correlationId": "req_abc123",
  "reason": "optional — free-text justification if the action supports one"
}
```

Design where this is stored: a dedicated audit table/append-only log — not solely the application
log stream, which is typically not queryable by business users, is often retained for a shorter
period than compliance requires, and can be lost/rotated independently of the business data it was
describing. State the retention period for the audit trail itself (see
`operations-readiness-checklist.md` §12 for the general data-lifecycle question).

## 10. Reconciliation for Non-Distributed Data Quality [SHOULD, MUST for financial ledgers]

`distributed-systems-checklist.md` §19 covers reconciling against an external system. The same
principle applies inside a single database: don't just trust that application logic always kept
derived/aggregate data correct. For a ledger, wallet, or any running-total design, state a
periodic (or on-demand) check that the aggregate matches the sum of its parts:

```text
account.balance ?= SUM(ledger_entries.amount WHERE account_id = account.id)
```

A mismatch here means a bug already corrupted data silently — design what happens when one is
found (alert, freeze the account pending investigation, auto-repair only if the repair logic is
itself trustworthy).

## 11. Data Classification [SHOULD]

State whether the data this module owns is Public, Internal, Confidential, PII, or Financial —
this classification is what later decisions (encryption at rest, retention period, who can query
it, whether it needs masking in non-prod environments) should be justified against, rather than
each of those being decided independently per field.

## 12. Idempotency at the Data Layer for Non-Distributed Writes [MUST for a write endpoint susceptible to duplicate submission — double-click, client retry, browser back-button resubmit]

Not every duplicate-submission risk is a distributed-systems problem — a plain synchronous REST
endpoint can receive the same logical request twice from an impatient user double-clicking submit.
State the mechanism: an `Idempotency-Key` column with a unique constraint, or a natural
business-key uniqueness constraint (§3) that makes the second identical request a safe no-op
(return the original result) rather than a second effect.

## 13. Validation Ordering [SHOULD]

State the order explicitly when it matters: validate (type/format/range) → normalize (trim,
case-fold, canonicalize) → business-rule check (against current DB state) → persist. A common
source of subtle bugs is normalizing after a uniqueness check instead of before it (e.g. checking
email uniqueness before lowercasing it lets `User@x.com` and `user@x.com` both pass as "unique"
when the business intends them to collide).

## 14. Anti-Patterns — Red Flags

If any of these appear in a design, stop and redesign: a business invariant stated only in prose
with no enforcement point named; a uniqueness requirement enforced only by an app-level
check-then-insert; money represented as `float`/`double`; a multi-table write with no stated
transaction boundary and no Saga/Outbox for the cross-service case; a delete design silent on what
happens to referencing rows; an audit log requirement satisfied by "we have application logs";
a ledger/balance design with no reconciliation path ever mentioned; a soft-delete design that lets
a new row collide with a "deleted" one's unique value without saying whether that's intended.

## 15. Invariants

```text
1. Every stated business invariant on persisted data has a named enforcement point.
2. A financial/critical uniqueness requirement is enforced by a DB constraint, not app logic alone.
3. Every foreign-key relationship states its delete/update behavior deliberately.
4. Money is never represented as binary floating point.
5. Every audit-logged action captures actor, action, resource, before, after, timestamp, and correlation — not just a free-text message.
6. A multi-row write that must be atomic is either in one short DB transaction or an explicit Saga/Outbox design.
7. A ledger/aggregate value has a stated reconciliation path against its source rows.
8. Soft-deleted rows' effect on uniqueness constraints and ordering/sequence fields is stated, not assumed.
```

## 16. Mandatory Test Cases [MUST include in the test plan for a module this checklist applies to]

Concurrent duplicate submission (two identical requests racing — expect one effect, not two);
unique-constraint violation surfaced as a clean 4xx/business error, not a raw 500/stack trace;
concurrent update to the same row (expect a lost-update-prevention error or the losing write
retried, never a silently overwritten value); partial-failure mid multi-table write (expect full
rollback, not a half-committed state); soft-delete followed by an attempt to recreate the same
unique value (expect the design's stated behavior, not an accidental collision or an accidental
permanent block); a reconciliation check catching a deliberately-corrupted aggregate in a test
fixture.
