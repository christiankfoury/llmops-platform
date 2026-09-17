# Five-minute local walkthrough

Use the [README startup commands](../README.md#run-locally), synthetic data and the
mock provider. No AWS environment, provider account or real user data is needed.

1. **Gateway:** send the example completion and show its request ID, model and usage.
   Explain that Java persists request/cost metadata and Redis enforces limits.
2. **Dashboard:** show the overview, filter by project/source/status, and open one
   request. Point out the synthetic/read-only label. These are fixed examples,
   separate from the request just sent. API-backed usage requires operator sign-in.
3. **Security and delivery:** show current CI, PostgreSQL/Redis integration coverage,
   image/dependency/secret scans and verified OCI promotion. Explain project grants,
   separate migration/application identities and schema-compatible rollback.
4. **Recovery:** show the [measured local rehearsal](archive/phase-reviews/phase-63.md):
   20/20 requests, Redis recovery, restart, compatible rollback and 24 restored
   request/cost records. Explain the small sample and local-only limits.
5. **Infrastructure:** show the Terraform/Helm design and the AWS checklist.
   AWS is not deployed. Monitoring finalization remains blocked; static configuration
   is not cloud operating evidence. Separate staging/prod environments are optional.

The [screenshot gallery](dashboard-screenshots.md) supports an offline walkthrough.
Use the actual application and retained CI/recovery evidence; do not present synthetic
values as measurements or show credentials, customer data or raw provider content.
