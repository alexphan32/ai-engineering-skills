# Implement Skill — NestJS Reference Material

> Load this when implementing in a NestJS (TypeScript) codebase. It complements
> `verification-checklist.md` — that file's language-agnostic checklist (linting, testing,
> secrets scan, docs) still applies; this file adds the traps specific to this stack.
>
> **First, identify the ORM.** NestJS is ORM-agnostic — check `package.json` for
> `@nestjs/typeorm` + `typeorm` vs. `@prisma/client` (with a `PrismaService` wrapping
> `PrismaClient`). The two produce different entity/repository code; don't assume one from
> memory or from a different NestJS project you've seen before.

---

## GOOD VS BAD IMPLEMENTATION EXAMPLES

### ❌ No global `ValidationPipe` — DTO decorators do nothing

```typescript
// main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000);
  // class-validator decorators on every DTO are inert without this —
  // any JSON body reaches the handler unvalidated and un-stripped
}
```

### ✅ Registering the global pipe

```typescript
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,            // strip properties with no decorator
    forbidNonWhitelisted: true, // reject requests that include them, instead of silently dropping
    transform: true,            // coerce payloads into the DTO class instance
  }));
  await app.listen(3000);
}
```

**Why this is better:** `@IsString()`/`@IsNotEmpty()` etc. are only enforced once a `ValidationPipe`
actually runs — without this, class-validator decorators are decoration in the literal sense.
`whitelist`/`forbidNonWhitelisted` is also the mechanism that prevents mass-assignment of fields
the DTO never declared.

---

### ❌ Returning the entity/Prisma model directly, ignoring the Response DTO

```typescript
@Get(':id')
async findOne(@Param('id') id: number) {
  return this.usersService.findOne(id); // includes passwordHash, internal flags, etc.
}
```

### ✅ Mapping through the Response DTO with the serializer applied

```typescript
@Get(':id')
@UseInterceptors(ClassSerializerInterceptor)
async findOne(@Param('id', ParseIntPipe) id: number): Promise<UserResponseDto> {
  return plainToInstance(UserResponseDto, await this.usersService.findOne(id));
}

@Exclude()
export class UserResponseDto {
  @Expose() id: number;
  @Expose() email: string;
  // passwordHash has no @Expose — ClassSerializerInterceptor strips it
}
```

**Why this is better:** declaring `@Exclude()`/`@Expose()` on a DTO does nothing by itself —
`ClassSerializerInterceptor` (registered on the method, controller, or globally) is what
actually applies it during serialization. Both pieces are required.

---

### ❌ Business logic in the controller

```typescript
@Post()
async create(@Body() dto: CreateUserDto) {
  const existing = await this.repo.findOneBy({ email: dto.email }); // controller talking
  if (existing) throw new ConflictException('email taken');          // straight to the repo
  return this.repo.save(this.repo.create(dto));
}
```

### ✅ Controller delegates, service owns the logic

```typescript
@Post()
async create(@Body() dto: CreateUserDto) {
  return this.usersService.create(dto);
}

// users.service.ts
async create(dto: CreateUserDto): Promise<User> {
  const existing = await this.repo.findOneBy({ email: dto.email });
  if (existing) throw new ConflictException('email taken');
  return this.repo.save(this.repo.create(dto));
}
```

**Why this is better:** the uniqueness check and persistence logic are unit-testable without
spinning up HTTP, and the controller stays a thin, uniform transport boundary across the module.

---

### ❌ Swallowing a thrown `HttpException` in a manual try/catch

```typescript
async create(dto: CreateUserDto) {
  try {
    return await this.repo.save(this.repo.create(dto));
  } catch (e) {
    throw new InternalServerErrorException('failed'); // masks the real
  }                                                     // ConflictException from a unique constraint
}
```

### ✅ Let the specific exception surface, or re-throw it explicitly

```typescript
async create(dto: CreateUserDto) {
  const existing = await this.repo.findOneBy({ email: dto.email });
  if (existing) throw new ConflictException('email taken'); // checked before insert,
  return this.repo.save(this.repo.create(dto));              // so no broad catch is needed
}
```

**Why this is better:** NestJS's built-in `HttpException` subclasses already map to the correct
status automatically — wrapping them in a catch-all swallows that mapping and turns every
failure into an opaque 500.

---

## IMPLEMENTATION PRIORITY

Same P0–P3 ordering as the general checklist — NestJS specifics slot in as follows:

### **P0 - Critical**
- Global `ValidationPipe` with `whitelist`/`forbidNonWhitelisted`/`transform` registered (or confirmed already present)
- Every mutating endpoint's Guard(s) actually applied (`@UseGuards`) — not just a DTO shape that implies auth
- Business/uniqueness/ownership checks in the Service, not the Controller
- No raw entity/Prisma model returned from a controller — always through a Response DTO

### **P1 - High**
- `ClassSerializerInterceptor` applied wherever a Response DTO uses `@Exclude`/`@Expose`
- Built-in `HttpException` subclasses thrown for expected failures, not masked by a broad `try/catch`
- Module wiring (`imports`/`providers`/`exports`) matches what the service actually needs injected

### **P2 - Medium**
- Unit tests (Jest + `@nestjs/testing`) for service logic with mocked repository/`PrismaService`
- e2e tests (Supertest) for controller endpoints, covering auth and validation failure paths

### **P3 - Low**
- N+1 cleanup via `relations`/`include` narrowing
- Response caching (`@nestjs/cache-manager`) for hot read paths

---

## VERIFICATION CHECKLIST (NestJS additions)

Run these in addition to the general checklist:

### 1. Code Quality
```bash
npx tsc --noEmit
npm run lint     # or pnpm/yarn equivalent
```
- [ ] No DTO field lacking a class-validator decorator that should have one (an undecorated field is invisible to `whitelist` stripping — it's neither validated nor guaranteed removed, check the pipe config)

### 2. Correctness
- [ ] Every service method that can fail expectedly throws a specific `HttpException` subclass, not a generic `Error`
- [ ] Every Response DTO with `@Exclude`/`@Expose` has `ClassSerializerInterceptor` applied somewhere in its request path
- [ ] Module's `providers`/`imports` include everything the service constructor injects

### 3. Security
- [ ] Global `ValidationPipe` registered with `whitelist: true, forbidNonWhitelisted: true`
- [ ] Every non-public endpoint has `@UseGuards(...)` present — verified by reading the decorator, not assumed from the route name
- [ ] Every endpoint taking a resource id also checks ownership in the service layer (`request.user.id` vs. the resource's owner field), not just the role — IDOR check, not just an authentication check
- [ ] No sensitive field (password hash, token) has `@Expose()` on any Response DTO
- [ ] Auth/OTP/payment endpoints have `@nestjs/throttler` (or gateway-level) rate limiting applied if the SDS specified a tier
- [ ] A state-changing service method on balance/payment/approval implements the concurrency-control/idempotency mechanism the SDS named — not just a plain repository `.save()`
- [ ] Global exception handling never lets a TypeORM/Prisma driver error message reach the response body — verify with a test that intentionally triggers a DB-layer error
- [ ] `main.ts` CORS config has no `origin: '*'` combined with `credentials: true`

```bash
git grep -iE "(password|secret|api_key|token)\s*=" -- '*.ts'
git grep -inE "logger\.(log|debug|warn|error)\(.*\b(password|token|otp)\b" -- '*.ts'
```

Full checklist (SSRF, file upload, secrets storage, dependency scan, mandatory security test
cases): `references/security-implementation-checklist.md`.

### 4. Testing
```bash
npm run test        # unit
npm run test:e2e     # e2e, if configured
```
- [ ] Service unit tests mock the repository/`PrismaService` via `Test.createTestingModule` providers, not a real DB
- [ ] e2e tests cover: success, validation failure (400 — including an extra/unknown field if `forbidNonWhitelisted` is on), missing auth (401), insufficient role (403), IDOR (user requesting another user's resource id → 403/404), expired/invalid JWT

### 5. Performance
- [ ] List endpoints that render a relation load it via `relations`/`include`, not a per-row extra query
- [ ] Unbounded list endpoints paginate (`skip`/`take` or cursor), not a bare `findAll()`
- [ ] No `QueryRunner`/`$transaction` block calls `HttpService`/Axios or does a blocking Kafka publish inside its boundary
- [ ] `HttpService`/Axios client has an explicit `timeout` configured — not left at the library default
- [ ] Any retry logic (interceptor or manual) is bounded with exponential backoff + jitter, excluding 4xx/validation errors
- [ ] Any `Promise.all` over a caller-controlled array is bounded (e.g. `p-limit`) if the array size isn't already capped by DTO validation

```bash
# query-in-loop candidates
grep -n -B2 "\.find(\|\.findOne(\|repository\." -- '*.ts' | grep -B2 "for (\|while (\|forEach\|\.map("
```

Full checklist (connection-pool sizing math, circuit breaker, cache stampede, memory streaming,
anti-pattern sweep): `references/performance-implementation-checklist.md`.

### 6. Distributed & Async (if this module publishes/consumes messages or calls an external system)
- [ ] A business-critical operation that must survive a crash isn't a bare fire-and-forget `Promise` — it's backed by a durable queue (`@nestjs/bull`, Kafka, SQS) or a persisted job
- [ ] Every `@EventPattern`/`@MessagePattern` handler checks a processed-events store for the message ID before applying the effect, and marks processed in the same transaction as the business update
- [ ] A DB write that must be atomic with an outgoing event goes through an outbox table in the same transaction, not an inline `kafkaClient.emit(...)`/`this.client.emit(...)` outside it
- [ ] Any entity with a status field is only mutated through a transition method — grep for direct `entity.status = ...` assignment outside that method
- [ ] A timeout calling an external system (Core Banking, payment gateway) sets the record to `UNKNOWN`/`PENDING`, never directly to a terminal failure state

```bash
grep -rn "\.status = ['\"]" -- '*.ts'
```

Full checklist (Saga/compensation, reconciliation jobs, DLQ payload shape, mandatory
failure-scenario tests): `references/distributed-systems-implementation-checklist.md`.

---

## TROUBLESHOOTING

**A DTO's validation decorators seem to do nothing — invalid payloads reach the handler:**
Check `main.ts` for a global `ValidationPipe`, or that one is applied via `@UsePipes` on the
specific controller/method. Decorators alone enforce nothing.

**A Response DTO's `@Exclude()`d field still appears in the JSON response:**
Check that `ClassSerializerInterceptor` is actually registered (globally, on the controller, or
via `@UseInterceptors` on the method) — `class-transformer` decorators are inert without it.

**An extra field the client sent silently vanished instead of being rejected:**
That's `whitelist: true` without `forbidNonWhitelisted: true` — expected if the design calls for
silent stripping, otherwise add `forbidNonWhitelisted: true` to reject it with a 400 instead.

**Every failure comes back as a 500 instead of the expected 4xx:**
Look for a broad `try/catch` around the service method that swallows the specific
`HttpException` and rethrows `InternalServerErrorException` — let the specific exception
propagate instead.

**Injecting a repository/service throws `Nest can't resolve dependencies`:**
The providing module's `providers`/`exports` (for the thing being injected) or the consuming
module's `imports` (for the module that exports it) is missing an entry — this is almost always
a module-wiring gap, not a code logic bug.
