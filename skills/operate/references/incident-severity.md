# Incident Severity & Communication

Load this during phase D (INCIDENT RESPONSE) for an incident big enough to need a severity call,
a dedicated incident commander, or communication beyond the on-call engineer's own escalation
chain — most small/contained incidents can follow the runbook skeleton in the main skill without
this file.

## 1. Severity Classification

Classify the incident as soon as scope is known (end of Triage), and let the severity drive how
much of the rest of this file applies:

```text
SEV1 — full outage or data-integrity risk, all hands, incident commander required,
       external communication likely needed
SEV2 — significant degradation or a subset of users/functionality affected,
       on-call + relevant team, internal stakeholders notified
SEV3 — minor, contained impact, on-call handles it solo, no broader notification needed
```

State the severity in the incident record, and re-classify if scope changes — a SEV3 that turns
out to affect payments processing becomes a SEV1, not a SEV3 that's "taking a while."

## 2. Incident Commander

For SEV1 (and SEV2 at the team's discretion), name one person as incident commander — the person
coordinating response, not necessarily the person fixing the bug. Splitting these roles matters:
the engineer debugging shouldn't also be the one fielding status-update requests and deciding
when to escalate further, because both suffer when one person tries to do both under pressure.

## 3. Stakeholder Communication

State who needs to know while the incident is live, separate from who's fixing it:

```text
internal:  affected team(s), support/customer-success if customers are calling in, leadership
           for SEV1
external:  a status page update, direct customer communication — only if customer-visible impact
```

Decide the cadence (e.g. "update every 30 minutes until resolved") up front rather than during
the incident — silence during an outage erodes trust faster than an update saying "still
investigating."

## 4. Timeline Discipline

Keep a timestamped log of what was observed and done as the incident happens, not reconstructed
afterward from memory — this is the raw material the postmortem's timeline section needs, and
memory reconstructed after the fact reliably drops the details (an early symptom that was
dismissed, an action that didn't help) that matter most for root-causing.

## Red Flags

- Severity never explicitly stated or re-evaluated as scope changes
- One person simultaneously debugging and fielding every stakeholder question during a SEV1
- No stakeholder update sent for over an hour during a customer-visible outage
- A postmortem timeline reconstructed entirely from memory after the fact
