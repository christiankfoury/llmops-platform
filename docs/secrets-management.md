# Secrets Management

Phase 24 moves runtime secret wiring to AWS Secrets Manager through External Secrets Operator.

No real secret values are committed. Terraform creates Secrets Manager containers and an optional IAM role for the External Secrets controller, but it does not create `aws_secretsmanager_secret_version` resources.

## Secret Naming

Runtime values are expected in one JSON secret per environment:

```text
production-ai-platform-dev/runtime
production-ai-platform-staging/runtime
production-ai-platform-prod/runtime
```

Expected JSON properties:

```json
{
  "database-url": "<set-outside-git>",
  "redis-url": "<set-outside-git>"
}
```

The generated Kubernetes Secret remains:

```text
ai-platform-runtime-secrets
```

Expected Kubernetes keys:

- `database-url`
- `redis-url`

## External Secrets Flow

```text
AWS Secrets Manager -> External Secrets Operator -> Kubernetes Secret -> API Deployment
```

The API Deployment still reads `DATABASE_URL` and `REDIS_URL` from `ai-platform-runtime-secrets`. External Secrets owns that Kubernetes Secret in non-local environments.

## Workload Identity

Terraform creates an optional IAM role named:

```text
<environment-name-prefix>-external-secrets
```

The trust policy is scoped to:

```text
system:serviceaccount:external-secrets:external-secrets
```

The read policy is scoped to this platform environment's Secrets Manager ARNs only.

Annotate the External Secrets Operator service account after Terraform apply:

```yaml
eks.amazonaws.com/role-arn: <external_secrets_role_arn output>
```

Do not commit a real role ARN into this repository.

## Creating Secret Values

After an approved infrastructure apply, create or update the runtime secret value through an approved secure channel, for example:

```bash
aws secretsmanager put-secret-value \
  --secret-id production-ai-platform-dev/runtime \
  --secret-string '{"database-url":"<database-url>","redis-url":"<redis-url>"}'
```

Use environment-specific secret IDs and approved credentials. Do not paste real values into issue comments, workflow logs, commits, or docs.

## Local Development Fallback

Local Docker Compose and local API runs continue to use `.env.example` patterns and developer-provided local environment variables. Do not create or commit a real `.env`.

## Rotation Guidance

1. Write the new value to AWS Secrets Manager.
2. Wait for the ExternalSecret refresh interval or force a refresh by restarting the External Secrets controller.
3. Restart affected API pods if the application needs environment variables reloaded.
4. Confirm `/health/ready`, gateway smoke tests, logs, metrics, and alerts.
5. Revoke the old secret value only after the new value is confirmed.

Database credential rotation should respect RDS managed password behavior and application connection draining.
