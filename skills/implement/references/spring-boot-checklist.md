# Implement Skill — Spring Boot Reference Material

> Load this when implementing in a Spring Boot (Java) codebase. It complements
> `verification-checklist.md` — that file's language-agnostic checklist (linting, testing,
> secrets scan, docs) still applies; this file adds the traps specific to this stack.
>
> **First, verify the Spring Boot major version** (`pom.xml`/`build.gradle`). Boot 3.x requires
> Java 17+ and moved the entire `javax.*` namespace to `jakarta.*` (`javax.persistence.Entity` →
> `jakarta.persistence.Entity`, `javax.validation.constraints.*` → `jakarta.validation.constraints.*`).
> Spring Security also dropped `WebSecurityConfigurerAdapter` in favor of a `SecurityFilterChain`
> `@Bean` with the lambda DSL. Writing code from pre-Boot-3 training data against a Boot 3 project
> (or vice versa) produces imports that don't compile — check the version before writing the
> first import line.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ Returning the JPA entity directly from a controller

```java
@GetMapping("/{id}")
public ResponseEntity<User> getById(@PathVariable Long id) {
    return ResponseEntity.ok(userRepository.findById(id).orElseThrow());
    // leaks every column (including passwordHash), and any lazy-loaded
    // association throws LazyInitializationException once Jackson tries
    // to serialize it outside the transaction
}
```

### ✅ Mapping to a Response DTO

```java
@GetMapping("/{id}")
public ResponseEntity<UserResponse> getById(@PathVariable Long id) {
    User user = userRepository.findById(id)
        .orElseThrow(() -> new UserNotFoundException(id));
    return ResponseEntity.ok(UserResponse.from(user));
}

public record UserResponse(Long id, String email, Instant createdAt) {
    public static UserResponse from(User u) {
        return new UserResponse(u.getId(), u.getEmail(), u.getCreatedAt());
    }
}
```

**Why this is better:** the response shape is explicit and stable regardless of what fields get
added to the entity later, sensitive columns never have a path to the wire, and there's no
lazy-association serialization surprise.

---

### ❌ Unconditional write `@Transactional`, or none at all

```java
@Service
public class OrderService {
    public Order placeOrder(OrderRequest req) {
        // no @Transactional — a partial failure between the two saves below
        // leaves the DB in an inconsistent state
        var order = orderRepository.save(new Order(req));
        inventoryRepository.decrementStock(req.productId(), req.qty());
        return order;
    }
}
```

### ✅ Explicit transaction boundary around the multi-step write

```java
@Service
@Transactional(readOnly = true) // default for the class — most methods just read
public class OrderService {

    @Transactional // override: this method writes, needs a real transaction
    public Order placeOrder(OrderRequest req) {
        var order = orderRepository.save(new Order(req));
        inventoryRepository.decrementStock(req.productId(), req.qty());
        return order; // both writes commit or roll back together
    }
}
```

**Why this is better:** `@Transactional` at the class level as `readOnly = true` documents intent
for the common case (queries) and lets Hibernate skip dirty-checking overhead on them; the
override on the write method ensures the multi-step mutation is atomic.

---

### ❌ String-concatenated JPQL

```java
@Query("SELECT u FROM User u WHERE u.email = '" + email + "'")
// classic injection vector the moment `email` comes from user input
```

### ✅ Parameterized query

```java
@Query("SELECT u FROM User u WHERE u.email = :email")
Optional<User> findByEmail(@Param("email") String email);

// or simply, Spring Data derives this automatically:
Optional<User> findByEmail(String email);
```

---

### ❌ N+1 from an unguarded list endpoint

```java
@GetMapping
public List<OrderResponse> list() {
    return orderRepository.findAll().stream() // each order.getCustomer() below
        .map(o -> new OrderResponse(o, o.getCustomer())) // triggers a separate SELECT
        .toList();
}
```

### ✅ Fetch the relation in one query

```java
@EntityGraph(attributePaths = {"customer"})
List<Order> findAll();
```

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — Spring Boot specifics slot in as follows:

### **P0 - Critical**
- `@Valid`/Bean Validation on every `@RequestBody` — the DTO boundary is the trust boundary
- `@PreAuthorize`/security matcher present on every endpoint that isn't intentionally public
- Response DTOs used everywhere — no JPA entity serialized directly to a client
- No JPQL/native query built via string concatenation

### **P1 - High**
- `@Transactional` boundaries correct (read-only default, explicit override on writes; multi-step writes atomic)
- Exception → HTTP status mapping via `@RestControllerAdvice`/`@ExceptionHandler`, not ad-hoc `try/catch` per controller method
- `createdAt`/`updatedAt` populated consistently (via `@PrePersist`/`@PreUpdate` or JPA Auditing — not both, pick one)

### **P2 - Medium**
- Unit tests for service logic (JUnit5 + Mockito), `@WebMvcTest` for controllers, `@DataJpaTest` for custom repository queries
- Javadoc/comments on non-obvious business rules

### **P3 - Low**
- `@EntityGraph`/`JOIN FETCH` tuning to eliminate N+1 on list endpoints
- Caching (`@Cacheable`/`@CacheEvict`) for hot read paths

---

## VERIFICATION CHECKLIST (Spring Boot additions)

Run these in addition to the general checklist:

### 1. Code Quality
```bash
mvn -q compile                 # or: ./gradlew compileJava
mvn -q checkstyle:check         # if configured — otherwise skip
```
- [ ] No `javax.*` imports in a Boot 3 project (or `jakarta.*` in a Boot 2 project) — check `pom.xml`/`build.gradle` version if unsure

### 2. Correctness
- [ ] Every `@RequestBody` parameter is annotated `@Valid`
- [ ] Every service method's `@Transactional(readOnly = ...)` matches whether it actually writes
- [ ] Every controller method returns a DTO, never an entity

### 3. Security
- [ ] Every non-public endpoint has an explicit auth/role check (`@PreAuthorize` or a `SecurityFilterChain` matcher) — verified by reading the actual annotation/config, not assumed from the endpoint's name
- [ ] Every endpoint taking a resource id also checks ownership in the service layer, not just the role — IDOR check, not just an authentication check
- [ ] No sensitive field (password hash, token) present on any Response DTO record
- [ ] No `@Query`/native query built via string concatenation with a variable
- [ ] `@Transactional` boundary around any read-modify-write on balance/payment/approval matches the locking strategy the SDS named (`@Lock`, `@Version`, or explicit pessimistic read) — not just `readOnly = false`
- [ ] Auth/OTP/payment endpoints have a rate-limit filter/bucket applied (Bucket4j, gateway-level, or equivalent) if the SDS specified one
- [ ] `GlobalExceptionHandler`'s catch-all never lets an unhandled exception's message/stack trace reach the client — verify with a request that intentionally triggers an uncaught exception in a test
- [ ] Security-sensitive actions (LOGIN/CREATE/UPDATE/DELETE/APPROVE/REJECT/TRANSFER/CHANGE_PERMISSION) emit an audit log entry if the SDS required one

```bash
git grep -iE "(password|secret|api_key|token)\s*=" -- '*.java'
git grep -inE "log\.(info|debug|warn|error)\(.*\b(password|token|otp)\b" -- '*.java'
```

Full checklist (SSRF, file upload, secrets storage, CORS/CSRF posture, dependency scan, mandatory
security test cases): `references/security-implementation-checklist.md`.

### 4. Testing
```bash
mvn test                        # or: ./gradlew test
```
- [ ] Service tests mock the repository (`@ExtendWith(MockitoExtension.class)`), not a real DB
- [ ] Repository tests (`@DataJpaTest`) verify custom `@Query`/`@EntityGraph` behavior against a real (embedded/Testcontainers) DB
- [ ] Controller tests (`@WebMvcTest` + `MockMvc`) cover: success, validation failure (400), missing auth (401), insufficient role (403), IDOR (authenticated user requesting another user's resource id → 403/404), expired/invalid JWT

### 5. Performance
- [ ] List endpoints that render a relation use `@EntityGraph`/`JOIN FETCH`, not a loop that lazy-loads per row
- [ ] Unbounded list endpoints use `Pageable`/`Page<T>`, not `findAll()`
- [ ] No `@Transactional` method calls `RestTemplate`/`WebClient`/Feign or does a blocking Kafka send inside its boundary — read the actual method body, not just the annotation
- [ ] `RestTemplate`/`WebClient`/Feign client config has an explicit connect/read timeout — not the library default
- [ ] `@Retryable` (if present) has `maxAttempts` + `@Backoff(delay=..., multiplier=..., random=true)` and excludes 4xx/validation exceptions
- [ ] HikariCP `maximumPoolSize` is explicit config, not left at the driver default

```bash
# query-in-loop candidates
grep -n -B2 "repository\.\|Repository\." -- '*.java' | grep -B2 "for (\|while ("
```

Full checklist (connection-pool sizing math, circuit breaker/bulkhead, cache stampede, memory
streaming, anti-pattern sweep): `references/performance-implementation-checklist.md`.

### 6. Distributed & Async (if this module publishes/consumes Kafka messages or calls an external system)
- [ ] Bare `@Async` is not used for a business-critical operation that must survive a crash — a durable queue or persisted job backs it instead
- [ ] Every `@KafkaListener` checks a `processedEventRepository`/equivalent for the event ID before applying the effect, and marks processed in the same `@Transactional` boundary as the business update
- [ ] A DB write that must be atomic with a Kafka publish goes through an outbox table in the same transaction, not an inline `kafkaTemplate.send(...)` outside it
- [ ] Any entity with a status field is only mutated through a transition method — grep for `.setStatus(` called from outside the entity/state-machine class
- [ ] A `TimeoutException` calling an external system (Core Banking, payment gateway) sets the record to `UNKNOWN`/`PENDING`, never directly to a terminal failure state

```bash
grep -rn "@Async" -- '*.java'
grep -n "\.setStatus(" -- '*.java'
```

Full checklist (Saga/compensation, reconciliation jobs, DLQ payload shape, mandatory
failure-scenario tests): `references/distributed-systems-implementation-checklist.md`.

---

## TROUBLESHOOTING

**`LazyInitializationException` when serializing a response:**
The entity is being returned/serialized outside its persistence context (session already
closed). Map to a DTO inside the `@Transactional` service method instead of returning the
entity and mapping later.

**A previously-passing import stopped compiling after a dependency bump:**
Check whether the project crossed the Boot 2 → 3 boundary — `javax.*` → `jakarta.*` is the
most common cause, followed by the `WebSecurityConfigurerAdapter` removal.

**A write "succeeds" but a related row is missing/stale:**
Check the `@Transactional` boundary — if the method that performs both writes isn't itself
transactional (or is `readOnly = true`), a failure partway through won't roll back the first write.

**Tests pass individually but fail when run together:**
Look for state leaking across `@DataJpaTest`/`@SpringBootTest` classes — usually a missing
`@Transactional` rollback (test-scoped transactions roll back by default; a test that manually
commits or uses `@Commit` breaks that isolation for tests that run after it).
