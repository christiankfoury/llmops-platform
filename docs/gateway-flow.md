# Gateway Flow

This document explains the application-level flow for the LLM gateway. It is meant to help a developer understand what happens when a client app calls the platform instead of calling OpenAI or another model provider directly.

The short version:

```text
Client app
  -> POST /v1/gateway/completions
  -> API key authentication
  -> project/application lookup
  -> prompt lookup
  -> model route lookup
  -> provider call
  -> request/cost logging
  -> response
```

Today the provider call uses the local mock provider. The structure is intentionally designed so a real OpenAI provider adapter can replace that mock while keeping the same authentication, routing, logging, metrics, and dashboard behavior.

## Main Files

The gateway is split into a thin API route and a service layer:

```text
apps/api/app/api/gateway.py
apps/api/app/services/gateway.py
apps/api/app/services/mock_provider.py
apps/api/app/services/pricing.py
apps/api/app/schemas/gateway.py
```

The database records involved in the gateway flow are defined in:

```text
apps/api/app/models/identity.py
apps/api/app/models/routing.py
apps/api/app/models/gateway_request.py
apps/api/app/models/cost_record.py
```

## Request Shape

The gateway endpoint is:

```text
POST /v1/gateway/completions
```

The client sends an API key in the request header:

```http
X-API-Key: local-dev-placeholder-key-not-a-secret
```

The request body uses `CompletionRequest`:

```json
{
  "input": "hello from my app",
  "prompt_name": "default-chat",
  "environment": "local"
}
```

Only `input` is required. If the caller does not send a prompt name or environment, the API uses:

```text
prompt_name = default-chat
environment = local
```

The response uses `CompletionResponse`:

```json
{
  "request_id": "req_...",
  "status": "succeeded",
  "provider": "mock",
  "model": "mock-llm-small",
  "output": "...",
  "prompt_version": 1,
  "latency_ms": 15,
  "input_tokens": 12,
  "output_tokens": 24,
  "estimated_cost_usd": "0.000005"
}
```

## Step 1: Route Receives The Request

The route handler lives in `apps/api/app/api/gateway.py`.

Its job is intentionally small:

1. Read the JSON body.
2. Read the `X-API-Key` header.
3. Reject missing keys.
4. Apply rate limiting.
5. Call the service-layer gateway function.
6. Convert known gateway errors into HTTP responses.

This keeps HTTP concerns in the route and business logic in the service.

## Step 2: API Key Authentication

The service hashes the incoming API key and looks for an active matching row in `api_keys`.

Conceptually:

```text
raw API key
  -> hash_api_key(...)
  -> api_keys.key_hash lookup
  -> active, non-revoked key required
```

The database stores the hash, not the raw key. That matters because a database leak should not immediately expose usable API keys.

If no matching key exists, the API returns:

```text
401 Invalid API key
```

## Step 3: Project And Application Lookup

An API key belongs to an application:

```text
api_keys.application_id -> applications.id
```

An application belongs to a project:

```text
applications.project_id -> projects.id
```

So the API key identifies the calling app and its parent project.

That gives the platform useful operational context:

```text
Which app made the request?
Which project owns it?
Which app should receive cost attribution?
Which app had errors or latency spikes?
```

This is why the gateway is more useful than a direct provider call. It centralizes operational visibility across multiple client apps.

## Step 4: Prompt Version Lookup

The request can include a `prompt_name`.

The gateway looks for an active prompt version scoped to the same project and application:

```text
project_id
application_id
prompt_name
is_active = true
```

If multiple versions exist, the gateway chooses the newest version.

This allows prompts to be managed centrally. A client can ask for `default-chat` without needing to hardcode the full prompt text.

If no active prompt is found, the API returns:

```text
404 No active prompt version found
```

## Step 5: Model Route Lookup

The gateway then chooses the model route for the request environment.

The route lookup uses:

```text
project_id
application_id
environment
is_active = true
```

Routes are ordered so default routes win first, then lower priority numbers win:

```text
is_default desc
priority asc
```

In local development, the seeded route is:

```text
provider = mock
model_name = mock-llm-small
environment = local
```

Later, a real production route could look like:

```text
provider = openai
model_name = gpt-4.1-mini
environment = prod
```

The client app does not need to know the actual provider/model decision. It calls the platform, and the platform decides.

If no active route is found, the API returns:

```text
404 No active model route found
```

## Step 6: Provider Call

The gateway currently calls the mock provider in:

```text
apps/api/app/services/mock_provider.py
```

The mock provider returns:

```text
output
input token estimate
output token estimate
```

It can also simulate failures for testing:

```text
[simulate_failure]
[simulate_timeout]
[simulate_transient_failure]
```

The gateway wraps the provider call with bounded retry behavior. A transient failure can be retried, but repeated provider failures are recorded and returned as an error response.

This is the main future integration point. To connect the platform to OpenAI, add a real provider adapter and route `provider = openai` through that adapter.

External apps that already call providers directly should not be forced through this provider-call path immediately. The telemetry-first integration defined in [external-telemetry-contract.md](external-telemetry-contract.md) lets apps keep their own provider calls and send sanitized usage events to the platform for centralized visibility.

## Step 7: Cost And Token Calculation

After a successful provider call, the gateway estimates cost.

The pricing helper is:

```text
apps/api/app/services/pricing.py
```

For now, pricing is static and mock-oriented. The local goal is to demonstrate the shape of cost attribution:

```text
provider
model
input tokens
output tokens
estimated USD cost
```

When a real OpenAI adapter is added, this should be refreshed to use real token counts and current model pricing.

## Step 8: Request And Cost Persistence

On success, the gateway writes two records:

```text
gateway_requests
cost_records
```

`gateway_requests` stores the request lifecycle record:

```text
request_id
project_id
application_id
api_key_id
prompt_version_id
model_route_id
provider
model_name
status
latency_ms
estimated_input_tokens
estimated_output_tokens
estimated_cost_usd
created_at
```

`cost_records` stores cost attribution:

```text
gateway_request_id
project_id
application_id
provider
model_name
input_tokens
output_tokens
estimated_cost_usd
currency
```

On provider failure, the gateway still writes a `gateway_requests` row with:

```text
status = failed
error_category = provider_error or provider_timeout
```

That means failures still appear in the dashboard and metrics.

## Step 9: Metrics, Logs, And Traces

The gateway emits operational signals while handling the request.

Metrics include:

```text
request count
error count
latency
token totals
estimated cost
auth failures
rate-limit rejections
```

Traces include spans for:

```text
gateway.request
gateway.auth
gateway.prompt_lookup
gateway.model_routing
gateway.provider_call
gateway.database_write
gateway.response_serialization
```

This is one of the main reasons the project exists. The value is not just calling a model; the value is seeing how model traffic behaves in production.

## How The Dashboard Uses This Data

The dashboard does not call the provider directly.

It reads usage data from:

```text
GET /v1/usage/summary
GET /v1/usage/requests
GET /v1/usage/errors
GET /v1/usage/scopes
```

Those endpoints read the records written by the gateway. That is how the dashboard can show:

```text
request volume
latency
cost
failures
project/application filters
provider/model filters
request detail drilldowns
```

Phase 32 external telemetry ingestion also writes accepted external events into the same request and cost tables, with external event fields that identify source app, operation type, external event ID, and external request ID. This means external app traffic can appear in usage summaries before those apps route provider calls through the gateway.

## Local Example

Start the stack:

```bash
docker compose up --build
```

Run migrations and seed data:

```bash
make api-migrate
make api-seed
```

Send a successful request:

```bash
curl -X POST http://localhost:8000/v1/gateway/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-placeholder-key-not-a-secret" \
  -d '{"input":"hello from local development"}'
```

Send a simulated provider failure:

```bash
curl -X POST http://localhost:8000/v1/gateway/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-placeholder-key-not-a-secret" \
  -d '{"input":"[simulate_failure]"}'
```

Open the dashboard:

```text
http://localhost:3000
```

The successful request should appear in recent requests. The simulated failure should appear in recent failures.

## Current Limitation

The gateway has the production shape, but the provider is still mocked.

Proofbase integration phases intentionally start with external telemetry ingestion rather than gateway-routed provider calls. That keeps Proofbase's retrieval, citation, permission, and answer-quality behavior outside this repository while still making cost, latency, token, request, and error signals visible in the platform.

Current flow:

```text
client app -> gateway -> mock provider
```

Target future flow:

```text
client app -> gateway -> OpenAI
```

The next meaningful product milestone is to add a real OpenAI provider adapter while preserving the same gateway responsibilities:

```text
auth
project/app attribution
prompt lookup
model routing
retry/timeout handling
request logging
cost tracking
metrics
dashboard visibility
```
