# Gateway request flow

The active implementation is Java/Spring Boot. See [Java gateway behavior](java-gateway.md)
for the API contract and [architecture](architecture.md) for system boundaries.

1. Receive `POST /v1/gateway/completions` and apply bounded HTTP input/admission checks.
2. Resolve the hashed application key and its active project/application scope.
3. Load active prompt and model-route configuration; reject unsupported providers.
4. Apply Redis-backed quotas and call the mock provider without holding a database connection.
5. Persist request/cost metadata and safe failure categories; emit operational signals.
6. Return request identifiers, model and usage fields without exposing credentials.

The gateway currently implements a mock provider only. Proofbase and AgentOps send
metadata through the [telemetry API](external-telemetry-contract.md); they retain their
own provider execution. The default dashboard is fixed synthetic data. API-backed
usage and administrative configuration require [operator authentication and grants](java-operator-security.md).

The [Python flow walkthrough](archive/gateway-flow-baseline.md) is historical reference.
Do not use its unauthenticated administration or Alembic instructions for Java.
