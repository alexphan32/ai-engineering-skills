# Disaster Recovery Checklist

Load this when phase E (DISASTER RECOVERY) needs to cover more than a single data restore —
specifically a full-region/full-service loss scenario, a recurring drill cadence, or a
compliance/data-residency angle. The main skill's three steps (backup cadence, RTO/RPO, tested
restore) are the floor for any service owning persistent state; this file is for services where
losing the whole thing, not just one dataset, is a real scenario worth planning for.

## 1. Beyond Single-Dataset Restore: Full-Service Loss

A tested restore of "this table from a backup" doesn't prove the service survives losing an
entire database, availability zone, or region. State what actually happens if the primary
datastore/region is gone entirely — a documented failover to a replica/secondary region, or an
explicit acceptance that recovery means rebuilding from scratch within the stated RTO. Don't let
"we have backups" stand in for an answer to this larger question if the service's stated
availability target implies it needs to survive more than a single-table loss.

## 2. Recurring Drill Cadence

A restore tested once, a year ago, is not the same guarantee as a restore tested on a schedule —
infrastructure changes, schemas evolve, and a restore procedure that worked once can silently
break. State the drill cadence (quarterly, after major infra changes, etc.) rather than treating
"tested once" as permanently sufficient. Track the date of the last successful drill somewhere
discoverable, so "when did we last confirm this works" has an answer that isn't "I think it was
fine."

## 3. Data Residency / Compliance

If the data this service owns has a data-residency requirement (must stay in a specific
region/country) or a regulatory retention requirement, state how the DR plan respects it — a
failover to a different region can silently violate a residency requirement if nobody checks.
This is a business/legal question when unclear (`[NEEDS COMPLIANCE CLARIFICATION]`), not one to
guess at.

## 4. Dependency on External Recovery

If recovery depends on a third party (cloud provider region recovery, a vendor's own DR), state
that dependency explicitly and what the plan does if that recovery takes longer than the stated
RTO — "wait for AWS" is not a recovery plan on its own if the RTO is tighter than a provider's
typical incident resolution time.

## Red Flags

- A stated availability target that implies region survival, with no failover plan beyond backups
- "We tested the restore" with no date, and no plan to test it again
- A failover path that could move regulated data outside its required residency
- An RTO tighter than the recovery time of an external dependency the plan silently assumes will be fast
