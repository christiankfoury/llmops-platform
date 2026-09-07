# Java gateway implementation

Phase 52 implements `POST /v1/gateway/completions` in the Java service. AWS remains the target, while Docker Compose/Helm still run the Python reference until Phase 58. The Java endpoint uses a local mock adapter; it requires no provider credentials and makes no external model calls.

## Request and response

Supply `X-API-Key` for the active application. Keys are looked up by their SHA-256 UTF-8 hash; absent, invalid, inactive or revoked keys and inactive applications return 401. Keys over 512 characters are rejected before database lookup. The request shape is:

```json
{"input":"synthetic hello","prompt_name":"default-chat","environment":"local"}
```

`prompt_name` and `environment` have the shown defaults when omitted; explicit null is invalid. Input is limited to 8,000 Unicode code points, prompt name to 160, and environment to 40. Unknown JSON fields, malformed bodies and non-string text fields return safe 400 errors; field validation returns 422 with snake_case locations and no rejected content. Valid correlation headers use at most 128 ASCII letters/digits/dot/underscore/hyphen, starting with a letter or digit. Other values are replaced by a generated `http_` ID. The response returns the correlation header and a separate persisted `req_` business ID, preserving the original distinction.

For an already migrated disposable loopback database, explicitly enable `SEED_LOCAL_DATA=true` and `ENVIRONMENT=local` at Java startup to create the documented local placeholder scopes. See the [database guide](database-migration-handover.md). The demo key is the synthetic `local-dev-placeholder-key-not-a-secret`, never a production credential.

Successful responses preserve the Python field names: request_id, status, provider, model, output, prompt_version, latency_ms, input_tokens, output_tokens and estimated_cost_usd. Cost remains a six-place decimal JSON string. Whitespace token counts are synthetic estimates; mock pricing uses decimal arithmetic and half-up rounding. For the default seeded prompt and `synthetic hello`, the fixture expects 13 input tokens, 16 output tokens and `"0.000005"`.

## Routing and persistence

Configuration is scoped to the authenticated project/application. Select the highest active prompt version. Active routes match the requested environment; default routes win, then lower priority, then UUID for a deterministic tie break. Missing prompts/routes return 404. Only `mock` / `mock-llm-small` is supported now. Unsupported routes return 404 instead of receiving mock output/pricing under a real-provider label. Configured prompt content is bounded to 32,000 code points for execution.

Authentication/configuration resolution uses a short read transaction. Provider waits hold no database connection. A successful request and its single cost record commit in one transaction; cost-write failure rolls back the request. Provider failures/timeouts commit one operational failure record with no cost, then return a safe HTTP error. Input text, configured prompt content and output text are not stored in request/cost records or written to application logs. Gateway-managed prompt definitions remain in their existing configuration table; this does not move Proofbase RAG or AgentOps workflow prompts into this platform.

## Execution bounds

| Setting | Default | Supported bound |
|---|---:|---|
| `PROVIDER_MAX_ATTEMPTS` | 2 | 1-3 |
| `PROVIDER_TIMEOUT_SECONDS` | 15 | Per-attempt deadline, at most 60 seconds |
| `PROVIDER_RETRY_BACKOFF_MS` | 100 | 0-1,000 milliseconds |
| `PROVIDER_CONCURRENCY` | 8 | 1-32 workers, with a queue of the same bounded size |

Queue wait counts toward the attempt deadline. Timeout/interruption cancels the task and removes canceled queued work. A full worker/queue capacity returns 503; retries are bounded for provider errors/timeouts. Mock markers `[simulate_transient_failure]`, `[simulate_failure]` and `[simulate_timeout]` exercise success-after-retry, 502 and 504 behavior. Unexpected provider diagnostic text is discarded. Thread interruption cannot forcibly stop an adapter that ignores it; such work remains bounded by worker capacity. A future real adapter must supply its own network timeouts/cancellation and retry policy.

Distributed API-key rate limits are Phase 56; full metrics/logs/traces are Phase 57. This phase does not yet provide the reference API's 429 admission response. Operator authorization and public readiness remain later gates. Do not treat a passing local gateway test as cloud deployment evidence.

## Validation

Required Java tests use real disposable PostgreSQL and cover HTTP success, missing/invalid/inactive/revoked keys, inactive applications, scoped prompt/route selection, missing/unsupported configuration, transient retries, timeout/failure persistence, decimal cost, Unicode limits, safe errors/correlation, cost rollback, connection release during provider waits, actual timeout cancellation and bounded overload. CI starts the packaged migration/app JARs with explicit synthetic loopback seeding and performs an authenticated completion. No test calls a real provider.
