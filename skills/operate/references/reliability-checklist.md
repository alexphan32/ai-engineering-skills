# Reliability Checklist

Load this when phase C (RELIABILITY) needs to go beyond "state the SLO" — specifically deciding
what happens when the error budget burns down, whether the system has actually been tested under
load or failure, and whether a third-party dependency is a hidden single point of failure.

## 1. Error Budget Policy

An SLO without a stated consequence for breaching it is just a number on a dashboard. State what
changes when the error budget is exhausted for a period — e.g. feature freeze until the budget
recovers, mandatory postmortem, escalation to a specific owner. If there's no error budget policy
yet, that's fine to state explicitly ("no formal policy — SLO breach triggers ad hoc review"), but
don't let it go unstated.

## 2. Load/Capacity Testing

State whether this feature's expected peak load has actually been tested, not just estimated —
"we think it can handle it" is a hypothesis until a load test (or production traffic at that
scale) confirms it. For a feature replacing or fronting an existing system, compare against the
existing system's known capacity rather than starting from zero.

## 3. Chaos/Failure Testing

For a feature on a critical path, state whether its failure-mode assumptions have been exercised
deliberately (a game day, a chaos experiment, or at minimum a manual "kill this dependency and see
what happens" test) rather than only inferred from the design. A circuit breaker that's never
actually tripped in a test is unverified, not working.

## 4. Third-Party Dependency Risk

A dependency the team doesn't operate (a payment gateway, an external API, a managed cloud
service) can still be this feature's single point of failure. State what happens to this feature
when that dependency is degraded or fully down — degrade gracefully, queue and retry later, or
hard-fail with a clear error — and don't assume "they have good uptime" is a mitigation.

## 5. Graceful Degradation

If a non-critical dependency (recommendation engine, analytics, a nice-to-have enrichment call)
is unavailable, state whether the feature's core function still works with that piece missing, or
whether it fails the whole request. A core banking transaction failing because a logging
sidecar is down is a graceful-degradation gap, not an acceptable tradeoff.

## Red Flags

- An SLO exists but nobody can say what happens when it's breached
- Peak-load capacity is an estimate that's never been tested
- A circuit breaker or failover path that's coded but never been deliberately triggered
- A non-critical dependency's outage taking down the entire feature, not just its own piece
