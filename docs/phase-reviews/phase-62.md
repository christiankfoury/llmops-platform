## Phase 62 Review

Status: **In Progress; vulnerability remediation deferred by the owner on
2026-09-08.** Do not automatically resume fixes or custom third-party rebuilds.
See the [deferred backlog](../security/monitoring-vulnerability-backlog.md) and
[current handoff](../monitoring-remediation.md). Phase 62 remains incomplete;
monitoring release eligibility and all security/cloud approval gates remain held.

The sections below retain the **initial 2026-09-07 audit checkpoint**, before
later local rebuild experiments. They do not describe the final candidate state.
The runtime prototype remains local working-tree work, not an approved or
published monitoring release. Phases 59–61 remain completed; Phase 63 has not started.

### Summary

- A new disposable Compose project ran Java, Prometheus, Grafana, Loki, Alloy,
  OpenTelemetry Collector, Tempo, PostgreSQL/Redis exporters, Alertmanager and a
  bounded synthetic-only alert receiver. Four dashboards returned real data;
  searchable Java logs correlated with stored provider/database spans; a Redis
  outage produced a fired and resolved notification. The project and its own
  newly created volumes were removed afterward. Existing databases were untouched.
- **Ten of eleven proposed upstream monitoring images fail** the enforced
  high/critical vulnerability policy. There were no secret findings. Version
  pins and sanitized results are in [the evidence record](phase-62-evidence.json).
  This prevents phase completion and release of the prototype.
- The default release's previous eleven CI gates passed on `35719e2` (Phase 61).
  Those results do **not** validate these new monitoring images or working-tree
  changes. The new monitoring checks have not been added to required CI yet.

### Scope Check

- In scope: supported log collection, private monitoring, cardinality/retention,
  local operational evidence and an uninstalled dev bootstrap proposal.
- Out of scope avoided: cloud resources or installation, production, real
  secret/DNS/TLS changes, external alert messages, scanner exceptions, custom
  patched third-party distributions, Phase 63 recovery/load/restore work.
- The retained-volume, single-replica EKS proposal is **dev only**. It is not a
  highly available production topology. Production storage/sizing needs a separate
  reviewed design before promotion; no public monitoring Ingress is introduced.

### Files Changed

- Local working tree: `docker-compose.monitoring.yml`, monitoring pins/configs,
  Alloy collection, corrected low-volume error-ratio queries, API log-volume
  preparation, optional Helm log sidecar/CA references and private dev rendering.
- Local validation helpers: monitoring lifecycle/configuration and bootstrap
  security tests. These artifacts remain uncommitted while image validation fails.
- Recorded handoff: this review, its sanitized evidence JSON, `phases-progress.md`
  and roadmap notes. This documentation does not activate the runtime proposal.

### Validation

- Command: build the Java API and migration Docker targets using unique
  `phase62-local` tags.
- Result: both passed. No Java source changed in Phase 62; Phase 61's full CI had
  280 non-skipped Java tests. The new log-directory image ran successfully below.
- Command: `validate_monitoring_stack.py` against those images, in newly owned
  synthetic project `ai-platform-monitoring-test-ba2b9fab1da1`.
- Result: passed. Application metric series: **44**. Populated datasource queries:
  cost **7**, logs **7**, overview **7**, reliability **8**. Time-only/NaN frames do
  not count. Prompt and key sentinels were absent from sampled exported logs and
  traces. Stream labels were only component/environment/service_name.
- Result: main application metrics endpoint returned 404; Grafana datasource
  access without authentication returned 401; every published port was loopback
  only. Redis outage changed readiness to 503 while liveness stayed 200;
  Alertmanager delivered both firing and resolved `LocalJavaNotReady` events.
- Command: pinned Prometheus/Alertmanager/Loki/Collector/Alloy binary config
  checks; strict Kubernetes 1.36 schemas; bootstrap negative input tests.
- Result: configuration checks passed; **56 resources valid, zero skipped**;
  four security-boundary tests passed, including public/broad CIDR and
  credential-bearing hostname rejection. These are offline checks, not live EKS
  RBAC, CNI, TLS, PVC or exporter-credential validation.
- Command: `trivy config --exit-code 1 --severity HIGH,CRITICAL` on the dev render.
- Result: passed, with no high/critical findings. This does not override image
  vulnerabilities or prove runtime authorization.
- Command: `trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed
  --scanners vuln,secret` for every proposed image.
- Result: **failed for ten images**; Redis exporter passed. Counts are package
  findings and may include the same CVE in multiple binaries. Full local reports
  are under `.maven-cache/monitoring-security`; evidence JSON records their hashes.

### Security Review

- Secrets: local fixtures only; Grafana's random synthetic password is not saved
  in evidence. EKS references require approved delivery of credentials, a dedicated
  PostgreSQL monitoring role and collector TLS; none were created or changed.
- Auth: Grafana requires login; EKS services are ClusterIP with default-deny
  network policy. Approved operator port-forward access and actual CNI enforcement
  still need validation. Loki/Tempo have no tenant authentication; network/namespace
  trust and controlled readers are therefore material boundaries.
- IAM/RBAC: proposed collectors have no AWS rights, Ingress writes, secret reads
  or Kubernetes writes. Prometheus/KSM get namespace-limited read discovery only.
  Alloy reads the API's own shared log directory, without a socket or host logs.
- Network: local HTTP endpoints bind loopback, with a private Docker project
  bridge. The bridge is not an outbound firewall. EKS collector ingestion is
  configured for verified TLS; actual cloud certificate and transport validation
  remains outstanding. API-to-Loki and internal datasource traffic use private
  HTTP and depend on cluster network isolation.
- Supply chain: no finding was suppressed. Official latest stable release
  metadata was checked on 2026-09-07. Prometheus
  [v3.13.3](https://github.com/prometheus/prometheus/releases/tag/v3.13.3), published
  that day, fixes x/crypto but its image still fails on CVE-2026-84304 in gRPC
  v1.82.1 (fixed v1.83.1). It was audited as a candidate and not selected.
  [Alertmanager v0.34.0](https://github.com/prometheus/alertmanager/releases/tag/v0.34.0)
  is still the latest stable release checked; its bundled crypto/mod/gRPC libraries
  fail. Other components also have unresolved bundled-library findings. A complete
  supported upstream image set satisfying the policy has not been found.

### Reliability Review

- Health checks: local service readiness and dependency recovery passed.
- Rollback: no cloud rollout occurred. Proposed EKS stores use the existing
  encrypted gp3 `Retain` storage class and five RWO PVCs; Recreate updates have
  deliberate monitoring downtime. PVC deletion, restore, failover and disk-fill
  behavior have not been rehearsed. Retention is not a guarantee against disk full.
- Failure handling: discovery now tolerates Alloy starting before Java's log
  file exists. Local storage is bounded ephemeral memory; logs rotate at 10 MB
  with a 30 MB cap. Alloy limits ingestion and retries; overload/outage can lose
  telemetry. Collector queues and timeouts are bounded.

### Observability Review

- Logs: allowlisted Java JSON and tested correlation, no prompt/output collection.
- Metrics: real committed counters and low-cardinality streams; dev proposal
  discovers every ready API endpoint rather than load-balancing counter scrapes.
- Traces: native Java provider/database spans reached Tempo through the Collector;
  cloud TLS validation and sustained retention remain outstanding.
- Dashboards: all four provisioned dashboards returned data through Grafana's
  datasource API. No screenshots or AWS operational evidence are claimed.
- Alerts: local firing/resolved delivery proved; external receivers remain
  intentionally unconfigured until separately approved.

### Risks / Follow-ups

- Obtain supported patched upstream images, audit their exact digests, repeat
  compatibility/runtime checks, then add mandatory CI scanning and lifecycle
  evidence. Rebuilding several upstream distributions with dependency overrides
  introduces a new maintenance and compatibility burden; no such unreviewed
  replacement was adopted just to pass the scanner.
- Finish cloud package transport/storage/exporter validation and documentation,
  then review and commit/push the validated Phase 62 implementation. Do not use
  this prototype for deployment while the phase is held.
- The stop follows AGENTS.md: validation cannot currently be completed safely
  with the proposed supported upstream image set. No exception approval is sought.

### Post-Commit Review

- Phase 62 implementation commit: none; vulnerable artifacts remain local.
- Top findings: runtime startup race fixed locally; initial Docker internal
  network prevented host publication and was corrected; timestamp-only Grafana
  frames no longer count; image vulnerabilities remain the blocking finding.
- Fix commits: none for Phase 62. Its commit/review loop is not complete.

### Next Phase

- Phase 62 remains In Progress. Phase 63 starts only after this gate is resolved.
