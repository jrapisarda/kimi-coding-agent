# Chopan AI Outreach Assistant

This project implements a microservices-based outreach platform featuring an API gateway, domain
services for content/email/social/prospect operations, and a worker capable of Celery-compatible
tasks. Infrastructure assets include Terraform and AWS CDK blueprints while a lightweight Next.js 15
dashboard illustrates how teams can monitor flows.

## Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Export the API key: `export CHOPAN_API_KEY=test-key`
3. Launch the gateway: `uvicorn codex_chopan_app.services.api_gateway.main:app --reload`
4. Explore the OpenAPI spec at `http://localhost:8000/docs`.

## CLI Utilities
- `python scripts/snapshot_create.py`
- `python scripts/snapshot_restore.py --to <snapshot_id>`
- `python scripts/db_migrate.py`
