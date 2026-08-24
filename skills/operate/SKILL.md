---
name: operate
description: >
  Use when preparing to ship reviewed code to production, or running/responding to a system
  already in production — "deploy feature X", "chuẩn bị rollback plan", "sự cố production",
  "disaster recovery plan". Covers deployment strategy, observability, reliability, and incident
  response — not making the code itself operable (that's `/implement`'s Operations Readiness
  checklist). Do NOT use for writing/reviewing code — `/implement` or `/review`.
---

## OVERVIEW

Everything that happens to a feature *after* `/review` passes and *while* it's live: deployment,
health signals, incident response, and data recovery. Distinct from the "Operations Readiness"
checklists already in `/design`/`/implement`, which make the *code* expose what it needs to (a
health endpoint, graceful shutdown, externalized config) — `/operate` is the practice built on
top: the actual deploy, the actual dashboard, the actual runbook.

**Core principle:** an incident's cost is set long before it happens — by whether a rollback path
exists, whether a dashboard would show the problem, and whether anyone knows what to do in the
first five minutes. `/operate` makes those three things true ahead of time, not improvised during
the incident.

**Prerequisite:** the code has passed `/review` (or is an existing production service). No review
yet? Route to `/review` first — deploying unreviewed code and then building a safety net around
it is backwards.

---

<HARD-GATE>
Do NOT mark a feature "ready to deploy" until:
1. A rollback path exists with an explicit trigger condition (not "we'll figure it out")
2. The specific metrics/logs/traces that would reveal this feature failing are named — not
   "we have general monitoring"
3. If the service owns persistent state: backup/restore is confirmed working for this data, not
   assumed from another service's setup

Do NOT close an incident until:
4. The immediate mitigation is in place (service stable), separate from the root cause
5. A root cause is stated, or explicitly marked unknown with a follow-up owner
6. Whether this incident reveals a missing test (`/test`) or a missing readiness gap
   (`/implement`'s checklist) is stated, even if the fix is deferred
</HARD-GATE>

**Violating any gate = violating the spirit of the skill.** Common rationalizations:

| Rationalization | Reality |
|---|---|
| "We can just redeploy the old version if something breaks" | Only a rollback path if you've confirmed the old version still works with the current data/schema — state it, don't assume it. |
| "The existing dashboards will show if this breaks" | General dashboards show general health, not this feature's specific failure mode. Name the metric that would actually catch it. |
| "It's a small change, no need for a runbook" | Small changes cause outages too, and a runbook written calmly beforehand beats one improvised mid-incident. Scope it, don't skip it. |
| "We fixed the symptom, the service is back up, we're done" | Mitigation isn't root cause. Without one, the incident recurs — state "unknown, follow-up: X" if you genuinely can't tell yet. |
| "This is an internal tool, it doesn't need a disaster recovery plan" | If it owns data anyone would miss, it needs a stated backup cadence — "acceptable to lose" is valid, but state it. |
| "It's a security incident, but the reliability runbook basically covers it" | Contain and preserve evidence before remediating — the usual "mitigate fast, root-cause later" order can destroy the evidence a forensic review needs. |
| "We'll figure out who needs to know once it's fixed" | Decide who gets a status update, and at what severity, during Triage — not as an afterthought once the incident is already resolved. |

**Red Flags — STOP and verify before proceeding:**
- Deploying with no stated rollback trigger
- "Monitoring is fine" with no metric named specific to the new feature
- Declaring an incident resolved with the cause still unknown and no follow-up owner
- A disaster recovery plan that's never been tested (backup exists, restore never tried)
- Remediating a security incident (rotating creds, wiping the affected system) before evidence is preserved

---

## WORKFLOW

Pick the phase that matches the request — these aren't always sequential.

### A. DEPLOYMENT PLAN

1. **Strategy** — rolling, blue-green, or canary, picked by blast-radius tolerance, not habit
2. **Feature flag** — gate a risky or gradual-rollout change behind a flag instead of all-or-nothing
3. **Rollback trigger** — the specific condition (error rate > X%, latency > Yms, failed health
   check) decided *before* deploying, not during
4. **Sequencing** — for a multi-service change, confirm deploy order matches compatibility
   (e.g. consumer before producer for a new message schema)

Run a **Pre-mortem** before finalizing 1-3: imagine the deploy has already failed — what caused
it, and does the rollback trigger in step 3 actually catch that failure mode?

Load `references/deployment-checklist.md` for schema/contract risk, multi-service deploy order,
or a deploy-window/freeze question.

### B. OBSERVABILITY SETUP

1. Start from what `/implement`'s Operations Readiness checklist already wired up (readiness/
   liveness endpoints, structured logs, externalized config) — this phase *uses* that, not
   re-derives it
2. Name the specific signal for this feature: one metric, log query, or trace attribute that
   would show it failing — generic "CPU/memory" dashboards don't count
3. Set an alert threshold tied to user impact, not an arbitrary round number — state what
   triggers it and who gets paged
4. Confirm the signal actually appears in the dashboard/log system before calling this done — an
   alert on a metric that's never emitted is worse than no alert; it creates false confidence

Load `references/observability-signals.md` for multi-hop correlation IDs, compliance-driven log
retention, or on-call alert routing.

### C. RELIABILITY

1. State the SLO this feature/service is expected to meet (latency, availability) if none exists
   yet — a rough number beats none
2. Verify retry/backoff/circuit-breaker behavior matches `/design`'s
   `.claude/skills/design/references/distributed-systems-checklist.md` — confirm it's *actually
   configured* in the deployed environment, not just coded
3. Identify the single point of failure, if any, and whether it's acceptable at the current
   scale tier (`.claude/skills/architecture/references/system-scale-checklist.md`)

Load `references/reliability-checklist.md` for an error-budget policy, load/chaos testing, or a
third-party dependency's failure mode.

### D. INCIDENT RESPONSE

**Runbook skeleton** (write before an incident, not during):
1. **Detection** — which alert/symptom indicates this incident
2. **Triage** — how to confirm scope and severity in under 5 minutes, and who needs a status
   update at this severity (on-call chain at minimum; add other internal teams or customer-facing
   comms per `references/incident-severity.md` if this incident's severity calls for it) — decide
   this now, not after mitigation is already underway
3. **Mitigation** — the fastest safe action to stop user impact (rollback, feature-flag kill,
   scale-up, failover) — the exact command/action, not "investigate"
4. **Root cause** — where to look first (logs/traces/recent deploys), and who to escalate to if
   unclear within a stated time box
5. **Postmortem** — blameless; root cause + timeline + owned follow-ups; feed any missing-test or
   missing-readiness finding back to `/test` or `/implement`. Use **Root Cause Analysis (5 Whys)**
   to get past the first symptom — "the service restarted" isn't a root cause until you've asked
   why enough times to reach something actionable

**Security incident** (breach, credential leak, suspicious access, data exposure) — mitigation
differs from a reliability incident and the runbook should say so explicitly rather than reusing
the generic steps above verbatim: contain first (revoke/rotate the exposed credential, isolate
the affected system/account) before investigating further; preserve evidence (logs, affected
rows/requests, access records) before remediating — cleanup can destroy what a forensic review
or compliance report would need; and treat notification obligations (affected users, compliance/
legal) as part of Triage, not an afterthought discovered during Postmortem.

**During a live incident:** follow the runbook if one exists; otherwise build the five sections
live, in order — don't skip straight to root-cause hunting while the service is still down.

Load `references/incident-severity.md` for severity classification, a dedicated incident
commander, or stakeholder communication beyond the on-call chain.

### E. DISASTER RECOVERY

Only for services owning persistent state:
1. State the backup cadence and where backups live
2. State RTO (how fast recovery must happen) and RPO (how much data loss is acceptable), even
   informally — e.g. "≤1 hour data loss acceptable, restore within 4 hours"
3. Confirm restore has actually been tested, not just backup — an untested backup is a hope, not
   a plan

Load `references/disaster-recovery-checklist.md` for full-region/full-service loss, a recurring
drill cadence, or a data-residency/compliance question.

---

## REFERENCES

Each goes one level deeper than its workflow phase — load only when the phase's own steps aren't
enough (a lean deploy or small incident usually doesn't need them):

| File | Load when |
|---|---|
| `references/deployment-checklist.md` | Schema/contract compatibility, multi-service deploy order, or a change-freeze question |
| `references/observability-signals.md` | Multi-hop correlation IDs, log retention/compliance, or on-call alert routing |
| `references/reliability-checklist.md` | Error-budget policy, load/chaos testing, or third-party dependency risk |
| `references/incident-severity.md` | Severity classification, incident commander, or stakeholder communication |
| `references/disaster-recovery-checklist.md` | Full-region loss, recurring DR drills, or data-residency/compliance |

---

## RELATIONSHIP TO OTHER SKILLS

| Skill | How it connects |
|---|---|
| `/review` | Must pass before `/operate`'s deployment phase begins |
| `/implement` | Its Operations Readiness checklist is the code-level input this skill builds practice on top of |
| `/design` | Distributed-systems and scale-tier checklists inform reliability targets and SLOs |
| `/test` | Incident postmortems that reveal a coverage gap route back here |
