# SDS Template E: NestJS / REST API (TypeScript)

> Reference for `design` skill — loaded on demand when creating MODE E SDS documents.
>
> **First, detect the persistence layer.** NestJS itself is ORM-agnostic — a project wires in
> either TypeORM (`@nestjs/typeorm` + `typeorm` in `package.json`, entities as decorated classes)
> or Prisma (`@prisma/client`, a `PrismaService` wrapping `PrismaClient`, schema lives in
> `prisma/schema.prisma`). The two shapes are different enough (decorated entity class vs.
> generated client + schema file) that this template branches at Section 2 — check
> `package.json`/`prisma/` before drafting rather than assuming one.

---

## TEMPLATE E: NestJS / REST API SDS

```markdown
# M-XX: [Module Name]

> **Status**: Draft
> **Created**: YYYY-MM-DD
> **Version**: 1.0
> **Related SRS**: F-XX: [Feature Name]
> **Tech Stack**: NestJS {version}, {TypeORM | Prisma} — discover exact versions from `package.json`

---

## 1. Module Overview

### 1.1 Description
[Describe what this module does in the system]

### 1.2 Scope
**Covers SRS Requirements**: FR-01, FR-02, FR-03
**Module Type**: [Core Domain / Supporting / Infrastructure]
**Scale Tier**: [Tier 1 MVP / Tier 2 Async-Growing / Tier 3 Enterprise-Distributed — one-line reason, see `.claude/skills/architecture/references/system-scale-checklist.md`]

### 1.3 Module Layout
```
src/{module}/
├── {module}.module.ts              # providers/controllers/imports wiring
├── {module}.controller.ts          # @Controller — HTTP boundary only
├── {module}.service.ts             # @Injectable — business logic
├── dto/create-{entity}.dto.ts      # class-validator decorated
├── dto/update-{entity}.dto.ts      # usually PartialType(CreateDto)
├── dto/{entity}-response.dto.ts    # what actually leaves the API
├── entities/{entity}.entity.ts     # TypeORM only — omit if using Prisma
└── {module}.service.spec.ts / {module}.controller.spec.ts
```

**Entities**: [List entities/models]
**APIs**: [List main endpoints]
**Dependencies**: [Auth module, other feature modules]

---

## 2. Data Model

### 2.1a TypeORM Entity (if project uses TypeORM)

```typescript
// src/{module}/entities/[entity].entity.ts
// Traceability: SDS M-XX Section 2.1
import { Entity, Column, PrimaryGeneratedColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('[table_name]')
export class [Entity] {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ unique: true })
  [field]: string;

  @Column({ default: true })
  active: boolean;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
```

### 2.1b Prisma Model (if project uses Prisma)

```prisma
// prisma/schema.prisma
// Traceability: SDS M-XX Section 2.1
model [Entity] {
  id        Int      @id @default(autoincrement())
  [field]   String   @unique
  active    Boolean  @default(true)
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")

  @@map("[table_name]")
}
```

**Field Definitions:**

| Field | Type | Required | Description |
|-------|------|----------|--------------|
| id | number | Yes (generated) | Primary key |
| [field] | string | Yes | [description] |
| active | boolean | Yes | Soft delete flag |
| createdAt | Date | Yes | Creation timestamp |
| updatedAt | Date | Yes | Last update timestamp |

### 2.2 Indexes

| Index | Columns | Type | Reason |
|-------|---------|------|--------|
| `idx_[field]` | `[field]` | Unique | Frequent lookup |
| `idx_active_created` | `active, createdAt DESC` | Compound | List query with sort |

---

## 3. DTOs (Trust Boundary)

```typescript
// src/{module}/dto/create-[entity].dto.ts
import { IsString, IsNotEmpty, MaxLength } from 'class-validator';

export class Create[Entity]Dto {
  @IsString()
  @IsNotEmpty()
  @MaxLength(255)
  field: string;
}

// src/{module}/dto/update-[entity].dto.ts
import { PartialType } from '@nestjs/mapped-types';
export class Update[Entity]Dto extends PartialType(Create[Entity]Dto) {}

// src/{module}/dto/[entity]-response.dto.ts
import { Exclude, Expose } from 'class-transformer';

@Exclude()
export class [Entity]ResponseDto {
  @Expose() id: number;
  @Expose() field: string;
  @Expose() createdAt: Date;
  // fields NOT decorated with @Expose (e.g. a sensitive column) never serialize out —
  // this only works if ClassSerializerInterceptor is registered, see Section 7.3
}
```

**DTO validation is the actual trust boundary for this stack.** It only holds if the global
`ValidationPipe` is registered with `whitelist: true, forbidNonWhitelisted: true, transform: true`
(usually in `main.ts`) — state this assumption explicitly if the SDS relies on unknown-field
stripping, since a project without that global pipe silently accepts extra client fields.

---

## 4. API Specification

### 4.1 Endpoints Overview

| Method | Path | Auth | Description |
|--------|------|------|--------------|
| GET | /[resource] | JWT | List resources (paginated) |
| GET | /[resource]/:id | JWT | Get by ID |
| POST | /[resource] | JWT (role) | Create resource |

### 4.2 API Details

#### GET /[resource]
**Purpose**: [description]
**Auth**: `@UseGuards(JwtAuthGuard)`
**Query Params**: `page` (default 1), `limit` (default 20, max 100)
**Response**: `{ data: [Entity]ResponseDto[], meta: { total, page, limit } }`
**HTTP Status**: 200 OK

#### POST /[resource]
**Purpose**: [description]
**Auth**: `@UseGuards(JwtAuthGuard, RolesGuard)`, `@Roles('[ROLE]')`
**Request Body**: `Create[Entity]Dto`
**Response**: `[Entity]ResponseDto`
**HTTP Status**: 201 Created | 400 Bad Request | 409 Conflict

---

## 5. Service Design

```typescript
// src/{module}/{module}.service.ts
// Traceability: SDS M-XX Section 5 [Entity] service
@Injectable()
export class [Module]Service {
  constructor(
    @InjectRepository([Entity]) private readonly repo: Repository<[Entity]>,
    // OR: private readonly prisma: PrismaService,
  ) {}

  async create(dto: Create[Entity]Dto): Promise<[Entity]> {
    const existing = await this.repo.findOneBy({ field: dto.field });
    if (existing) {
      throw new ConflictException(`[Entity] with field '${dto.field}' already exists`);
    }
    return this.repo.save(this.repo.create(dto));
  }

  async findOne(id: number): Promise<[Entity]> {
    const entity = await this.repo.findOneBy({ id });
    if (!entity) throw new NotFoundException(`[Entity] ${id} not found`);
    return entity;
  }
}
```

**Flow (Create):**
```
1. DTO already validated by the global ValidationPipe before the handler runs
2. Check uniqueness via repository/PrismaService
3. Throw a built-in HttpException subclass for expected failures — NestJS maps it to the
   right HTTP status automatically, no manual switch/mapping layer needed (unlike MODE B/D)
4. Persist
5. Return entity — mapping to Response DTO happens at the controller/interceptor boundary
```

**Business logic lives in the service, never the controller** — the controller's job is
extracting the request and returning what the service produces.

---

## 6. Controller Design

```typescript
// src/{module}/{module}.controller.ts
@Controller('[resource]')
@UseInterceptors(ClassSerializerInterceptor)
export class [Module]Controller {
  constructor(private readonly service: [Module]Service) {}

  @Get(':id')
  @UseGuards(JwtAuthGuard)
  async findOne(@Param('id', ParseIntPipe) id: number): Promise<[Entity]ResponseDto> {
    return plainToInstance([Entity]ResponseDto, await this.service.findOne(id));
  }

  @Post()
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles('[ROLE]')
  @HttpCode(HttpStatus.CREATED)
  async create(@Body() dto: Create[Entity]Dto): Promise<[Entity]ResponseDto> {
    return plainToInstance([Entity]ResponseDto, await this.service.create(dto));
  }
}
```

### 6.1 Module Wiring

```typescript
// src/{module}/{module}.module.ts
@Module({
  imports: [TypeOrmModule.forFeature([[Entity]])], // or: [] if using a global PrismaModule
  controllers: [[Module]Controller],
  providers: [[Module]Service],
  exports: [[Module]Service],
})
export class [Module]Module {}
```

---

## 7. Security Design

### 7.1 Authentication Requirements

| Endpoint | Auth | Role |
|----------|------|------|
| GET /[resource] | Optional | - |
| GET /[resource]/:id | Required (JWT) | Any |
| POST /[resource] | Required (JWT) | [ROLE] |

### 7.2 Guards

- `JwtAuthGuard` (wraps Passport's `AuthGuard('jwt')`) for authentication
- `RolesGuard` + `@Roles(...)` (via `Reflector` reading metadata set by `@SetMetadata`) for
  authorization — specify exactly which roles gate which endpoint here, not just "protected"
- Ownership checks (resource belongs to the authenticated principal) belong in the **service**,
  reading `request.user` passed down from the controller — not duplicated per-guard logic

### 7.3 Response Shaping

- Every Response DTO uses `@Exclude()` at the class level + `@Expose()` per field that should
  leave the API, and the controller (or a global interceptor) must actually apply
  `ClassSerializerInterceptor` — declaring the DTO without the interceptor does nothing
- Never return the raw entity/Prisma model from a controller method — always run it through
  `plainToInstance(ResponseDto, entity)` or an equivalent explicit mapping

### 7.4 Data Security

- Global `ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true })` —
  state this as a precondition if not already present in `main.ts`
- SQL injection: TypeORM query builder / repository methods only, never raw string interpolation
  into `.query()`; Prisma's parameterized API only, raw `$queryRawUnsafe` is out of scope unless
  explicitly justified

### 7.5 Universal Security (see `design/references/security-checklist.md`)

- **Secrets**: `ConfigService`-backed env vars or a secret manager for JWT secret/DB
  credentials — never a literal in a module's static config object
- **Business security**: for a state-changing service method on balance/payment/approval, state
  the transaction/locking approach (`QueryRunner` + row lock, or optimistic version column) and,
  for transfer-like endpoints, the idempotency key check
- **Error handling**: confirm the global `ExceptionFilter`/Nest's built-in `HttpException` mapping
  (§8) never lets a TypeORM/Prisma driver error message reach the response body
- **CORS/CSRF**: state whether this API is Bearer-token (CSRF not needed for that reason, state it)
  or cookie-session based (requires `app.enableCors({credentials: true, origin: [...]})` — never
  `origin: '*'` with credentials — plus explicit CSRF middleware)
- **Rate limiting**: name the tier (`@nestjs/throttler` or gateway-level) for auth/OTP/payment
  endpoints specifically
- **Security testing**: e2e coverage (§4 Testing) includes IDOR (user A requesting user B's
  resource id → 403/404) and expired/invalid JWT, on top of the missing-auth (401) and
  insufficient-role (403) cases already listed

---

## 8. Error Handling

NestJS's built-in `HttpException` subclasses (`NotFoundException`, `BadRequestException`,
`ConflictException`, `ForbiddenException`, `UnauthorizedException`) already map to the correct
HTTP status when thrown from a service or controller — **no manual error → status switch is
needed**, unlike MODE B/D. Only add a custom `ExceptionFilter` (`@Catch()` + `app.useGlobalFilters()`)
for a domain error that has no built-in equivalent, or to reshape the error response body
project-wide.

### 8.1 Error Mapping

| Thrown Exception | HTTP Status | Scenario |
|--------------------|------------|----------|
| `NotFoundException` | 404 | Resource doesn't exist |
| `ConflictException` | 409 | Duplicate entry |
| `BadRequestException` / `ValidationPipe` failure | 400 | DTO validation failure |
| `UnauthorizedException` | 401 | Invalid/missing JWT |
| `ForbiddenException` | 403 | Insufficient role |

---

## 9. Performance Design

### 9.1 Query Strategy

- N+1 prevention: TypeORM `relations: [...]` / query-builder `leftJoinAndSelect`, or Prisma
  `include`/`select` — narrow to what the endpoint actually returns
- Pagination: offset (`skip`/`take` or Prisma `skip`/`take`) for admin lists, cursor-based for
  high-volume public feeds — state which this SDS uses and why
- Read caching via `@nestjs/cache-manager`'s `CacheInterceptor` + `@CacheTTL(...)` where reads
  vastly outnumber writes

### 9.2 Caching

| Cache Key | Value | TTL | Eviction Trigger |
|-----------|-------|-----|---------------------|
| `{module}:{id}` | Response DTO JSON | 15 min | Manual `cacheManager.del()` on update/delete |

State cache stampede mitigation (jittered TTL, or a request-coalescing wrapper around the
cache-miss path) if this key is hot enough that concurrent misses would fan out into simultaneous
DB queries.

### 9.3 Universal Performance (see `design/references/performance-checklist.md`)

- **Performance baseline**: state expected RPS and P95/P99 latency target for this endpoint — mark `[PERF TARGET NEEDED]` if the SRS doesn't specify one
- **Transaction scope**: no TypeORM `QueryRunner`/Prisma `$transaction` block calls an external HTTP client or a blocking Kafka publish inside it — state the split explicitly for any method needing both
- **Timeout**: `HttpService`/Axios client config states connect/read/overall timeout; any retry (interceptor or manual) states bound + exponential backoff + jitter, excluding 4xx/validation errors
- **Connection pools**: TypeORM/Prisma pool size and any downstream HTTP client's connection pool sized against `instance count × pool size ≤ downstream capacity`
- **Concurrency**: state whether this feature does any unbounded `Promise.all` fan-out over a caller-controlled array — bound it (e.g. `p-limit`) if the array size isn't already capped by validation

---

## 10. Distributed & Async Design

> Full checklist: `design/references/distributed-systems-checklist.md`. Fill this section when
> this module crosses a service boundary, publishes/consumes a Kafka/queue message, runs work
> asynchronously (a job queue, `@nestjs/bull`), or calls an external system (Core Banking,
> payment gateway). If this module is a plain synchronous CRUD API with no external dependency,
> state "N/A — synchronous, single-service, no messaging" and skip to Test Plan.

### 10.1 Data Ownership & Consistency

- **Owner**: this module owns `[Entity]` — no other service writes to its table directly
- **Source of truth**: [this service | Core Banking | another service] is authoritative for `[field]`
- **Consistency**: [STRONG | EVENTUAL] for `[operation]` — state the reason if STRONG

### 10.2 Async Boundary & Transactional Outbox

- **Sync vs. async**: [synchronous response | 202-accepted, processed via `[topic]`]
- **Outbox**: if a DB write must be atomic with an event publish, an `outbox_event` row is
  inserted in the same TypeORM `QueryRunner`/Prisma `$transaction` as the business write; a
  separate poller/CDC-based publisher sends unpublished rows to Kafka — never an inline
  `kafkaClient.emit(...)` call outside the transaction

### 10.3 Idempotency & Ordering

- **Idempotency key**: `[idempotencyKey field]` propagated from [client/API] through to [`@EventPattern`/external call]
- **Duplicate handling**: the consumer checks a `processedEventRepository`/cache for `eventId` before applying, marks processed in the same transaction as the business update
- **Ordering scope**: [Global | Tenant | Account | Aggregate] — partition key: `[field, e.g. accountId]`

### 10.4 State Machine (if this entity has a status field)

```text
[PENDING] → [PROCESSING] → [COMPLETED]
                ↓
           [RETRYING] → [FAILED]
```
Transitions validated in a dedicated state-machine service method — never set directly via
`entity.status = ...` from a consumer.

### 10.5 Failure Handling

- **Retry**: bounded attempts with exponential backoff + jitter (interceptor or `@nestjs/bull` retry config), retryable: `[list]`; non-retryable: `[list]`
- **DLQ**: topic `[topic].dlq`, carries `eventId, eventType, payload, retryCount, error, failedAt, correlationId`
- **Unknown result**: a timeout calling `[external system]` transitions this record to `UNKNOWN`, resolved via `[status-inquiry endpoint | reconciliation job]` — never directly to `FAILED`
- **Reconciliation**: [if financial/critical] `[job name]` compares `[fields]` against `[external system]` on `[schedule]`

---

## 11. Test Plan

### 11.1 Service Unit Tests (Jest + `@nestjs/testing`)

```typescript
const module = await Test.createTestingModule({
  providers: [[Module]Service, { provide: getRepositoryToken([Entity]), useValue: mockRepo }],
}).compile();
```

| Test Case | Scenario | Expected |
|-----------|----------|----------|
| `create_success` | Valid dto | Returns created entity |
| `create_conflict` | Duplicate field | Throws `ConflictException` |
| `findOne_notFound` | Invalid id | Throws `NotFoundException` |

### 11.2 Controller / e2e Tests (Supertest + `INestApplication`)

| Test Case | Endpoint | Auth | Expected Status |
|-----------|----------|------|--------------------|
| GET success | GET /:id | Valid JWT | 200 |
| GET not found | GET /invalid-id | Valid JWT | 404 |
| GET no auth | GET /:id | None | 401 |
| POST create | POST / | Role JWT | 201 |
| POST extra field | POST / with unknown field | Role JWT | 400 (if whitelist enabled) |

### 11.3 SRS Traceability

| SRS Requirement | Implemented In |
|--------------------|-------------------|
| FR-01: [requirement] | Service method: [name], API: [endpoint] |
| BR-01: [business rule] | Service validation logic |
```

---

## NAMING CONVENTIONS (MODE E)

- SDS path: same as MODE B/C/D — `docs/04-sds/M-XX-module-name.md`
- File names: kebab-case (`create-user.dto.ts`, `user.service.ts`)
- Classes: PascalCase with role suffix (`UserService`, `UserController`, `UserModule`, `CreateUserDto`)
- Entities: PascalCase singular; DB table via `@Entity('table_name')` / `@@map("table_name")`

---

## LAYERING RULES (MODE E)

**Layer Import Rules (VIOLATIONS = ARCHITECTURAL DEFECTS):**

| Layer | Can Import | Cannot Import |
|-------|-----------|----------------|
| Controller | Service, DTO | Repository / `PrismaService` directly |
| Service | Repository / `PrismaService`, other services | Express `Request`/`Response` (breaks testability & transport independence) |
| Entity | ORM decorators only | Business logic methods with side effects |
| DTO | class-validator / class-transformer decorators | ORM decorators (keep persistence and transport shapes separate) |

**Design Principle:**
Design from the Entity/Prisma model outward (Entity → Service/Repository → DTO → Controller →
Module wiring) — same inside-out discipline as MODE B/D, adapted to Nest's module system.
Don't design the endpoint/route first and only think about the entity afterward.

**Common trap this stack invites:** because NestJS's built-in exceptions and global
`ValidationPipe` do so much automatically, it's tempting to skip designing the DTO validation
rules and error mapping explicitly ("Nest handles it"). Still spec them — a future implementer
needs to know *which* fields are required/optional and *which* exception each failure mode
should throw, even though the HTTP-status translation itself is automatic.
