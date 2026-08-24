# Concurrency Testing

Load this when the change involves multiple threads/processes/requests touching the same shared
state at the same time — parallel workers, a counter or balance updated from more than one
request, an optimistic-lock retry path, or an idempotency check meant to hold under simultaneous
duplicate requests. This is distinct from `failure-testing.md`: concurrency testing is about
**simultaneity** (two things happening at once), failure testing is about **a single flow breaking
partway through** (crash, timeout, lost message). A feature can need either, both, or neither.

**Core principle:** a race condition doesn't show up by calling the code twice in sequence — it
shows up when two calls genuinely overlap in time. A concurrency test that just calls the function
twice in a `for` loop proves nothing about what happens when both calls are mid-execution
simultaneously; it has to force the overlap.

## 1. Force the overlap, don't hope for it [MUST]

```text
vulnerable: for i in range(2): reserve_seat(seat_id)   # sequential, second call sees first's result
required:   fire N goroutines/threads at reserve_seat(seat_id) simultaneously via a barrier/
            countdown-latch/WaitGroup, so all N calls are in-flight before any completes
```

```go
var wg sync.WaitGroup
start := make(chan struct{})
results := make([]error, 10)
for i := 0; i < 10; i++ {
    wg.Add(1)
    go func(i int) {
        defer wg.Done()
        <-start                       // all goroutines block here until released together
        results[i] = reserveSeat(seatID)
    }(i)
}
close(start)                          // release all at once — forces real overlap
wg.Wait()
assertExactlyOneSucceeded(results)    // the invariant under test
```

## 2. Assert the invariant, not the interleaving [MUST]

You generally can't control or assert the exact order the OS schedules threads in, and shouldn't
try to — assert the outcome that must hold regardless of order: exactly one of N concurrent
reservations for the last seat succeeds, a balance never goes negative, a counter incremented N
times concurrently ends up at exactly N (not less, from a lost update).

## 3. Test idempotency under real concurrency, not just repetition [MUST for idempotent endpoints]

```text
vulnerable: call the idempotent endpoint twice, sequentially, assert same result
required:   call it twice concurrently with the same idempotency key, assert the side effect
            (charge, row insert, email sent) happened exactly once — not once per call racing past
            a check-then-act gap
```

A check-then-act idempotency implementation (`if not exists: create`) can pass a sequential test
and still double-create under concurrency, because both calls can pass the `exists` check before
either finishes the `create` — the concurrent version of the test is what catches this gap.

## 4. Use the language's race detector, not just manual review [SHOULD]

```bash
go test -race ./...                         # Go
mvn test -Djcstress.mode=default            # Java, via jcstress for stress-level concurrency tests
python -m pytest --forked                   # process isolation as a poor-man's substitute where no detector exists
```

A race detector catches unsynchronized shared-memory access that a purely behavioral assertion can
miss (the test happens to pass this run, but the access pattern is still unsafe).

## 5. Re-run to catch scheduler-dependent flake [MUST]

A concurrency test that passes once may only have gotten lucky with the scheduler — re-run it
10-20 times (or use a stress-testing harness that does this automatically) before trusting a green
result. If it fails 1 time in 15, that's a real bug at a low probability, not a flaky test to
retry past.

## Verify

```bash
# confirm the test actually launches concurrent work, not a sequential loop pretending to
grep -n "go func\|Thread(\|WaitGroup\|CountDownLatch\|asyncio.gather\|Promise.all" <new_test_file>

# confirm a barrier/gate exists to force overlap, not just concurrent-looking code that still runs sequentially in practice
grep -n "sync.WaitGroup\|CountDownLatch\|Barrier\|start := make(chan" <new_test_file>
```
