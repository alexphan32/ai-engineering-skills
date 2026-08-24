# SDS Template D: Spring Boot / REST API (Java)

> Reference for `design` skill — loaded on demand when creating MODE D SDS documents.
>
> **First, verify the Spring Boot major version.** Spring Boot 3.x requires Java 17+ and moved
> the entire javax.* namespace to jakarta.* (`javax.persistence.Entity` → `jakarta.persistence.Entity`,
> same for `javax.validation` → `jakarta.validation`). Spring Security's config style also changed
> from `WebSecurityConfigurerAdapter` (removed in Security 5.7+/Spring Boot 3) to a `SecurityFilterChain`
> `@Bean` with the lambda DSL. Check `pom.xml`/`build.gradle` for the actual `spring-boot` version
> before drafting import statements or security config from training-data memory — this is the
> single most common source of dead-on-arrival generated code for this stack.

---

## TEMPLATE D: Spring Boot / REST API SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: {tech_stack — discover exact Spring Boot / Java version from pom.xml or build.gradle}

---

## 1. Module Overview

### 1.1 Description
[Describe what this module does in the system]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Module Type**: [Core Domain / Supporting / Infrastructure]
**Scale Tier**: [Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed — one-line reason, see `.claude/skills/architecture/references/system-scale-checklist.md`]

### 1.3 Package Layout
```
src/main/java/{basePackage}/{module}/
├── domain/{Entity}.java                  # JPA entity — persistence + minimal invariants only
├── repository/{Entity}Repository.java    # Spring Data JPA interface
├── service/{Entity}Service.java          # Service interface
├── service/impl/{Entity}ServiceImpl.java # @Service, @Transactional boundaries
├── controller/{Entity}Controller.java    # @RestController
├── dto/{Entity}Request.java              # Request record + Bean Validation
├── dto/{Entity}Response.java             # Response record — never the entity itself
├── mapper/{Entity}Mapper.java            # Entity <-> DTO (MapStruct or manual static methods)
└── exception/{Entity}NotFoundException.java
```

**Entities**: [List JPA entities]
**APIs**: [List main endpoints]
**Dependencies**: [M-01 IAM for auth, etc.]

---

## 2. Data Model

### 2.1 JPA Entity: [EntityName]

```java
// src/main/java/{basePackage}/{module}/domain/[Entity].java
// Traceability: SDS M-XX Section 2.1
package {basePackage}.{module}.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "[table_name]", indexes = {
    @Index(name = "idx_[field]", columnList = "[field]", unique = true)
})
public class [EntityName] {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "[field]", nullable = false)
    private String [field];

    @Column(nullable = false)
    private boolean active = true;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @PrePersist
    void onCreate() { createdAt = updatedAt = Instant.now(); }

    @PreUpdate
    void onUpdate() { updatedAt = Instant.now(); }

    // getters/setters or Lombok @Getter/@Setter — match project convention (check CLAUDE.md)
}
```

**Field Definitions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Long | Yes (generated) | Primary key |
| [field] | String | Yes | [description] |
| active | boolean | Yes | Soft delete flag |
| createdAt | Instant | Yes | Creation timestamp |
| updatedAt | Instant | Yes | Last update timestamp |

**Optimistic locking** (if concurrent writes are a concern): add `@Version private Long version;`.

### 2.2 Table Design

| Column | Type | Constraint |
|--------|------|------------|
| id | BIGINT | PRIMARY KEY |
| [field] | VARCHAR(255) | UNIQUE, NOT NULL |
| active | BOOLEAN | NOT NULL DEFAULT true |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

**Indexes:**

| Index | Columns | Type | Reason |
|-------|---------|------|--------|
| `idx_[field]` | `[field]` | Unique | Frequent lookup |
| `idx_active_created` | `active, created_at DESC` | Compound | List query with sort |

### 2.3 Caching (if applicable)

| Cache Name | Key | TTL | Eviction |
|------------|-----|-----|----------|
| `{module}Cache` | `#id` | 15 min | `@CacheEvict` on update/delete |

---

## 3. Domain Interfaces

### 3.1 Repository Interface

```java
// src/main/java/{basePackage}/{module}/repository/[Entity]Repository.java
package {basePackage}.{module}.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.EntityGraph;
import java.util.Optional;

public interface [Entity]Repository extends JpaRepository<[Entity], Long> {
    Optional<[Entity]> findByField(String field);
    Page<[Entity]> findByActiveTrue(Pageable pageable);

    // Use @EntityGraph or JOIN FETCH to avoid N+1 when a list query needs a relation eagerly
    @EntityGraph(attributePaths = {"[relation]"})
    Optional<[Entity]> findWithRelationById(Long id);
}
```

### 3.2 Service Interface

```java
// src/main/java/{basePackage}/{module}/service/[Entity]Service.java
package {basePackage}.{module}.service;

public interface [Entity]Service {
    [Entity]Response get(Long id);
    Page<[Entity]Response> list(Pageable pageable);
    [Entity]Response create([Entity]Request request);
}
```

### 3.3 Domain Exceptions

```java
// src/main/java/{basePackage}/{module}/exception/[Entity]NotFoundException.java
public class [Entity]NotFoundException extends RuntimeException {
    public [Entity]NotFoundException(Long id) {
        super("[Entity] not found: " + id);
    }
}

public class [Entity]ConflictException extends RuntimeException { /* duplicate field */ }
```

---

## 4. API Specification

### 4.1 Endpoints Overview

| Method | Path | Auth | Description |
|--------|------|------|--------------|
| GET | /api/v1/[resource] | JWT | List resources (paginated) |
| GET | /api/v1/[resource]/{id} | JWT | Get by ID |
| POST | /api/v1/[resource] | JWT (ROLE) | Create resource |

### 4.2 Request/Response DTOs

```java
// src/main/java/{basePackage}/{module}/dto/[Entity]Request.java
package {basePackage}.{module}.dto;

import jakarta.validation.constraints.*;

public record [Entity]Request(
    @NotBlank @Size(min = 1, max = 255) String field
) {}

// src/main/java/{basePackage}/{module}/dto/[Entity]Response.java
public record [Entity]Response(
    Long id,
    String field,
    Instant createdAt
) {
    public static [Entity]Response from([Entity] e) {
        return new [Entity]Response(e.getId(), e.getField(), e.getCreatedAt());
    }
}
```

### 4.3 API Details

#### GET /api/v1/[resource]
**Purpose**: [description]
**Auth**: JWT required, role: [ROLE]
**Query Params**: `page` (default: 0), `size` (default: 20, max: 100) — Spring `Pageable` via `@PageableDefault`
**Response**: `Page<[Entity]Response>` → `{ "content": [...], "totalElements": N, "totalPages": N }`
**HTTP Status**: 200 OK

#### POST /api/v1/[resource]
**Purpose**: [description]
**Auth**: JWT required, role: [ROLE]
**Request Body**: `[Entity]Request` (validated via `@Valid`)
**Response**: `[Entity]Response`
**HTTP Status**: 201 Created | 400 Bad Request | 409 Conflict

---

## 5. Service Layer Design

### 5.1 Use Cases List

| Operation | Method | SDS Reference |
|-----------|--------|----------------|
| Get[Entity] | `service.get(id)` | Section 5.2 |
| Create[Entity] | `service.create(request)` | Section 5.3 |

### 5.2 Create[Entity] Flow

```java
// src/main/java/{basePackage}/{module}/service/impl/[Entity]ServiceImpl.java
// Traceability: SDS M-XX Section 5.2 Create[Entity] Flow
@Service
public class [Entity]ServiceImpl implements [Entity]Service {

    private final [Entity]Repository repository;

    @Transactional
    @Override
    public [Entity]Response create([Entity]Request request) {
        repository.findByField(request.field()).ifPresent(e -> {
            throw new [Entity]ConflictException(request.field());
        });
        [Entity] entity = new [Entity]();
        entity.setField(request.field());
        return [Entity]Response.from(repository.save(entity));
    }
}
```

**Flow:**
```
1. Validate input (Bean Validation already ran via @Valid before this point)
2. Check uniqueness via repository
3. Map request -> entity
4. Save via repository (inside @Transactional boundary)
5. Evict/update relevant cache
6. Map entity -> response DTO, return
```

**Transaction boundary note:** class-level `@Transactional(readOnly = true)` for read services,
override per-method `@Transactional` for writes — state which methods are read-only vs.
read-write here so the implementer doesn't default every method to a write transaction.

---

## 6. Controller Design

```java
// src/main/java/{basePackage}/{module}/controller/[Entity]Controller.java
package {basePackage}.{module}.controller;

@RestController
@RequestMapping("/api/v1/[resource]")
public class [Entity]Controller {

    private final [Entity]Service service;

    @GetMapping("/{id}")
    public ResponseEntity<[Entity]Response> getById(@PathVariable Long id) {
        return ResponseEntity.ok(service.get(id));
    }

    @PostMapping
    @PreAuthorize("hasRole('[ROLE]')")
    public ResponseEntity<[Entity]Response> create(@Valid @RequestBody [Entity]Request request) {
        var created = service.create(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }
}
```

---

## 7. Security Design

### 7.1 Authentication Requirements

| Endpoint | Auth | Role |
|----------|------|------|
| GET /api/v1/[resource] | Optional | - |
| GET /api/v1/[resource]/{id} | Required (JWT) | Any |
| POST /api/v1/[resource] | Required (JWT) | [ROLE] |

### 7.2 Authorization

- Method security: `@PreAuthorize("hasRole('[ROLE]')")` on the controller method, or a
  `SecurityFilterChain` `@Bean` matcher (`.requestMatchers("/api/v1/[resource]/**").hasRole(...)`) —
  state which mechanism this SDS assumes, since mixing both without care hides where the actual
  gate lives.
- Ownership checks (resource belongs to the authenticated principal) happen in the **service**
  layer, not the controller — the controller only extracts the principal, the service enforces
  the rule so it's covered by service unit tests.

### 7.3 Data Security

- **Sensitive fields**: [fields] → never present on the Response DTO record at all (not just
  `@JsonIgnore`'d — leaving them off the record is the only guarantee against accidental exposure)
- **Input sanitization**: Bean Validation at the DTO boundary; trim/normalize in the mapper, not the entity
- **SQL injection**: Spring Data JPA / JPQL parameter binding only — never string-concatenate into `@Query`
- **Mass assignment**: the Request DTO's fields are the only fields a client can set — never bind
  a client-supplied DTO straight onto an existing managed entity with a blanket setter/mapper call

### 7.4 Universal Security (see `design/references/security-checklist.md`)

- **Secrets**: DB credentials / JWT signing key from `application-{profile}.yml` backed by env
  vars or a secret manager — never a literal value committed in `application.yml`
- **Business security**: for a state-changing service method on balance/payment/approval, state
  the `@Transactional` isolation/locking approach (`@Lock(PESSIMISTIC_WRITE)`, `@Version` optimistic
  locking, or a distributed lock) and, for transfer-like endpoints, the idempotency key check
- **Error handling**: confirm `GlobalExceptionHandler` (§8) has a catch-all that returns the
  generic `ProblemDetail` shape and logs the real exception — never let an unhandled exception
  reach Spring's default error page with a stack trace
- **CORS/CSRF**: state whether this API is Bearer-token (state CSRF protection isn't needed for
  that reason) or session-cookie based (requires explicit CSRF config, since Spring Security
  enables CSRF protection by default for stateful apps and disabling it needs a stated reason)
- **Security testing**: `@WebMvcTest` coverage (§4 Testing) includes IDOR (authenticated user A
  requesting user B's resource id → 403/404) and expired/invalid JWT, on top of the missing-auth
  (401) and insufficient-role (403) cases already listed

---

## 8. Error Handling

### 8.1 Global Exception Handling

```java
// src/main/java/{basePackage}/shared/GlobalExceptionHandler.java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler([Entity]NotFoundException.class)
    public ProblemDetail handleNotFound([Entity]NotFoundException ex) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
    }

    @ExceptionHandler([Entity]ConflictException.class)
    public ProblemDetail handleConflict([Entity]ConflictException ex) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "validation failed");
    }
}
```

`ProblemDetail` (RFC 7807) is Spring 6/Boot 3's built-in shape — if the project targets Boot 2,
use a project-defined `ErrorResponse` DTO instead and say so explicitly.

### 8.2 Error Code Mapping

| Domain Exception | HTTP Status | Scenario |
|-------------------|------------|----------|
| [Entity]NotFoundException | 404 Not Found | Resource doesn't exist |
| [Entity]ConflictException | 409 Conflict | Duplicate entry |
| MethodArgumentNotValidException | 400 Bad Request | `@Valid` DTO validation failure |
| AuthenticationException | 401 Unauthorized | Invalid/missing JWT |
| AccessDeniedException | 403 Forbidden | Insufficient role |

---

## 9. Performance Design

### 9.1 Query Strategy

- N+1 prevention: `@EntityGraph` or `JOIN FETCH` for any list endpoint that also renders a relation
- Pagination: `Pageable`/`Page<T>` everywhere a list can grow unbounded; default size 20, max 100 (enforce in controller or a `PageableHandlerMethodArgumentResolverCustomizer`)
- Read-only transactions (`@Transactional(readOnly = true)`) on query paths to skip dirty-checking overhead

### 9.2 Caching

| Cache | Key | TTL | Eviction Trigger |
|-------|-----|-----|-------------------|
| `{module}Cache` | id | 15 min | `@CacheEvict` on update/delete |

State cache stampede mitigation (Caffeine's `refreshAfterWrite`, or a `@Cacheable`-adjacent
single-flight pattern) if this key is hot enough that concurrent misses would fan out into
simultaneous DB queries.

### 9.3 Universal Performance (see `design/references/performance-checklist.md`)

- **Performance baseline**: state expected RPS and P95/P99 latency target for this endpoint — mark `[PERF TARGET NEEDED]` if the SRS doesn't specify one
- **Transaction scope**: no `@Transactional` service method calls an external HTTP client, a blocking Kafka send, or `Thread.sleep`/retry inside its boundary — state the split (short DB-only transaction, external call after commit) explicitly for any method that needs both
- **Timeout**: `RestTemplate`/`WebClient`/Feign client config states connect/read/overall timeout; any `@Retryable` states max attempts + exponential backoff + which exceptions are retryable (never on 4xx/validation)
- **Connection pools**: HikariCP `maximumPoolSize` sized against `instance count × pool size ≤ DB max connections`, stated explicitly rather than left at the default
- **Circuit breaker**: state whether a Resilience4j (or equivalent) circuit breaker wraps this feature's calls to an external dependency that can degrade

---

## 10. Distributed & Async Design

> Full checklist: `design/references/distributed-systems-checklist.md`. Fill this section when
> this module crosses a service boundary, publishes/consumes a Kafka/queue message, runs work
> asynchronously (`@Async`, a job queue), or calls an external system (Core Banking, payment
> gateway). If this module is a plain synchronous CRUD API with no external dependency, state
> "N/A — synchronous, single-service, no messaging" and skip to Test Plan.

### 10.1 Data Ownership & Consistency

- **Owner**: this module owns `[Entity]` — no other service writes to its table directly
- **Source of truth**: [this service | Core Banking | another service] is authoritative for `[field]`
- **Consistency**: [STRONG | EVENTUAL] for `[operation]` — state the reason if STRONG

### 10.2 Async Boundary & Transactional Outbox

- **Sync vs. async**: [synchronous response | 202-accepted, processed via `[topic]`]
- **Outbox**: if a DB write must be atomic with an event publish, an `outbox_event` row is
  inserted in the same `@Transactional` method as the business write; a separate
  `@Scheduled`/CDC-based publisher sends unpublished rows to Kafka — never an inline
  `kafkaTemplate.send(...)` call outside the transaction

### 10.3 Idempotency & Ordering

- **Idempotency key**: `[idempotencyKey field]` propagated from [client/API] through to [`@KafkaListener`/external call]
- **Duplicate handling**: `@KafkaListener` method checks `processedEventRepository.existsById(eventId)`, marks processed in the same `@Transactional` boundary as the business update
- **Ordering scope**: [Global | Tenant | Account | Aggregate] — partition key: `[field, e.g. accountId]`

### 10.4 State Machine (if this entity has a status field)

```text
[PENDING] → [PROCESSING] → [COMPLETED]
                ↓
           [RETRYING] → [FAILED]
```
Transitions validated in `[Entity.transitionTo()]` or a dedicated state-machine service — never
set directly via `entity.setStatus(...)` from a consumer.

### 10.5 Failure Handling

- **Retry**: `@Retryable(maxAttempts = [N], backoff = @Backoff(...))`, retryable: `[list]`; non-retryable: `[list]`
- **DLQ**: topic `[topic].dlq`, carries `eventId, eventType, payload, retryCount, error, failedAt, correlationId`
- **Unknown result**: a `TimeoutException` calling `[external system]` transitions this record to `UNKNOWN`, resolved via `[status-inquiry endpoint | reconciliation job]` — never directly to `FAILED`
- **Reconciliation**: [if financial/critical] `[job name]` compares `[fields]` against `[external system]` on `[schedule]`

---

## 11. Test Plan

### 11.1 Service Unit Tests (JUnit5 + Mockito)

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `create_success` | Valid request | Returns created response |
| `create_conflict` | Duplicate field | Throws `[Entity]ConflictException` |
| `get_notFound` | Invalid id | Throws `[Entity]NotFoundException` |

### 11.2 Controller Tests (`@WebMvcTest` + MockMvc)

| Test Case | Endpoint | Auth | Expected Status |
|-----------|----------|------|-------------------|
| GET success | GET /{id} | Valid JWT | 200 |
| GET not found | GET /invalid-id | Valid JWT | 404 |
| GET no auth | GET /{id} | None | 401 |
| POST create | POST / | Role JWT | 201 |
| POST validation | POST / (blank field) | Role JWT | 400 |

### 11.3 Repository Tests (`@DataJpaTest`)

Verify custom query methods and `@EntityGraph` fetch behavior against a real (embedded or
Testcontainers) database — not against mocks, since the whole point is verifying the generated SQL.

### 11.4 SRS Traceability

| SRS Requirement | Implemented In |
|-------------------|------------------|
| FR-01: [requirement] | Service method: [name], API: [endpoint] |
| BR-01: [business rule] | Service validation logic |
```

---

## NAMING CONVENTIONS (MODE D)

Discover exact conventions from CLAUDE.md/`pom.xml` groupId — below are typical patterns:

- SDS path: same as MODE B/C — `docs/04-sds/M-XX-module-name.md`
- Package: `{basePackage}.{module}.{layer}` lowercase
- Entity: PascalCase, singular (`Video`, not `Videos`)
- DTO: `{Entity}Request` / `{Entity}Response` (records, not mutable classes, unless project convention differs)
- Exception: `{Entity}NotFoundException`, `{Entity}ConflictException`
- Test class: `{ClassUnderTest}Test` (unit), `{ClassUnderTest}IT` (integration, if the project separates them)

---

## LAYERING RULES (MODE D)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|----------------|
| domain (entity) | JPA annotations, stdlib | Spring MVC, Controller, Service |
| repository | Spring Data JPA, domain | Controller, DTO |
| service | repository, domain, DTO (map at the boundary) | Spring MVC `HttpServletRequest`/`ResponseEntity` |
| controller | service, DTO, mapper | repository directly |

**Entity Design:**
- JPA entity holds persistence concerns and minimal invariants only — no business logic that
  belongs in the service layer, no calls out to other services
- Never return a JPA entity directly from a controller — lazy-loaded associations serialize
  unpredictably (or throw `LazyInitializationException` outside the persistence context) and
  any field added to the entity later leaks to clients automatically. Always map to a DTO.
- `createdAt`/`updatedAt` via `@PrePersist`/`@PreUpdate` or Spring Data JPA Auditing
  (`@CreatedDate`/`@LastModifiedDate` + `@EnableJpaAuditing`) — pick one, state which in the SDS

**Service Pattern:**
```java
// Every write path: validate -> check invariants -> mutate -> map to response, inside @Transactional
@Transactional
public [Entity]Response create([Entity]Request request) { ... }
```

**SDS Traceability Comment (required):**
```java
// Traceability: SDS M-XX Section Y.Z [Operation Name]
public [Entity]Response create(...) { ... }
```

**SDS Design Principle:**
Design from the JPA Entity outward (Entity → Repository → Service → Controller/DTO) — same
inside-out discipline as MODE B, adapted to Spring's layered convention instead of Go's
Clean Architecture folder split. Don't design the Controller/endpoint first and only think about the Entity afterward.
