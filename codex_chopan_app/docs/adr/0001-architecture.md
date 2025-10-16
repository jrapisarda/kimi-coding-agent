# ADR 0001: Adopt Microservices on ECS Fargate

## Context
The outreach assistant requires independent scalability for content, social, email, and prospect
pipelines while maintaining strong isolation boundaries.

## Decision
Deploy each domain service as a FastAPI container on ECS Fargate behind an API Gateway facade. Use
Redis for queue coordination and S3 for immutable snapshots.

## Consequences
- Enables independent deployments and blue/green rollouts.
- Introduces cross-service observability requirements handled via structured logging and tracing.
