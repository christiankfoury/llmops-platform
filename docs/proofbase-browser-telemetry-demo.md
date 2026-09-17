# Proofbase telemetry demonstration

Start the [Java Compose stack](deployment.md). Flyway migration and placeholder local
seeding run through the current Java setup; do not run Alembic in its API container.
Send an invented metadata event from the repository root:

```sh
python scripts/send_proofbase_browser_demo_event.py
```

The sender uses the local placeholder application key and reports synthetic usage.
It does not call an LLM provider or execute the client application. Provider/model
names in the example describe invented reported metadata, not an actual charge.
Use `--help` for supported endpoint and event options.

To inspect the stored event in a browser, configure [operator sign-in and project grants](java-operator-security.md)
for that client scope and use the authenticated dashboard's Source App filter.
The default synthetic dashboard is isolated and will not display this event.

If the sender returns 401, verify the intended local scope/key configuration; do not
re-enable a revoked key or reseed a shared database as a workaround. A 403 in the
operator view requires the correct grant. Never transmit prompts, generated outputs,
documents, workflow JSON, tool payloads or real credentials in a demo event.

[Integration contract](proofbase-integration.md) · [Historical browser evidence](archive/proofbase-browser-telemetry-demo-baseline.md)
