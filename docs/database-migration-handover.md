# PostgreSQL migration ownership

Phase 51 introduces Java JPA mappings and a Flyway V1 schema equivalent to the Python Alembic head `0002_external_telemetry`. Python remains the deployed runtime until Phase 58. The eight application tables keep their names, UUID identifiers, JSONB data, `numeric(12,6)` money, timestamp precision, foreign keys, indexes and uniqueness rules. Hibernate uses `validate`, never schema creation/update. Runtime Flyway execution is disabled by default; a separate executable migration JAR owns explicit changes.

## Fresh disposable database

Build from `apps/api-java` with `./mvnw --batch-mode --no-transfer-progress --strict-checksums clean verify` (`.\mvnw.cmd` on Windows). Provide these environment settings through your local shell or secret delivery mechanism, without putting real credentials in commands, source files or logs:

| Setting | Meaning |
|---|---|
| `JDBC_DATABASE_URL` | PostgreSQL JDBC URL; use a disposable loopback database for rehearsal |
| `DATABASE_USERNAME` / `DATABASE_PASSWORD` | Database credentials; the CLI requires both explicitly |
| `DATABASE_SCHEMA` | Dedicated lowercase application schema, default `public` |
| `DATABASE_MIGRATIONS_ENABLED` | Runtime migration switch; defaults to `false`, tests explicitly enable it |
| `ENVIRONMENT` | Defaults to `local`; cloud environments use their explicit name |
| `SEED_LOCAL_DATA` | Defaults to `false`; synthetic startup seeds require explicit opt-in, `local`, and a loopback JDBC host |

For a new, empty, disposable schema, run:

```text
java -jar target/production-ai-platform-api-0.1.0-SNAPSHOT-migration.jar migrate
java -jar target/production-ai-platform-api-0.1.0-SNAPSHOT.jar
```

The application and CLI share `DATABASE_SCHEMA`. Both Java entrypoints require exactly one explicit schema and the standard `flyway_schema_history` table; custom history names, extra managed schemas or an implicit default schema are refused so the Python guard cannot miss ownership. Starting the app against an unmigrated database fails validation. Never add `ddl-auto=update`, `baseline-on-migrate=true`, Flyway clean, or an automatic downgrade to work around a failure. The migration entrypoint holds a PostgreSQL session advisory lock matching the guarded Python Alembic runner. Lock acquisition times out after five seconds and restores its connection settings afterward. Runtime migration requires a pool with at least two connections; the default Hikari pool supplies ten. Release jobs will use the separate command in Phase 61.

## Adopting an existing Alembic database

This is an explicit ownership transfer, not a normal application startup action. Rehearse on a restored copy first. Real infrastructure, production changes and destructive migrations remain subject to the approval gates in `AGENTS.md`.

1. Record the application release and database revision, take a verified backup, and restore an isolated copy. Preserve the old image and recovery instructions.
2. Stop migration jobs and application writers for the target of the handover. Deploy the guarded Alembic runner before considering transfer; older unguarded releases do not honor the shared lock. Prevent out-of-band DDL and keep the migration role separate from runtime access at cloud cutover.
3. Confirm the target schema is dedicated to the platform and contains exactly Alembic head `0002_external_telemetry`. Test fresh installation and adoption with this release before proceeding.
4. On the approved target, invoke the migration JAR with `adopt-alembic` instead of `migrate`. It reads catalog metadata and compares all eight tables to `contracts/python-baseline/database-metadata.json`. It rejects missing/extra tables, altered columns/precision/defaults/nullability, constraints, foreign-key actions, indexes and unverified schema objects before writing a Flyway baseline marker.
5. Only a matching schema can receive the explicit Flyway baseline at V1. Existing application rows and the historical `alembic_version` marker remain intact. Ordinary `migrate` refuses an unadopted Alembic database; repeated adoption refuses an already owned schema. The guarded Alembic online runner refuses schemas containing Flyway history.
6. Compare row counts and representative IDs, JSONB, money, timestamps and relationships with the pre-handover copy. Run application compatibility checks before allowing traffic. Future changes are Flyway-only.

The compatibility verifier intentionally refuses unrelated tables, views, triggers, row security, inheritance, nondefault column collations, generated columns and changed index semantics. This phase has no automatic repair path. Diagnose a mismatch on the copy; do not edit version markers or bypass verification. Catalog validation plus the cooperative lock does not stop a privileged operator issuing unrelated DDL, so writer/migration isolation remains part of the handover procedure.

Rollback means selecting a schema-compatible prior application release or restoring a verified backup into an isolated replacement and following the approved recovery procedure. Do not run Alembic downgrade, remove Flyway history, or run both owners. Python application reads/writes remain schema-compatible at V1, but its migration runner must remain disabled after ownership transfers.

## Synthetic seeds and evidence

Opt-in Java seeding creates the same local demo, Proofbase and AgentOps scopes and placeholder key hashes. New IDs/timestamps are deterministic; existing IDs, configuration, inactive state and revoked keys are preserved. Seeded prompt text is synthetic or explicitly a client-owned placeholder. No real provider credentials, prompts, generated outputs or workflow payloads are needed.

Java tests start actual disposable PostgreSQL 16.15 through pinned embedded PostgreSQL tooling. Startup failures fail the suite; there is no database skip or H2 substitute. Tests compare a fresh Flyway schema with an imported Alembic schema containing synthetic rows across all eight tables, verify unchanged rows after adoption, exercise schema drift refusals, JPA round trips, transactional uniqueness rollback and seed idempotency. Python CI requires its ownership-lock regression against PostgreSQL. CI also runs the packaged migration JAR against a separate service database before starting the application JAR.

No existing local application database or AWS RDS database was migrated during this phase. Cloud handover evidence belongs to the approved deployment phases.

## Additive operator migration (Phase 55)

Flyway V2 adds `operator_project_grants` with a unique identity/project grant and constrained viewer/operator roles. Fresh installation and explicit Alembic adoption now apply V2 after the verified V1 baseline; all eight legacy tables and rows remain unchanged. The strict eight-table verifier still applies before adoption and is not weakened to ignore unknown tables. Tests separately freeze V1 parity and verify additive V2 adoption/data preservation. Runtime Hibernate validates the ninth entity; grants are never seeded automatically. Grant provisioning is an explicit command documented in [operator security](java-operator-security.md).
