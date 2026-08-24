# Contract Testing

Load this when the change calls, or is called by, an independently deployed service — a
different repo, a different deploy cadence, a team boundary. This is a different failure mode
than integration testing: integration testing verifies your code and your database agree with
each other; contract testing verifies your service and *someone else's* service still agree on
the shape of a request/response after either side deploys independently.

**Core principle:** a contract test must fail the moment either side changes the interaction shape
— field renamed, field removed, type changed, new required field added — without needing the two
real services running together. If your "contract test" only passes or fails based on both
services being up and reachable, it's an integration or e2e test wearing a contract test's name.

## 1. Pick a strategy proportional to the risk [MUST decide, not skip]

| Strategy | What it catches | When it's enough |
|---|---|---|
| Consumer-driven contract (Pact, Spring Cloud Contract) | Consumer's actual expectations vs. provider's actual behavior, verified independently on each side | Two services under active co-development, breaking changes are a real risk |
| Schema diff (OpenAPI/JSON Schema/protobuf backward-compat check in CI) | Structural breaking changes (removed field, changed type, removed enum value) | A stable, well-documented API where consumer expectations rarely go beyond the schema |
| Recorded-response replay (VCR-style cassette against the real API, replayed offline) | Drift between what you assumed the API returns and what it now returns | Third-party API you don't control and can't run a consumer-driven pact against |

Don't default to "we'll just be careful" — that's not a test, it's a hope. State which strategy
applies and why if the project doesn't already have one in place.

## 2. Consumer-driven: write the expectation from the consumer's actual usage [MUST]

```text
consumer side test:
  given a request matching {method: GET, path: /accounts/{id}}
  expect a response matching {id: number, balance: number, status: "ACTIVE"|"FROZEN"|"CLOSED"}
  → publishes this as a contract (pact file) the provider must verify against

provider side test:
  replays every published consumer contract against the real provider implementation
  → fails if the real response no longer matches what any consumer expects
```

The consumer defines the contract from what it actually reads off the response — not from the
provider's full schema — so an unused field changing shape doesn't fail a contract that never
depended on it, while a field an existing consumer does depend on always does.

## 3. Wire provider verification into CI on both sides [MUST]

A contract test that only runs locally, or only runs when someone remembers to, doesn't prevent
the breaking deploy it exists to catch. The provider's CI must verify against the latest published
contracts before that provider can deploy; a broken verification blocks the deploy, it doesn't
just log a warning.

## 4. Version the contract when a break is intentional [SHOULD]

When an intentional breaking change ships (e.g. a new required field), version the endpoint or the
message schema (`/v2/...`, an event schema version field) rather than silently changing `/v1/...`
underneath existing consumers — see the "Event Schema Versioning" item in
`.claude/skills/design/references/distributed-systems-checklist.md` for the design-time version of
this same rule.

## Verify

```bash
# a contract test that hits the real network end-to-end is an e2e test mislabeled — check for it
grep -n "http://\|https://" <new_contract_test_file>   # should be absent or point at a stub/pact broker, not a live env

# confirm the provider-side verification step actually runs in CI, not just locally
grep -rn "pact.*verify\|contract.*verify" <ci_config_file>
```

If the test only fails when you manually change the *client* code, it isn't catching provider
drift — deliberately break the provider's response shape locally and confirm the test goes red.
