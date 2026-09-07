# Java admission, readiness and shutdown

Phase 56 makes PostgreSQL and Redis required dependencies of the Java API. AWS remains the deployment target; Docker/Helm runtime cutover is Phase 58. These checks are local and CI evidence, not an AWS availability claim.

## Distributed quotas

Each replica uses the same Redis primary and `LIMITS_NAMESPACE`. Redis Lua checks/increments a counter and sets its TTL atomically. The window starts with its first accepted request. Rejections neither increment saturated counters nor extend expiry. The algorithm permits a burst around window boundaries; it is not a sliding window or a financial spending cap.

| Setting | Default | Scope |
|---|---:|---|
| `GLOBAL_REQUEST_LIMIT` | 600 | Each of gateway, telemetry and operator traffic, before authentication |
| `GATEWAY_KEY_REQUEST_LIMIT` | 60 | Each authenticated gateway key UUID |
| `TELEMETRY_KEY_REQUEST_LIMIT` | 300 | Each authenticated telemetry key UUID |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Window shared by these counters |
| `LIMITS_NAMESPACE` | ai-platform-local | Deployment namespace, default follows ENVIRONMENT |
| `MAX_CONCURRENT_REQUESTS` | 32 | In-flight /v1/ requests per instance, maximum 48 |

All replicas must have identical quota/window settings. Global counters use exactly three fixed keys; random invalid credentials cannot allocate Redis keys. Per-key counters use trusted database UUIDs, never raw credentials. Gateway quota runs after authentication/configuration resolution and before provider execution. Telemetry quota runs after authentication and before payload normalization; malformed authenticated payloads and duplicate deliveries consume quota. Invalid-key traffic consumes global quota. Exhausting it can affect legitimate traffic in the same class; this is a bounded admission defense, not per-customer fairness or a substitute for ingress controls.

429 includes a whole-second, rounded-up `Retry-After` derived from Redis TTL. Redis failure fails closed with a safe 503 and `Retry-After: 1`. Capacity exhaustion and dependency/drain refusal use the same safe 503. Rejected admission does not create request or cost records. Redis restart or eviction can reset quota state; configure the dedicated cache with an appropriate memory policy and monitor capacity. Use a separate namespace per environment and test run. Never flush a shared cache as a recovery step.

## Connections and input bounds

Configure `REDIS_HOST`, `REDIS_PORT` (6379 by default), optional `REDIS_USERNAME`, `REDIS_PASSWORD` and `REDIS_TLS_ENABLED`. Environments other than local/test require TLS and a password. TLS uses the JVM trust store with certificate and hostname verification enabled. AWS uses the approved ElastiCache primary endpoint and externally supplied credentials; no cloud secret is committed here. This client expects a standalone/cluster-mode-disabled primary, not Redis Cluster topology discovery.

Lettuce bounds connect/command waits to 500 ms, queues at most 64 requests, rejects commands while disconnected and reconnects automatically. Its event loop uses two I/O and two computation threads per application context. Database acquisition is bounded to one second; JDBC connect/socket/cancel timeouts are 2/3/1 seconds. Provider work holds no database connection.

The application bounds /v1/ paths to 2,048 characters and queries to 4,096 characters (414), gateway/telemetry bodies to 32 KiB and other API bodies to 256 KiB (413). Declared and streamed/chunked bodies receive the same limit. Body reads have a five-second total deadline plus at most one second of idle socket wait (408). Tomcat also limits headers to 8 KiB, connection/keepalive waits to five seconds, worker threads to 64, connections to 256 and the accept queue to 128. Connector-level malformed requests may use Tomcat's generic response; application refusals use safe JSON. Health requests bypass application quotas.

## Health and graceful shutdown

`/health/live` and management-port `/actuator/health/liveness` describe process lifecycle independently of Redis/PostgreSQL. `/health/ready` and management-port `/actuator/health/readiness` require both dependencies and an accepting, non-draining process. Details are hidden. One daemon checker refreshes a dependency snapshot one second after its previous bounded check completes; readiness refuses snapshots older than three seconds. HTTP probes read that snapshot without querying dependencies. A failed/stale snapshot may temporarily refuse work; recovery automatically restores readiness after a successful check.

On context shutdown, draining rejects new admitted work and readiness fails. Tomcat receives a 40-second graceful shutdown budget. `PROVIDER_TIMEOUT_SECONDS` is a total budget across queue wait, all attempts and backoff: default 15 seconds, maximum 20 seconds. Canceled/queued provider tasks are handled explicitly. The body, bounded admission and provider budgets leave time for recording and response completion; this is not an absolute guarantee for an adapter that ignores interruption. Future real provider adapters must implement their own network deadlines. Kubernetes termination grace must exceed the application budget; its configuration is Phase 58.

For dependency incidents, check the private application/Redis/database health and connectivity, restore the dependency, then wait for readiness recovery. Do not restart an otherwise live API merely because a dependency is down. Check a 429 response's retry interval and configured traffic volume before changing quotas. Record intentional quota changes consistently across replicas.

## Required validation and local fixture

Maven tests require a real disposable Redis at `127.0.0.1:56379` (`TEST_REDIS_HOST` / `TEST_REDIS_PORT` override it). PostgreSQL tests start their own disposable native server. CI supplies Redis 7.2.16 and PostgreSQL 16.15; no integration tests silently skip. For a working Docker engine:

```sh
docker run --rm --name ai-platform-redis-test -p 127.0.0.1:56379:6379 redis:7.2.16-alpine@sha256:b5dee736fa6758052556cc97b5d5423177dcd8e26ce9746e6e3d58484a5a4143 redis-server --save '' --appendonly no --maxmemory 64mb --maxmemory-policy noeviction
```

The pinned digest is Linux amd64. On this Windows workstation the Docker engine was unavailable. `python scripts/prepare_redis_test_runtime.py` verifies the official OCI manifest/layer digests and extracts only regular Redis binaries/libraries under the ignored `.maven-cache/redis-7.2.16-root`. The existing Docker Desktop WSL distribution can execute its bundled musl loader with those library paths; the loopback-only, persistence-disabled fixture needs no WSL software installation or configuration changes. The helper downloads/extracts only; it does not start or stop services. Run it before starting the fixture. This fallback does not establish that Docker Compose works.

Tests include 320 concurrent requests through independent Redis connections with exactly 37 admissions, expiry without extending rejected windows, fixed invalid-key state, authenticated limits, oversized/chunked payloads, bounded in-flight capacity, total retry deadlines, and real Redis/database connection interruption/recovery. Fault proxies close only test-owned sockets, not service processes or data. The packaged server smoke also proves actual chunked refusal and idle/trickle timeouts. Phase 57 adds [structured operational logs, bounded metrics and traces](java-observability.md).

References: [Redis atomic rate limiting](https://redis.io/docs/latest/develop/use-cases/rate-limiter/), [Lettuce production guidance](https://redis.io/docs/latest/develop/clients/lettuce/produsage/), [Spring Boot application properties](https://docs.spring.io/spring-boot/appendix/application-properties/).
