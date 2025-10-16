# Chopan AI Outreach Assistant Architecture

The solution is built as a microservice platform running on ECS Fargate. Each domain-specific
capability—content, email, social, and prospect discovery—exposes a FastAPI service. The API Gateway
aggregates functionality, enforces rate limits, and brokers authentication.

A worker service encapsulates asynchronous jobs exposed through Celery-compatible interfaces while a
Next.js dashboard offers operational visibility. Terraform and AWS CDK definitions provide
infrastructure-as-code coverage for ECS, networking, and supporting data stores.
