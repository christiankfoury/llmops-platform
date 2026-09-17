# Java usage and operator APIs

Phases 54–55 introduced the Java dashboard query/configuration contract and OIDC project grants. Java is now the default Docker Compose/Helm runtime after the Phase 58 cutover; Python remains a compatibility reference. AWS is not deployed. See [current progress](../phases-progress.md).

## Operator access

Phase 55 replaces the temporary loopback-only identity with OIDC and server-side project grants. Every usage/configuration read requires an authenticated viewer/operator grant for the project; writes require operator. Machine API keys and caller actor headers cannot grant operator access. Access defaults to disabled when identity is unconfigured. See [operator security and setup](java-operator-security.md) for dashboard sessions, grant provisioning, key management and the isolated synthetic demo.

## Usage responses

| Endpoint | Behavior |
|---|---|
| GET /v1/usage/summary | Request count, failed count, average non-null latency, and the sum of linked cost records. Empty results use 0, 0, 0.0 and the decimal string 0.000000. |
| GET /v1/usage/requests | Recent records with the original project/application labels and nullable operational fields. |
| GET /v1/usage/errors | Same record shape, always restricted to failed requests, even if a different status filter is supplied. |
| GET /v1/usage/scopes | Active projects and their active applications; active projects with no active applications remain visible. |

Filters preserve the reference names: project_id, application_id, status, provider, model_name, source_app, operation_type, error_category, created_from and created_to. Text comparisons remain exact. Filters combine with AND; UUIDs and user text are bound parameters. Summary aggregation uses one SQL snapshot and a unique cost-record join, so request counts cannot multiply. Workflow summaries remain request observations with no billed cost; null costs remain null in lists. The durable cost table drives the aggregate.

Requests/errors default to 20 rows and cap limit at 100. Results order by creation time descending, then UUID descending for deterministic ties. Scope labels sort by name, then UUID. JSON decimals remain strings and timestamps preserve microseconds. Responses exclude raw metadata, keys and configured prompt content from usage lists.

Intentional validation changes: duplicate/unknown usage query parameters, invalid UUIDs, nonpositive limits, oversized filter strings and reversed date intervals return safe 422 errors. Dates require an explicit ISO offset and supported years, and truncate sub-microsecond precision like the Python reference. Limits accept bounded positive integer spellings, including values above 100 that are capped. Invalid path UUID conversion retains the safe framework error response.

## Prompt/model controls and audit

Both resource families preserve GET, POST create, PATCH update and POST `/{id}/activate`. Response field names match the Python schemas. Prompt responses include content because these are gateway-managed configuration definitions; client-owned RAG/workflow prompts are not imported. Lists default to and cap at 100 records, using creation time/UUID descending order. A GET limit can request fewer records.

Prompt creation resolves an active project/application, accepts an explicit positive version or allocates the next version, and optionally activates it. Activation deactivates other versions in the same project/application/name. Explicit duplicate versions return 409 without changing existing activation; automatic allocation refuses integer exhaustion. Model defaults are cleared only in the same project/application/environment. Activating a model also marks it active. Repeating activation remains effective. Historical project-wide rows with null application IDs remain updateable within their project.

All configuration mutations acquire the parent project row lock, including empty scopes, before reading/updating versions or defaults. Concurrent requests therefore allocate distinct versions and leave a single active/default record in the relevant scope. Unrelated names, applications and environments are preserved. Bulk deactivation refreshes the target entity before applying its final flag, preventing stale in-memory state from undoing a repeated activation. This intentionally serializes configuration writes within a project; provider execution does not acquire this lock.

Configuration and its audit row commit together in a five-second transaction. Audit failure rolls back new configuration and prior deactivations. Audit metadata records operational configuration identifiers/flags, never prompt content. Project/application deactivation blocks further configuration changes. No destructive delete endpoint is added because the reference API uses deactivation.

Payloads are flat, strict JSON objects with known fields. Duplicate keys, trailing documents, unknown fields and scalar coercion are rejected with safe 422 errors. Bodies are limited to 256 KiB; prompt content to 32,000 Unicode code points, matching the gateway execution limit. NUL/unpaired surrogates are rejected. JSON booleans and positive integers must have their actual types; numeric/boolean strings are not coerced. Optional null patch fields leave the corresponding property unchanged, matching the reference. Oversized bodies return 413. Text defaults, activation/default flags and priority retain the reference defaults.

## Validation and current state

Required PostgreSQL tests cover summary/list field sets, decimal/null fidelity, filters, stable pagination, active scopes, configuration concurrency, cross-application isolation, audit rollback and gateway use of configured resources. Phase 55 adds project authorization and verified audit identity. Existing dashboard contract tests remain in place alongside session/OIDC tests.

The packaged-service smoke uses a temporary signed identity and explicitly provisioned grants. It validates anonymous refusal, the synthetic nine-request summary after gateway/client telemetry ingestion, all six dashboard reads and authenticated prompt creation. Redis readiness/limits, application observability and the Java runtime cutover are implemented. Monitoring finalization and AWS deployment remain blocked; see [observability status](observability.md).
