# Dashboard Screenshots

## Status

The repository includes dashboard implementations and dashboard definitions, but it does not commit live screenshots from an AWS or Grafana deployment.

Reason:

- No approved live Grafana deployment is created by this repository.
- Screenshots must not expose real account IDs, hostnames, API keys, prompts, users, provider credentials, or incident data.
- The correct portfolio move is to capture screenshots from a seeded local or staging demo environment.

## Screenshot Targets

Application dashboard:

- Next.js dashboard overview
- usage summary cards
- recent gateway requests
- recent gateway failures
- prompt versions
- model routes

Grafana dashboards:

- Production AI Platform Overview
- Production AI Platform Reliability
- Production AI Platform Cost
- Production AI Platform Logs

Operational views:

- GitHub Actions CI run
- deployment workflow summary
- rollback workflow inputs
- Argo CD Applications view if GitOps is installed

## Capture Checklist

1. Use local or staging demo data only.
2. Run migrations and seed data.
3. Generate gateway traffic:

   ```bash
   python scripts/smoke_load.py --requests 20 --concurrency 4
   ```

4. Generate at least one provider failure:

   ```bash
   curl -X POST http://localhost:8000/v1/gateway/completions \
     -H "Content-Type: application/json" \
     -H "X-API-Key: local-dev-placeholder-key-not-a-secret" \
     -d '{"input":"[simulate_failure] screenshot demo"}'
   ```

5. Confirm dashboards have meaningful time ranges and non-empty panels.
6. Redact or avoid:
   - account IDs
   - API keys
   - provider credentials
   - database URLs
   - Redis URLs
   - customer data
   - sensitive prompts
7. Store approved screenshots under:

   ```text
   docs/assets/screenshots/
   ```

8. Update README image links only after approved screenshots exist.

## Current Evidence Without Screenshots

- Web dashboard code: `apps/web/components/dashboard.tsx`
- Web dashboard test: `apps/web/components/dashboard.test.tsx`
- Grafana dashboards: `infra/monitoring/grafana/dashboards/`
- Grafana provisioning: `infra/monitoring/grafana/provisioning/`
- Observability docs: `docs/observability.md`
