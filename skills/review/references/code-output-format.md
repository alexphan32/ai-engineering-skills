# Code Review — Output Format

> Loaded during Step 5 SUMMARY. Full output template for review reports.

---

## Output Template

```
PLAN:
- Scope: [review scope]
- Goal: [review objective]
- Exclusions: [what's out of scope]

SPLIT:
1. function_a
2. function_b
...

REVIEW:
Function: function_a (file_path:line_number)
- Issue: [problem description]
- Analysis: [detailed analysis]
- Severity: [critical/high/medium/low]
- Impact: [consequence if not fixed]

Function: function_b (file_path:line_number)
- Issue: [problem description]
- Analysis: [detailed analysis]
- Severity: [critical/high/medium/low]
- Impact: [consequence if not fixed]

PROPOSE:
- Proposal: [specific suggestion]
- Reason: [why change]
- Impact: [consequence if not fixed]

FIX (if requested):
- Changed code: [description or diff]
- Justification: [link to issue and proposal]

SUMMARY:
- Total issues: [count]
- By severity: critical: X, high: Y, medium: Z, low: W
- Priority fixes: [ordered list]
- Recommendations: [next step recommendations]
```

## Good vs Bad Examples

### Bad (too generic, not actionable):
"This code has a performance problem"

### Good (specific, actionable, with severity):

**Issue**: N+1 query problem in `get_user_profiles`
**Location**: src/users/service.py:45-52
**Analysis**:
- Loop through 1000 users, each iteration calls DB for `user.profile` → 1000 queries
- When users > 100, API timeout (current threshold: 5s)

**Severity**: High (API timeout affecting production users)

**Proposal**:
- Use `select_related('profile')` to eager load profiles in 1 query
- Or use `prefetch_related` if custom queryset needed

**Impact**:
- Reduce DB calls from O(n) to O(1)
- Improve response time from 8s to 0.8s (benchmark with 1000 users)

**Code suggestion**:
```python
# Before
users = User.objects.all()
for user in users:
    profile = user.profile  # N+1 query

# After
users = User.objects.select_related('profile').all()
for user in users:
    profile = user.profile  # No additional query
```

### Good distributed/async finding (names the failure mode, not just "missing idempotency"):

**Issue**: Core Banking timeout treated as business failure — `debit_account`

**Location**: src/transfers/core_banking_client.py:88-97

**Analysis**:
```python
try:
    response = core_banking_client.debit(request, timeout=3)
except TimeoutError:
    transaction.status = "FAILED"   # WRONG
    transaction.save()
```
- A `TimeoutError` on this call means the *response* was lost, not that Core Banking rejected
  the debit — Core Banking may have already processed it successfully
- Marking the transaction `FAILED` here, combined with any retry/resubmission path elsewhere in
  the code, creates a real risk of double-debiting the customer's account
- There's also no idempotency key on the `debit()` call, so even a deliberate retry after this
  timeout has no way to be a no-op if Core Banking did already process the first attempt

**Severity**: Critical (double-debit risk on a financial transaction)

**Proposal**:
- On `TimeoutError`, set `transaction.status = "UNKNOWN"`, not `"FAILED"`
- Add a status-inquiry call to Core Banking (or a scheduled reconciliation job) that resolves
  `UNKNOWN` transactions to their actual outcome
- Add an idempotency key to the `debit()` request so a legitimate retry is provably a no-op if
  Core Banking already applied the first attempt

**Impact**:
- Removes the double-debit risk this timeout path currently creates
- Matches the invariant that a timeout on an external call is not the same as a failure —
  the correct state is "we don't know yet," resolved by asking, not by guessing
