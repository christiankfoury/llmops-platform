# Java client telemetry ingestion

Phase 53 introduced `POST /v1/usage/llm-events` for Proofbase and AgentOps. Java is now the default Docker Compose/Helm runtime; Python remains a compatibility reference. AWS is not deployed. This endpoint receives operational metadata. It neither executes client workflows nor handles RAG documents, prompts, generated answers, or tool payloads.

## Authentication and attribution

Send an active, unrevoked application key in `X-API-Key`. The stored project/application registration determines the source:

| source_app | Project slug | Application slug |
|---|---|---|
| proofbase | proofbase | enterprise-knowledge-agent |
| agentops | agentops | agentops-workflow-platform |

Missing/invalid/revoked keys and inactive applications return 401. A valid key for another source, including the local gateway demo key, or a disabled project returns 403. Proofbase accepts rag_query, rag_query_stream, markdown_cleanup, query_decomposition and embedding_generation; AgentOps accepts agent_step, structured_generation and workflow_summary. Source-incompatible operations return 422. These registrations are the existing client scopes, not caller-provided project IDs. Local seeding is explicitly opt-in and restricted to disposable loopback development databases; see [migration handover](database-migration-handover.md).

## Payload and replay compatibility

The nine frozen Python fixtures and eight captures from the actual client builders/sanitizers pass the Java HTTP tests. The actual AgentOps helper emits `agent_step` with a text or structured_json response_type; both are accepted, along with the existing structured_generation operation. Captures contain synthetic values only, fixed timestamps/UUIDs and hashes of the inspected client source files. No client payload or source was changed.

Normalized fingerprints retain Python's sorted compact ASCII JSON, null/default fields, Unicode escaping and key ordering, shortest floating-point representation, decimal scale/exponent, and microsecond timestamps including their original offset. Python's [JSON documentation](https://docs.python.org/3/library/json.html) explains the encoding options; executable vectors captured from this project's Python reference are authoritative. Decimal amounts round half-even to six places, preserving the legacy rule. The golden fixtures and 141 additional JSON vectors test these details. Same-instant timestamps with a different original offset still constitute different payloads, as in the reference.

Successful ingestion returns 202 with accepted, duplicate, request_id, external_event_id, external_request_id, project_id, application_id and status. Matching replays return the original request ID. A reused event ID with different normalized content returns 409. Historical rows without a verifiable fingerprint also return 409; they are never silently overwritten or recharged.

## Input limits and intentional stricter behavior

- The endpoint reads at most 32 KiB plus one byte; excess bodies return 413 even without Content-Length. Duplicate JSON keys, trailing documents, non-object bodies, unknown top-level fields, ambiguous model/model_name aliases and invalid values return safe 422 errors without echoing inputs.
- Metadata is a flat allowlisted object, at most 20 entries and 2,048 bytes in compact ASCII JSON. Strings are at most 240 Unicode code points; numeric metadata must be finite and have magnitude at most 1e12. Nested objects/arrays, unapproved fields, NUL and unpaired surrogates are rejected.
- Token/latency fields require nonnegative JSON integers within PostgreSQL's 32-bit range. Numeric strings, booleans and floating-point token counts are rejected. When supplied together, token totals must match.
- Money is nonnegative finite USD, bounded by numeric(12,6) after rounding. Numeric spelling/scale bounds prevent excessive decimal work. Dates require an ISO offset, years 1-9999 and Java-supported offsets; sub-microsecond precision is truncated consistently. Failed events require a nonblank safe error category.
- A workflow_summary cannot carry cost or token values, including zero, or claim estimated/cached pricing. Summaries store operational status with unknown/unpriced amounts and create no cost row.
- Missing cost stays SQL NULL. Missing pricing is inferred as unknown when cost is absent and estimated when an amount is supplied. An estimated label without an amount is stored as unknown. This reporting correction does not alter the original normalized replay fingerprint.

The metadata allowlist blocks raw content fields. Producers still own redaction of the permitted operational strings; a field named error_message_redacted is not proof that arbitrary supplied text is safe. The platform does not log event bodies, API keys, client diagnostics or identifiers as metric labels.

## Atomicity and instrumentation

The existing unique application/event constraint arbitrates concurrent writes using PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`. The subsequent read sees the committed winner. A matching loser returns duplicate; a conflicting loser returns 409. Both statements and the optional cost insert share one five-second transaction. Cost failure rolls back the event and permits a later clean retry. Schema V1 is unchanged. No exception-driven duplicate path logs rejected database values.

Bounded telemetry event/error/cost/token counters increment after the transaction returns. Only a newly committed event contributes cost or tokens; duplicates, validation failures and rolled-back writes do not. Source and operation labels come from finite sets; arbitrary error categories collapse to other. Model names, IDs and operational strings never become labels. These are process counters rather than a durable billing ledger; a process crash after database commit can miss a metric increment. Full Prometheus exposure, tracing and structured logs arrive in Phase 57; database queries remain the durable usage source.

Client sending remains optional and best-effort in the unchanged client helpers. Receiver errors/timeouts do not become workflow failures. Distributed admission limits, operator access control and the Java runtime cutover are implemented. Live AWS evidence remains outstanding; see [current progress](../phases-progress.md).

## Reproducing validation

Run the Java Maven Wrapper `clean verify`; its required PostgreSQL tests cover fixture parity, authentication, source binding, concurrent identical/conflicting retries, rollback, nonbillable summaries, bounds, privacy and label cardinality. CI also starts the packaged migration/application JARs, sends all eight real-helper captures and replays each one.

Regenerate captures only when deliberately updating the client contract. With the Python reference dependencies installed, run:

```powershell
.venv/Scripts/python.exe scripts/capture_client_telemetry_contract.py --client proofbase --client-root S:/github-repos/enterprise-knowledge-agent --check
.venv/Scripts/python.exe scripts/capture_client_telemetry_contract.py --client agentops --client-root S:/github-repos/agentops-workflow-platform --check
.venv/Scripts/python.exe scripts/export_backend_contract.py --check
```

The capture uses actual builders/sanitizers with an in-memory sender, overrides database/provider settings, and imports from an empty temporary working directory. It does not read client .env files or send network requests. CI consumes the committed captures without needing either private client checkout.
