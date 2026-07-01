# Dashboard Screenshots

Phase 21 adds the Grafana dashboard definitions before any live Grafana deployment exists.

After Grafana is deployed and connected to Prometheus, capture recruiter-facing screenshots for:

- Production AI Platform Overview
- Production AI Platform Reliability
- Production AI Platform Cost
- Production AI Platform Logs

Store final screenshots under a future documentation asset folder, such as:

```text
docs/assets/grafana/overview.png
docs/assets/grafana/reliability.png
docs/assets/grafana/cost.png
docs/assets/grafana/logs.png
```

Screenshot checklist:

- Generate sample gateway traffic first so request, latency, cost, token, and model panels are populated.
- Verify the dashboard time range shows meaningful data.
- Avoid exposing real hostnames, account IDs, API keys, user data, or provider credentials.
- Prefer staged or demo data over production customer data.
- Update the final README to embed the screenshots only after the images exist.
