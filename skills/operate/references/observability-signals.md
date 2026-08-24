# Observability Signals Checklist

Load this when phase B (OBSERVABILITY SETUP) needs more than "name one metric" — specifically for
a feature that spans multiple services/hops, has compliance-driven log retention requirements, or
needs its alert routed to a specific on-call rotation rather than a generic channel.

## 1. Correlation Across Hops

A signal that only exists inside one service is only half useful once a feature spans a network
call. State that `correlationId`/`traceId` propagates through every hop this feature touches
(API → Service A → queue → Service B → external system) and that logs at each hop include it —
otherwise an incident gets "debugged" by grepping for a timestamp and guessing, instead of
following one ID end to end. `.claude/skills/design/references/distributed-systems-checklist.md`
§22 covers the design-time version of this; this is the "confirm it's actually emitted in
production" check.

## 2. Business vs. Technical Signals

Classify each signal named in phase B as one of:

```text
business:   did the thing the system is for actually happen — orders.failed.total,
            payment.declined.total
technical:  is the infrastructure healthy — request.duration.p99, queue.consumer.lag,
            db.connection.pool.exhausted
```

A dashboard built entirely from technical signals can look green while the business outcome is
failing (e.g. payments silently declining at 100% while latency and error rate look normal) —
make sure at least one business signal exists for anything user-facing.

## 3. Log Retention

State how long logs for this feature are retained, and whether that meets any compliance or
audit requirement that applies to the data involved (financial transactions, PII access). "Logs
are retained forever" and "logs are retained for 7 days" are both valid answers — an unstated
default that nobody chose deliberately isn't.

## 4. Alert Routing

An alert that pages doesn't help if it pages the wrong rotation, or a channel nobody watches at
3am. State which on-call rotation/team owns the alert, and confirm the routing was actually
tested (a test page reached a real human), not just configured and assumed to work.

## 5. Signal Verification

Before calling phase B done, confirm each named signal actually appears in the dashboard/log
system under real or synthetic traffic — an alert wired to a metric that's never emitted creates
false confidence, which is worse than no alert (this is also stated as a hard gate in the main
skill; this file is where you go to check it thoroughly for a multi-hop feature).

## Red Flags

- A multi-hop feature with no propagated correlation ID
- Only technical metrics named for a user-facing, revenue-affecting feature
- An alert configured but never test-paged to confirm it reaches a real person
- Log retention left as "whatever the default is" for data with a known compliance requirement
