# Performance Testing

Load this when the SDS/design flags a Performance/scale tier ≥2 (see
`.claude/skills/architecture/references/system-scale-checklist.md`), or the change adds a
loop-over-query, a list/export endpoint, or a path already known to be high-traffic.

**Core principle:** "faster than before" is not a pass/fail criterion — it has no threshold, so it
can never fail, which means it isn't actually a test. A performance test asserts against a stated
numeric budget (from the SDS's non-functional requirements, an SLA, or an explicit ask to the user
if neither exists) — p95 latency under 300ms at 100 rps, or it fails.

## 1. Pick the test type that matches the question being asked [MUST decide, not skip]

| Type | Question it answers |
|---|---|
| Load test | Does the system meet its latency/throughput budget at *expected* traffic? |
| Stress test | Where does the system actually break, and how does it fail (graceful degradation vs. cascading failure)? |
| Spike test | Does a sudden traffic burst (marketing push, retry storm) survive without falling over? |
| Soak test | Does the system stay healthy over hours (memory leak, connection pool exhaustion, disk fill) rather than just a 5-minute burst? |

A single "load test" run at expected traffic says nothing about what happens at 3x that traffic or
after six hours — pick the type that answers the question the SDS/risk actually raises.

## 2. State the budget before running anything [MUST]

```text
vulnerable: "run the load test and see how it does"
required:   "p95 < 300ms and error rate < 0.1% at 200 rps sustained for 10 minutes" — from the
            SDS's NFRs, or asked of the user/stakeholder if the SDS doesn't state one
```

Without a stated budget, any result can be rationalized as acceptable after the fact — the budget
has to exist before the run so the run can actually fail it.

## 3. Measure percentiles and error rate, not just the average [MUST]

An average latency can look fine while p99 users experience multi-second waits — averages hide the
tail that actually generates support tickets. Capture at minimum: p50, p95, p99 latency,
throughput (successful requests/sec), and error rate; for a stateful service also capture resource
usage (CPU, memory, DB connection pool saturation, queue depth) so a failure mode has a cause, not
just a symptom.

## 4. Isolate what's actually being measured [SHOULD]

```text
vulnerable: load test hits a cold cache, cold JIT, cold connection pool → numbers reflect warmup,
            not steady-state behavior
required:   a warm-up period before the measurement window starts; report only the steady-state
            window
```

Also verify the test environment is representative of production scale (DB size, index presence,
data distribution) — a load test against a near-empty dev database will pass regardless of an
`N+1` query or a missing index that only shows up at production data volume.

## 5. Use the project's existing tool, don't introduce a new one without reason [SHOULD]

Stack-agnostic options exist for most environments (k6, Locust, Gatling, JMeter, autocannon) —
check the project's CLAUDE.md or existing test scripts for a convention already in place before
picking a new tool; a load-testing tool no one else on the team knows how to run doesn't get
re-run after the first time.

```javascript
// example k6 script skeleton — adapt to the project's actual tool
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 50,            // concurrent virtual users
  duration: '10m',
  thresholds: {
    http_req_duration: ['p(95)<300'],   // the stated budget, enforced as a pass/fail gate
    http_req_failed: ['rate<0.001'],
  },
};

export default function () {
  const res = http.get('https://target/endpoint');
  check(res, { 'status is 200': (r) => r.status === 200 });
}
```

## Verify

```bash
# confirm the test config actually encodes a threshold, not just a report
grep -n "threshold\|p(9\|p95\|p99" <load_test_config>
```

Re-run the same test twice back to back — if results vary wildly between runs with no code change,
the environment has noise (shared infra, insufficient warm-up) that needs controlling before the
numbers can be trusted as a gate.
