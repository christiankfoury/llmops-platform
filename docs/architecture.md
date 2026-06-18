# Architecture

## Overview

This project is a production-style LLMOps platform.

The product surface is intentionally small:

- Gateway API
- Dashboard
- Database
- Redis
- Observability stack

The infrastructure surface is intentionally serious:

- Terraform-managed AWS infrastructure
- EKS Kubernetes cluster
- Helm chart deployment
- Staged environments
- CI/CD
- Secrets
- Observability
- Rollback
- Runbooks
- Cost controls

## Logical architecture

```text
Users / Client Apps
        |
        v
    Ingress
        |
        v
+-------------------+
| LLM Gateway API   |
+-------------------+
 |        |        |
 |        |        +--> Mock/Real LLM Provider
 |        |
 |        +----------> Redis
 |
 +-------------------> PostgreSQL

API emits:
- JSON logs
- Prometheus metrics
- OpenTelemetry traces
```

## Application components

### API

Responsibilities:

- API key authentication
- LLM gateway endpoint
- prompt version lookup
- model route selection
- provider adapter call
- request logging
- cost calculation
- latency tracking
- failure categorization
- metrics/logs/traces

### Web dashboard

Responsibilities:

- usage overview
- cost overview
- latency overview
- error overview
- request table
- prompt versions
- model routes

### PostgreSQL

Stores:

- projects
- applications
- API keys
- prompt versions
- model routes
- gateway requests
- cost records
- audit logs

### Redis

Used for:

- rate limiting
- lightweight caching
- optional worker queue support

## Infrastructure architecture

### AWS

Planned services:

- EKS
- ECR
- RDS PostgreSQL
- ElastiCache Redis
- Secrets Manager
- IAM
- VPC/subnets/security groups
- S3/DynamoDB for Terraform state locking if configured
- Optional Route 53/ACM

### Kubernetes

Workloads:

- API Deployment
- Web Deployment
- optional Worker Deployment
- Services
- Ingress
- ExternalSecrets
- ConfigMaps
- ServiceAccounts
- HPA
- PodDisruptionBudget
- NetworkPolicies

### Observability

- Prometheus for metrics
- Grafana for dashboards
- Loki for logs
- OpenTelemetry for traces
- Alertmanager or equivalent alert routing placeholder

## Environment strategy

### Local

- Docker Compose
- local PostgreSQL
- local Redis
- mock LLM provider

### Dev

- auto-deploy from main
- small infrastructure
- relaxed capacity
- separate namespace and secrets

### Staging

- manual deploy
- production-like config
- pre-prod validation
- full observability

### Prod

- approval required
- conservative settings
- backups
- rollback
- alerts
- stricter security

## Design principles

- Infrastructure is code.
- Environments are explicit.
- Secrets are never committed.
- App configuration is externalized.
- Releases are traceable.
- Rollbacks are documented.
- Metrics, logs, and traces are first-class.
- Cost is measured and explained.
