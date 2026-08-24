# Deployment Checklist

Load this when planning phase A (DEPLOYMENT PLAN) for a change with real blast radius — a schema
migration, a behavior change on a critical path, a new external dependency, or anything touching
more than one service. A small config tweak deployed via the team's normal pipeline doesn't need
all of this; state which parts are N/A rather than skipping the file entirely.

## 1. Schema/Contract Backward Compatibility

Before deploying any change to a database schema, event schema, or API contract that has active
consumers, classify it:

```text
additive:  new optional field, new enum value nobody's switch-case rejects — safe to deploy
           in any order relative to consumers
breaking:  renamed/removed field, changed type, removed enum value, new mandatory field
           with no default — requires a coexistence period or synchronized deploy
```

A breaking change deployed without a coexistence window is a self-inflicted incident, not bad
luck — the old and new versions must be able to run side by side for however long the rollout
takes. See `.claude/skills/design/references/distributed-systems-checklist.md` §36 if this
change originated from a distributed-systems design; this section is the "confirm it's actually
safe to ship now" check.

## 2. Deploy Order for Multi-Service Changes

State the order explicitly and why: for a new message schema, the consumer that can tolerate the
new shape deploys before the producer that starts emitting it; for a new API field a client will
send, the API that accepts it deploys before the client that sends it. Getting this backwards
means the window between deploys is an active failure window, not a theoretical one.

## 3. Pre-Deploy Smoke Test

Define the specific check that confirms the new version is actually serving traffic correctly
*before* declaring the deploy done — a health check returning 200 confirms the process started,
not that the feature works. For a canary/blue-green rollout, this is what gates promotion to the
next stage; for a rolling deploy, it's what you'd check within the first few minutes.

## 4. Deploy Window / Change Freeze

State whether this deploy falls inside a change freeze (pre-holiday, high-traffic event, another
team's release window) or needs to happen during a low-traffic period because rollback would be
harder to execute safely under load. "We can deploy anytime" is a valid answer for a low-risk
change — state it, don't leave the question unasked for a risky one.

## 5. Migration Backfill Timing

If this deploy includes a data backfill (new column populated for existing rows), state whether
it runs online (no downtime, no long lock) or needs a maintenance window, and whether the backfill
is idempotent — a backfill that dies halfway through and gets re-run must not double-apply.

## Red Flags

- A breaking schema/contract change with no stated coexistence period
- Multi-service deploy order decided "however the pipeline happens to run them"
- "The deploy succeeded" used as the smoke test, instead of a feature-specific check
- A backfill script with no idempotency check, run against production for the first time
