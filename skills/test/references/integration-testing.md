# Integration Testing

Load this when the SDS's Data Integrity section is present, or the change writes to more than one
table/collection, or crosses an in-process module boundary (service → repository → real DB/cache)
that a unit test would otherwise mock away.

**Core principle:** mock the edge you don't own (a third-party API, a system outside your control),
never the boundary you're actually testing. A "unit test" that mocks the repository to prove the
service calls it correctly doesn't prove the query is correct, the constraint holds, or the
transaction actually commits — it proves the mock was configured the way you expected.

## 1. Use the real dependency, not a substitute [MUST]

```text
vulnerable: repository test asserts against an in-memory fake map
required:   repository test runs against a real (ephemeral/containerized) instance of the same
            database engine used in production — Postgres against Postgres, not H2/SQLite standing
            in for Postgres, since constraint behavior and type coercion differ between engines
```

An in-memory substitute is acceptable only when the project has no other option and the gap is
stated explicitly in the test's Implementation Readiness note — don't silently treat it as
equivalent coverage.

## 2. Test the constraint, not just the happy path [MUST]

If the Data Integrity section calls out a uniqueness constraint, a foreign key, or a multi-table
invariant, write a test that violates it and asserts the real database rejects it:

```python
def test_duplicate_account_number_rejected():
    create_account(number="123")
    with pytest.raises(IntegrityError):
        create_account(number="123")  # must hit the real unique constraint, not app-level validation only
```

A test that only checks app-level validation (`if exists(): raise`) without also exercising the DB
constraint will pass even if a second, unvalidated code path writes duplicates directly.

## 3. Isolate test data per test [MUST]

Each test must set up its own data and clean up after itself — via a transaction rolled back at
teardown, a truncate between tests, or a uniquely-namespaced key per test. Shared fixtures that
accumulate state across tests produce order-dependent failures: a test passes alone and fails only
when run after another test left rows behind.

## 4. Assert on observable state, not internal calls [SHOULD]

```text
weak:      assert repository.save was called once
stronger:  re-query the database and assert the row exists with the expected values
```

Asserting a mock was called proves the code *attempted* the write; re-reading real state proves
the write actually *succeeded and persisted correctly* — the thing the test exists to catch.

## 5. Run migrations before the suite, not by hand [SHOULD]

The test setup should apply the same migration scripts used in production (via the project's
migration tool) against the ephemeral test database, so schema drift between "what migrations
define" and "what the test DB actually has" surfaces as a test failure, not a production incident.

## Verify

```bash
# confirm the test actually talks to a real instance, not a mock
grep -n "Mock\|fake\|InMemory" <new_integration_test_file>   # should show none for the boundary under test

# confirm teardown exists — an integration test with no cleanup step is a future flake
grep -n "teardown\|rollback\|afterEach\|@AfterEach" <new_integration_test_file>
```

Run the new test twice in a row without a fresh database — if the second run fails and the first
didn't, cleanup is incomplete.
