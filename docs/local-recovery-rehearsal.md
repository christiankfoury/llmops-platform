# One local resilience and recovery rehearsal

Phase 63 plan: reuse the Java Compose runtime, existing synthetic seeds, load
helper and schema verifier. Measure one 20-request/four-worker sample, Redis
outage/recovery, graceful API stop/start, a compatible image replacement and a
quiesced PostgreSQL dump restored into a new service. Validate durable rows and
one request on the recovered database. Do not run deferred monitoring images.

## Repeat from a clean checkout

Use Docker Desktop/Linux containers and Python 3.12. Run from the repository root.
Build from the clean checkout, not the preserved Phase 62 prototype. These two
source revisions have identical `apps/api-java`, `contracts` and `.dockerignore`
inputs. This is an explicit compatible release/revert exercise with distinct
image IDs/revision labels, not a behavioral or schema downgrade. If those inputs
change, select and validate an appropriate compatible pair before using this guide.

```sh
git diff --exit-code 1737899a576b7e4bb6c679d1e64b49b6e8d54047 a291ad7a7083217aa76b3b2a78eb00b36de076f9 -- apps/api-java contracts .dockerignore
docker build -f apps/api-java/Dockerfile --target api --label org.opencontainers.image.revision=a291ad7a7083217aa76b3b2a78eb00b36de076f9 -t production-ai-platform-api:phase63-candidate .
docker build -f apps/api-java/Dockerfile --target api --label org.opencontainers.image.revision=1737899a576b7e4bb6c679d1e64b49b6e8d54047 -t production-ai-platform-api:phase63-rollback .
docker build -f apps/api-java/Dockerfile --target migration -t production-ai-platform-migration:phase63 .
python scripts/rehearse_local_recovery.py
```

Keep the current mandatory CI and image audits; Docker build's package step skips
tests and is not a substitute for Maven verification against PostgreSQL/Redis.
The script resolves local image IDs before starting, verifies exact revision
labels and equivalent app inputs, ignores personal `.env`, assigns loopback-only
ports and refuses an existing Compose project. It has no endpoint/credential
option for an existing database. The API/operator defaults keep writes protected;
only the synthetic application's placeholder machine key sends mock requests.

## Evidence and recovery boundary

The command prints `.maven-cache/ai-platform-recovery-<unique-id>/evidence.json`.
That folder contains its empty environment file, Compose override and synthetic
dump. The [retained summary](archive/phase-reviews/phase-63-evidence.json) includes:

- Client-observed min/mean/nearest-rank p95/max latency, request/error counts and
  concurrency. Twenty requests are a short sample, not a capacity estimate.
- Redis outage readiness 503, liveness 200, rejected gateway 503 with no durable
  request added; measured recovery through a successful gateway request.
- Graceful stop exit code, restart timing, exact rollback image, and unchanged
  Flyway V2 history. Rollback uses `verify-schema`; no migration downgrade runs.
- A quiesced binary dump, new empty target, exact per-table counts/hashes and a
  successful new API write. Backup/restore command times are separate from target
  startup/API verification. There are no writes during backup; this does not
  measure point-in-time recovery or a cloud data-loss window.

Only the synthetic fixture is stopped in `finally`. Both database volumes remain
if created. No `down --volumes`, `dropdb`, cloud call or destructive migration is
part of the rehearsal. Preserve failed-attempt evidence, fix the failed check and
repeat only as needed; unchanged successful checks need no benchmark campaign.

Prometheus/Grafana/Loki/trace/alert runtime checks remain deferred under Phase 62.
The dated monitoring prototype evidence is not final image eligibility or a
passed current alert-resolution check. AWS backup configuration and the single
approved deployment demonstration belong to Phase 66.
