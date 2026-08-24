# Database Design Checklist

Load this in DESIGN, when shaping the schema/data-model layer — MODE B's Entity, MODE C's Prisma
model, MODE D's JPA Entity, MODE E's Entity/Prisma model, and any MODE A module writing a durable
output another system reads as fact. This is the schema-*shape* question: what tables/collections
exist, how they're indexed, how they evolve — distinct from `data-integrity-checklist.md`, which
asks whether the shape you chose actually *holds* under concurrent, adversarial, or buggy callers
(constraints, atomicity, referential behavior). Design both together: this file first (what the
schema looks like), then `data-integrity-checklist.md` (how it stays correct).

## Priority levels

Same convention as the other checklists: **[MUST]** blocks the SDS from being done for a module
this applies to, **[SHOULD]** needs an explicit reason if skipped, **[MAY]** is a recommendation.

## 1. Normalization vs. Denormalization [MUST]

Default to normalized (one fact, one place) unless a stated read pattern justifies denormalizing.
State the reason when denormalizing — a duplicated/derived field with no stated reason is a data
staleness bug waiting to happen:

```text
Normalized:   Order → OrderLineItem → Product (price looked up live)
Denormalized: OrderLineItem stores `priceAtPurchase` — justified because a price change after
              purchase must not alter historical order totals; this is a business requirement,
              not a performance shortcut.
```

A denormalized/derived field always states: what keeps it in sync (write-time computation,
background job, DB trigger) and what happens if it drifts from its source — silent drift is a
`data-integrity-checklist.md` §10 reconciliation gap waiting to be found in production instead of in
design.

## 2. Indexing Strategy [MUST]

Design indexes from the **access pattern**, not from "index everything" or "index nothing until it's
slow." For every query this feature runs, state the columns it filters/sorts/joins on — this is
exactly what `api-design.md` §5's allowlisted filter/sort fields should already state; index against
those, not against a guess:

- Every foreign key column gets an index (most engines don't do this automatically) — a delete on
  the parent table without one forces a full scan of the child table to check referential integrity.
- A composite index's column order matters: put the equality-filtered column(s) before the
  range-filtered/sorted one (`WHERE tenant_id = ? AND created_at > ?` wants `(tenant_id,
  created_at)`, not the reverse).
- A unique constraint (`data-integrity-checklist.md` §1/§3) already creates an index — don't add a
  second regular index on the same column redundantly.
- State which indexes exist purely to support a specific query in this SDS — an index with no query
  using it is dead weight on every write.
- For a soft-delete pattern, a partial index (`WHERE deleted_at IS NULL`) scoped to live rows is
  usually what the common query path actually needs — a full-table index wastes space maintaining
  entries for rows no live query touches.

## 3. Query Access Pattern → Schema Fit [MUST]

State the top 2–3 queries this feature's schema must serve well *before* finalizing the shape — a
schema that's "correct" in isolation but forces an N+1 pattern or an unindexable filter at the
call site is a design defect, the same class of issue the DESIGN step's "query inside a loop"
prohibition targets, just one layer up: the fix there is batch-fetch; the fix here is not needing to.

```text
Bad:  Comment { postId } with no way to fetch "all comments for these 50 posts" in one query
      because postId isn't indexed and there's no batch-fetch-friendly shape.
Good: Comment { postId (indexed) } → WHERE postId IN (...) fetches all 50 posts' comments in one
      round-trip; the schema was designed knowing this is how the feed page reads it.
```

## 4. Migration Safety [MUST for any change to an existing table/collection with production data]

State the migration as a sequence of safe, independently-deployable steps — never a single step that
both changes the shape and assumes existing rows already match it:

```text
Adding a NOT NULL column to a populated table:
  1. Add the column as NULLABLE with a default (or no default)
  2. Backfill existing rows (batched, not one giant UPDATE on a hot table)
  3. Add the NOT NULL constraint once every row is confirmed populated

Renaming a column with an active reader/writer elsewhere:
  1. Add the new column, dual-write to old + new
  2. Backfill historical rows
  3. Migrate readers to the new column
  4. Drop the old column only after nothing reads it
```

State whether the migration is reversible (a rollback migration exists) and whether it locks the
table for its duration — a migration that locks a large, high-traffic table needs a stated
maintenance-window or online-migration-tool plan, not a silent assumption that it'll be fast enough.

## 5. Connection & Transaction Sizing [SHOULD — cross-reference, don't re-derive]

Connection pool sizing and transaction-scope rules (short/deterministic/DB-only) already live in
`performance-checklist.md` and the DESIGN step's prohibited-patterns list — this file doesn't
restate them. State here only what's schema-specific: whether this table/collection is expected to
be a write hotspot (many concurrent writers to the same row/document — feeds `data-integrity-checklist.md`
§5's lost-update mechanism) or a read hotspot (feeds §2's indexing and whether a read replica/cache
in front of it is warranted).

## 6. Document/Collection Shape (MongoDB-style stores) [MUST when the engine is document-oriented]

For MODE B (MongoDB via Fiber) or any Mongo-backed collection: state embedding vs. referencing per
relationship explicitly — this is the document-store equivalent of §1's normalization call:

- **Embed** when the sub-document is always read/written with its parent, has a bounded size, and
  is never queried independently (e.g. an `Address` embedded in `Customer`).
- **Reference** (store an ID, join in application code) when the related data is large, unbounded
  (a customer's transaction history), queried independently, or shared across multiple parents.
- State the max realistic size of any embedded array — MongoDB's document size limit (16MB) is a
  real constraint, and an unboundedly-growing embedded array (e.g. embedding every transaction
  inside its account document) is a design defect that surfaces only once production data grows.

## 7. Schema Ownership in a Shared Store [MUST when 2+ features/services touch the same table/collection]

State which feature owns which fields when a table/collection is shared — this is the schema-design
counterpart to MODE C's Prisma-model-ownership rule (`design/SKILL.md` MODE C prohibited list) and
applies equally to MODE B/D/E's shared tables: an unowned or ambiguously-owned field is where two
features silently overwrite each other's writes.

## 8. Anti-Patterns — Red Flags

If any of these appear in a design, stop and redesign: an index added with no query in this SDS
that uses it; a foreign key column with no index; a migration that adds a `NOT NULL` column to a
populated table in one step with no backfill phase; a denormalized/derived field with no stated
sync mechanism; an embedded array in a document store with no stated bound; a schema decided before
knowing the queries it must serve; a shared table/collection with no stated per-field ownership.

## 9. Invariants

```text
1. Every foreign key column has a supporting index.
2. Every index in the design maps to a stated query that uses it.
3. A composite index's column order puts equality filters before range/sort columns.
4. Any NOT NULL column added to a populated table is migrated in add → backfill → constrain steps.
5. A denormalized/derived field states its sync mechanism and drift-detection path.
6. An embedded document/array (document stores) states its realistic max size.
7. A table/collection shared across features states per-field write ownership.
```

## 10. Mandatory Test Cases [MUST include in the test plan when this checklist applies]

Query against the top stated access pattern returns via an index, not a full scan (verify with
`EXPLAIN`/equivalent, not assumption); migration applied against a populated table/collection
matching production shape (not just an empty test DB); rollback migration restores the prior schema
cleanly; a write to a shared table/collection from one feature doesn't clobber a field another
feature owns.
