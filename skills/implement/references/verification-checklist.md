# Implement Skill — Reference Material

Generic verification detail that doesn't need to be always-loaded in `SKILL.md`. The mechanical
security/performance/distributed grep checks live in `scripts/verify-checks.sh` and the five
specialized checklists (security/performance/distributed-systems/data-integrity/operations-
readiness) — this file does not restate them.

## GOOD VS BAD IMPLEMENTATION EXAMPLE

### ❌ SQL injection vulnerability

```python
def get_user(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return db.execute(query)

# Attack: username = "admin' OR '1'='1"
```

### ✅ Parameterized query + input validation

```python
import re

def get_user(username: str) -> Optional[Dict]:
    """Retrieve user by username (alphanumeric + underscore, 3-32 chars)."""
    if not re.match(r'^[a-zA-Z0-9_]{3,32}$', username):
        raise ValueError(f"Invalid username format: {username}")

    query = "SELECT * FROM users WHERE username = ?"
    result = db.execute(query, (username,))
    return result.fetchone() if result else None
```

The shape that generalizes: validate at the boundary (whitelist, not blacklist), then pass
untrusted input to the DB/shell/template engine only through an API that can't reinterpret it as
code (parameterized query, not string interpolation).

---

## IMPLEMENTATION PRIORITY

When time is short, this is the order to protect — don't spend P2/P3 effort while P0 is still open:

| Priority | Covers | Rule |
|---|---|---|
| **P0 — Critical** | Input validation, auth/authorization, injection prevention, core logic correctness | Don't ship until complete |
| **P1 — High** | Full feature per requirements, edge cases, integration with existing modules | Don't move to P2 until P1 is stable |
| **P2 — Medium** | Tests for critical paths, docstrings, README/CHANGELOG | Can ship partial, but state the plan to finish |
| **P3 — Low** | Performance tuning, refactors, extra features | Never trade against P0-P2 |

---

## VERIFICATION CHECKLIST (MANDATORY)

Security, performance, and distributed/async checks are `SKILL.md`'s VERIFY step +
`scripts/verify-checks.sh` + the specialized checklists — don't re-derive them here. What's below
is the rest of "done": code quality, docs, integration, and final review.

### Code Quality
```bash
<project_linter> <changed_paths>          # e.g. ruff/eslint/golangci-lint/checkstyle
<project_formatter> --check <changed_paths>
<project_type_checker>                    # mypy / tsc / etc., if the project uses one
```
- [ ] Linter passed or warnings justified
- [ ] Files placed in the correct modules/folders per the project's architecture
- [ ] Constants/enums used from their shared location, not redefined locally

### Testing
- [ ] All tests pass, not just the new one
- [ ] Coverage adequate for the critical paths touched (check the project's coverage tool)
- [ ] Edge cases tested (empty inputs, None/null, boundary values)
- [ ] Error conditions tested (exceptions/errors raised as expected)

### Documentation
- [ ] Docstrings on public functions/classes with non-obvious logic (Args/Returns/Raises)
- [ ] Comments explain WHY, not WHAT
- [ ] README/CHANGELOG updated if setup, CLI, or module structure changed

### Integration
- [ ] Works with existing modules — no unannounced breaking change
- [ ] Backward compatible, or migration path documented
- [ ] New env vars/config documented; new dependencies added to the project's manifest

### Final Self-Review
- [ ] Code re-read line-by-line against the plan/SDS
- [ ] No TODOs left unaddressed (or logged in Known Limitations)

---

## TROUBLESHOOTING

**Tests failing:** read the actual assertion error first, not just pass/fail; run the single
failing test in verbose/debug mode (`pytest -v -s --pdb`, `go test -run TestX -v`, `--inspect-brk`,
etc. — whichever the project's runner supports) before touching code.

**Linter failing:** most linters have an autofix mode (`ruff check --fix`, `eslint --fix`,
`gofmt -w`) — run it first, then fix what's left by hand or justify with an inline suppression.

**Dependency scan failing:** check the CVE detail, upgrade the vulnerable package if a fixed
version exists; if not, document the accepted risk and mitigation rather than silently ignoring it.
