# Java migration compatibility contract

Phase 49 freezes the Python reference before the Spring Boot implementation. The committed files under `contracts/python-baseline/` contain source-derived schemas and synthetic fixtures only. They are a compatibility target, not evidence of a live AWS installation or authorization to apply SQL to an existing database.

## Reproduce and check

From the repository root, with `apps/api/requirements.txt` installed:

```powershell
.venv\Scripts\python.exe scripts/export_backend_contract.py --check
.venv\Scripts\python.exe -m pytest apps/api/tests/test_migration_contract.py
```

The exporter runs Alembic in offline SQL mode and disables tracing. It does not connect to PostgreSQL, Redis, AWS, or an LLM provider. Running without `--check` updates the six generated artifacts; review every change rather than regenerating merely to clear a failing check. `telemetry-fixtures.json` is the hand-authored input. CI runs drift detection and requires the PostgreSQL fixture lifecycle test with `REQUIRE_DATABASE_TESTS=true`. A local database skip is not database validation.

| Artifact | Purpose |
|---|---|
| `openapi.json` | Existing route, parameter, response, and validation schemas |
| `telemetry.schema.json` | Actual Pydantic event schema; the current raw-dictionary route omits it from OpenAPI |
| `database-metadata.json` | PostgreSQL column types/nullability, constraints, foreign-key delete actions, indexes |
| `alembic-schema.sql` | Offline migration history through the current head, including Alembic ownership |
| `metrics.json` | Source-defined metric names, types, labels, and histogram boundaries |
| `telemetry-fixtures.json` / `telemetry-golden.json` | Eight safe operation examples, normalization, fingerprints, persisted metadata and costs |

## HTTP behavior

All application routes use the existing `/v1` prefix. JSON names remain snake_case, UUIDs remain strings, optional response fields remain visible as `null`, and a valid `X-Request-ID` is returned on responses. The separate generated OpenAPI file is authoritative for individual field lengths and types.

| Route | Methods and baseline behavior |
|---|---|
| `/health`, `/health/live`, `/health/ready` | GET 200; readiness returns 503 during shutdown but currently only checks whether dependency URLs are configured |
| `/metrics` | GET Prometheus text; intentionally omitted from OpenAPI |
| `/v1/gateway/completions` | POST 200 completion; 401 absent/invalid/inactive key scope; 404 missing prompt/route; 422 validation; 429 rate limit; 502 provider error; 504 provider timeout |
| `/v1/usage/llm-events` | POST 202 new or identical duplicate event; 401 key failure; 409 conflicting duplicate; 422 invalid or forbidden telemetry |
| `/v1/usage/summary` | GET 200 counts, average latency and estimated cost |
| `/v1/usage/requests`, `/v1/usage/errors` | GET 200 newest-first records; default limit 20, minimum 1, values over 100 capped at 100; errors forces failed status |
| `/v1/usage/scopes` | GET 200 active project/application choices ordered by name |
| `/v1/admin/prompt-versions`, `/v1/admin/model-routes` | GET 200; POST 201 create; invalid scope returns 404 |
| `/v1/admin/prompt-versions/{prompt_id}`, `/v1/admin/model-routes/{route_id}` | PATCH 200 update; missing record returns 404 |
| Both admin `/{id}/activate` routes | POST 200 activation; missing record returns 404 |

Usage filters combine project_id, application_id, status, provider, model_name, source_app, operation_type, error_category, created_from and created_to. Date bounds are inclusive. Empty summaries return zero counts/latency and `"0.000000"` cost. Authentication currently covers gateway and telemetry keys only. Admin and usage read endpoints are unauthenticated in the reference; `X-Actor-ID` is caller-supplied. These weaknesses must not survive the public cutover.

Ordinary HTTP errors have `{"detail":"message"}`. Validation errors have a `detail` array with locations and error types. Preserve status and useful field locations, but do not preserve Pydantic-specific URLs, raw rejected values, exception strings, or stack traces in Java. Some current validation errors echo rejected content; safe error responses are an intentional change.

## Gateway and operator configuration

Keys use the SHA-256 hexadecimal digest of the UTF-8 key. Active, unrevoked keys resolve an active application. Prompt selection and default routing follow `app/services/gateway.py`; the existing admin tests prove newly activated prompts/routes affect gateway requests and emit audit records. Port scope and ordering explicitly; do not rely on unspecified database row ordering.

The mock adapter combines configured prompt content and synthetic input, estimates whitespace-separated tokens (minimum one), and supports failure, timeout, and first-attempt transient-failure markers. No actual provider call is required. Gateway success, retry, failure persistence, filters and operator creation remain covered by `test_gateway.py` and `test_admin_config.py` against PostgreSQL. The new migration tests separately fix the HTTP error envelope, status mapping, decimal representation and rate-limit boundary.

## Money, dates and duplicate events

- Database money is `NUMERIC(12,6)`. Wire money is a JSON string. Do not convert financial arithmetic through binary floating point. Gateway mock pricing rounds half-up to six places; external telemetry currently rounds half-even. Tests record both rules.
- Missing cost stays `null` and creates no cost record. A known zero cost is distinct. Safe workflow summaries omit cost and token counts; unpriced embeddings omit cost. The fixture lifecycle checks both cases against PostgreSQL.
- Event dates require a timezone; the original microsecond instant becomes `created_at` and `updated_at`. PostgreSQL stores an instant; compare offsets by instant. Pydantic's normalized fingerprint representation uses `Z` for UTC while persisted metadata uses `+00:00`.
- Duplicate identity is `(application_id, external_event_id)`, enforced by a unique constraint. An identical replay returns 202 with `duplicate=true` and the same request_id, without adding cost. A changed normalized payload returns 409. Concurrent insertion currently has an unhandled race; transactional conflict recovery is a required Java improvement.
- Existing fingerprints hash the full validated payload with aliases, explicit nulls and defaults, sorted keys, compact separators, Python ASCII JSON escaping, and SHA-256. Decimal strings retain their input scale. Golden vectors capture this representation. Existing rows require compatible replay checking or a separately versioned, tested adoption path; Java's default JSON serializer is not interchangeable.

## Telemetry privacy and source boundaries

Fixtures cover `rag_query`, `rag_query_stream`, `markdown_cleanup`, `query_decomposition`, `embedding_generation`, `agent_step`, `structured_generation`, and `workflow_summary`. They include success, failure, skipped/cached, unknown and unpriced events. AgentOps currently also identifies structured work as `agent_step` with `response_type=structured_json`; do not require a client switch to `structured_generation`.

Unknown top-level fields and forbidden metadata keys are rejected. Metadata uses the existing allowlist, at most 20 scalar entries and bounded strings. No prompts, output bodies, document text, workflow payloads, tool arguments/results, or credentials belong in telemetry. Fixtures use invented identifiers and operational metadata. Golden files contain no real client data. Read both actual client implementations again before Phase 53; fixtures do not replace that requirement.

## Database ownership and planned intentional changes

The schema has application-generated UUIDs and timestamps rather than database defaults. Preserve foreign-key `RESTRICT`, `CASCADE`, and `SET NULL` behavior, JSONB, uniqueness and indexes. Offline Alembic SQL is historical evidence; never execute it as an existing-database adoption shortcut. Phase 51 must prove fresh creation and a verified copy of the Alembic database converge before Flyway owns migrations. Never run Alembic and Flyway together or enable automatic schema updates.

| Planned change | Phase | Compatibility implication |
|---|---|---|
| Race-safe ingestion, enforce non-billable summaries, bound telemetry values | 53 | Reject unsafe/oversized or double-counting events, retain valid client events |
| Verified operator identity, project grants, key lifecycle and audit attribution | 55 | Admin/usage calls require authentication; ignore caller-spoofed actor identity |
| Redis admission controls and real dependency readiness | 56 | Controlled 429/503 during overload/outages, without making liveness dependency-sensitive |
| Safe errors/logs, bounded metric labels, valid correlation IDs | 50/53/57 | Never echo rejected payloads; metric names/labels retained where safe, label values bounded |
| Java runtime cutover and supported web CORS methods | 58 | Dashboard uses authenticated operator calls; browser PATCH preflight must work |

The current API does not enforce non-billable summaries if a caller supplies a cost, does not check active project status during key resolution, and accepts unbounded metric label values. Those are documented gaps, not compatibility guarantees. Keep the Python reference private/local until the controls and cutover criteria pass.
