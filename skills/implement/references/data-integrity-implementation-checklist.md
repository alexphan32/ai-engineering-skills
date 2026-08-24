# Data Integrity Implementation Checklist

Load this whenever the code being implemented writes to a table/collection this service owns.
Design-time rationale for every item here lives in
`.claude/skills/design/references/data-integrity-checklist.md` — this file verifies the code
actually enforces what was designed, with concrete per-stack patterns.

## Priority levels

Same convention as the other implementation checklists: **[MUST]** blocks completion, **[SHOULD]**
needs an explicit reason if skipped.

## 1. DB Constraints Actually Exist [MUST]

Verify the migration for this change includes the constraint the SDS named — a `CHECK`,
`NOT NULL`, `UNIQUE`, or `FOREIGN KEY` mentioned in the design but never added to the actual
migration file is a gap that won't surface until a bad row is already in the table:

```sql
ALTER TABLE transactions ADD CONSTRAINT chk_amount_positive CHECK (amount > 0);
ALTER TABLE transactions ADD CONSTRAINT uq_external_ref UNIQUE (tenant_id, external_reference);
```

Don't rely on ORM-level `@Column(nullable = false)`-style annotations alone if the design called
for a DB-level constraint — verify the generated/hand-written migration actually creates it.

## 2. Duplicate Prevention Uses the Constraint, Not Just a Pre-Check [MUST]

```python
# vulnerable — race window between the check and the insert
if not Reference.objects.filter(ref=ref).exists():
    Reference.objects.create(ref=ref)

# required — let the unique constraint be the actual guard, handle the conflict
try:
    Reference.objects.create(ref=ref)
except IntegrityError:
    return existing_result_for(ref)   # or raise a clean 409/business "already exists" error
```

Verify the catch/conflict-handling path returns a clean business response (existing result, or a
409-style "already processed") rather than letting the raw constraint-violation exception surface
as a 500.

## 3. Multi-Table Write Atomicity [MUST]

Grep for a multi-step write (more than one `INSERT`/`UPDATE`/`.save()` call implementing one
business operation) with no surrounding transaction — verify it's wrapped in the shortest
transaction that covers exactly those statements (per the Performance checklist's transaction-scope
rule: no external call inside it), or, if the writes span services, that it's implemented as the
Saga/Outbox pattern the SDS specified rather than an ad-hoc "hope both succeed."

## 4. Optimistic Locking / Lost-Update Prevention Wired, Not Just Modeled [MUST for a concurrently-updated entity]

```sql
UPDATE account SET balance = ?, version = version + 1 WHERE id = ? AND version = ?
```

Verify the calling code actually checks the affected-row count and treats `0` as a
concurrent-modification error (retry with the fresh version, or fail explicitly to the caller) —
a version column that exists on the entity but whose `0`-rows-updated result is silently ignored
provides no protection at all.

## 5. Invariant Enforcement at the Actual Write Path [MUST]

For every business invariant the SDS named (amount positive, valid state transition, required
field), verify the validation actually runs on every code path that can reach the write — not just
the primary "happy path" handler. A second admin-tool endpoint, a bulk-import script, or a data-fix
utility that writes to the same table without going through the same validation is a common way an
invariant that "is definitely enforced" turns out not to be, for that one code path.

## 6. Money Never as Floating Point [MUST]

```python
amount = 19.99          # WRONG for money — binary floating point, accumulates rounding error
amount = Decimal("19.99")   # required — or an integer minor-unit representation (cents)
```

Grep for a monetary field typed as `float`/`double`/bare JS `number` and flag it — this is a
Critical-severity finding regardless of how the value is currently used, because the error compounds
silently across many operations before anyone notices a discrepancy.

## 7. Soft Delete Doesn't Silently Break Uniqueness or Ordering [SHOULD, MUST if this code path soft-deletes rows with a unique constraint or an order/position field]

Verify a unique constraint that must allow reuse of a value after soft-delete is actually scoped to
active rows (`WHERE deleted_at IS NULL` partial index / equivalent), and that any "prev/next" or
"nth" query near a soft-deletable, ordered table doesn't assume the `order` column is contiguous —
query nearest-neighbor, never `order ± 1`.

## 8. Audit Entry Written With the Full Shape [MUST for actions requiring an audit log]

```json
{"actor": "user123", "action": "TRANSACTION_APPROVED", "resource": "transaction:tx_789",
 "before": {"status": "PENDING_APPROVAL"}, "after": {"status": "APPROVED"},
 "occurredAt": "...", "correlationId": "..."}
```

Verify the audit write actually captures before/after state (not just "transaction updated") and
is written to the durable audit store the design specified — not solely `logger.info(...)`. Verify
it's written in the same transaction as the business change where feasible, so an audit entry can't
exist for a change that was rolled back, or vice versa.

## 9. Reconciliation Check Actually Runs [SHOULD for a ledger/aggregate value]

If the design specified a periodic reconciliation (`account.balance` vs. `SUM(ledger_entries)`),
verify the job/query exists and is scheduled — not just designed. Verify a detected mismatch
produces an actionable signal (alert, flagged record) rather than a log line nothing reads.

## 10. Migration Safety Actually Followed [MUST for any migration touching a populated table/collection]

Design-time sequencing rationale lives in
`.claude/skills/design/references/database-design.md` §4 — this item verifies the migration
*files* actually implement that sequence, not just the SDS describing it:

```sql
-- vulnerable — single step, fails immediately on any existing NULL row, or locks the whole
-- table while every row is validated against the new constraint at once
ALTER TABLE transactions ADD COLUMN status VARCHAR NOT NULL;

-- required — three separate, independently-deployable migrations
-- 1) add nullable
ALTER TABLE transactions ADD COLUMN status VARCHAR;
-- 2) backfill (batched, not one giant UPDATE — see distributed-systems-implementation-checklist §18)
-- 3) constrain, only after every row is confirmed populated
ALTER TABLE transactions ALTER COLUMN status SET NOT NULL;
```

Verify: a `NOT NULL` column added to a table that already has rows is split across add →
backfill → constrain migrations (not one step); a rollback migration exists and has actually been
run against a copy of production-shaped data, not just written and assumed to work; a large/
high-traffic table's migration either runs online (tool/mechanism stated) or has a stated
maintenance window — a migration that silently locks a hot table for the deploy's duration is a
production incident, not a deploy detail.

For a document store (Mongo-backed collection): verify an embedded array the design called
bounded actually has an enforced max size in the write path (application-level check or schema
validator), not just a comment saying it should stay small.

For a table/collection the design flagged as shared across features: grep the write path for a
change to a field the design didn't assign to this feature — an unowned or wrongly-owned field
write is how two features silently clobber each other's data.

## 11. Anti-Pattern Grep Sweep [MUST — run before claiming data-integrity-reviewed]

```bash
# money as float/double
grep -rn "float.*amount\|double.*amount\|amount.*: number" <changed_files>

# check-then-insert without a surrounding unique constraint / conflict handling
grep -n -B3 "\.create(\|INSERT INTO" <changed_files> | grep -B3 "exists()\|findOne(\|SELECT.*WHERE"

# status/state field assigned directly (cross-check against distributed-systems checklist too)
grep -rn "\.setStatus(\|status = \"" <changed_files>

# migration file missing a constraint the SDS named (manual check — grep can only find candidates)
grep -n "CHECK\|UNIQUE\|NOT NULL\|FOREIGN KEY" <migration_files>

# NOT NULL added in the same migration step as the column itself (candidate — verify by hand)
grep -n "ADD COLUMN.*NOT NULL" <migration_files>
```

## 12. Failure-Scenario Test Coverage [MUST]

Verify tests exist for: concurrent duplicate submission (expect one effect), a unique-constraint
violation surfaced as a clean business error (not a raw 500), a lost-update attempt (expect a
version-conflict error, not a silently overwritten value), and — for a multi-table write — a
forced failure partway through that verifies full rollback rather than a partial commit. For a
migration touching a populated table: the migration applied against production-shaped data (not
an empty test DB), and the rollback migration restores the prior schema cleanly.
