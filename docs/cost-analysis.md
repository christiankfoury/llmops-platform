# Cost Analysis

## Purpose

This document explains expected cloud and LLM costs and how the project controls them.

## Cost categories

### Cloud infrastructure

Expected cost drivers:

- EKS cluster
- worker nodes
- RDS PostgreSQL
- ElastiCache Redis
- load balancer
- NAT gateway if used
- log/metric storage
- container registry storage

### LLM usage

Expected cost drivers:

- input tokens
- output tokens
- model selected
- retries
- failed requests that still consume tokens

## Environment cost strategy

### Local

Use Docker Compose.

No cloud cost.

### Dev

Use smallest practical resources.

Enable teardown guidance.

### Staging

Keep production-like but not oversized.

Run only when needed if possible.

### Prod

Use conservative resources and backups.

## App-level LLM cost controls

The gateway should track:

- cost per request
- cost by project
- cost by app
- cost by model
- cost over time
- token usage

## Infrastructure cost controls

Planned controls:

- right-sized node groups
- resource requests/limits
- autoscaling
- dev teardown documentation
- AWS budget alert placeholder or implementation
- cost dashboard
- log retention settings

## README claim requirement

Only claim cost controls that are actually implemented.

Acceptable final claim:

> The platform tracks estimated LLM usage cost per request and includes environment-specific cloud cost analysis, right-sizing notes, and budget alert guidance.
