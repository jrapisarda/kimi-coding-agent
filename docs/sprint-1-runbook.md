# Sprint Runbook (Sprints 1-5)

This runbook documents the current capabilities of the Kimi multi-agent coding assistant after completing the first five sprints. Sprint one laid the CLI/persistence foundation; sprint two added GPT-5-mini powered analysis, workspace safety, and richer persistence; sprint three delivered executable scaffolding, automated smoke tests, and documentation artifacts; sprint four introduced CLI-aware sandbox policies and npm integration; sprint five captures resolved dependency manifests, provenance metadata, and packaged logs for downstream auditing.

## 1. Environment Setup

- Python 3.10+ (3.13 recommended). Create and activate a virtual environment:
  ```bash
  python -m venv .venv
  .venv\Scripts\activate  # Windows
  python -m pip install -r requirements-dev.txt
  ```
- Optional: export `OPENAI_API_KEY` to exercise the OpenAI client with a real key. Without it, the client returns deterministic stub content.

## 2. CLI Workflow

```bash
agent run projects/nextjs --prompt "Generate Next.js 15 dashboard" --input-docs docs/spec.md
agent run projects/fastapi --prompt "One CRUD resource" --allow-cli-tools --dry-run
```

- The pipeline executes `Requirements -> Coding -> Testing -> Documentation` sequentially.
- `--dry-run` skips artifact packaging and workspace snapshots but still records run metadata.
- Use `--verbose` to emit DEBUG logs for orchestration troubleshooting; pass `--allow-cli-tools` (and optionally `--allow-package-installs`) to exercise real Next.js/FastAPI CLIs when available.
- Run identifiers follow `run-<UTC timestamp>-<suffix>` and drive paths in `var/` and `dist/`.

## 3. Persistence Layout

- SQLite database: `var/runs.sqlite`
  - `runs`: run-level metadata, including status, config JSON, and packaging path.
  - `steps`: per-agent execution records (input, output payloads, error text).
  - `artifacts`: JSON payloads emitted by agents (requirements, coding plan, test plan, docs, workspace restore hints).
  - `run_events`: timeline log capturing start, agent completion/failure, packaging, rollback, and completion events.
- Inspect recent runs:
  ```bash
  sqlite3 var/runs.sqlite "SELECT run_id, status, completed_at FROM runs ORDER BY id DESC LIMIT 5";
  sqlite3 var/runs.sqlite "SELECT event_type, message FROM run_events WHERE run_id='run-...'";
  ```

## 4. Workspace Snapshots & Restore

- Snapshots: `var/snapshots/<run_id>.zip` (created for non dry-run executions when the target path exists).
- Restores: `var/restores/<run_id>/` (staging directory populated if a run fails after partial writes).
- The orchestrator does not overwrite the original workspace automatically; it prepares a restore copy for manual inspection or scripted fix-forward tooling.

## 5. Packaging & Artifacts

- Successful non-dry runs produce `dist/<run_id>.zip` containing:
  - `manifest.json` summarising agents, statuses, metadata, and run-level configuration.
  - `provenance.json` mirroring run metadata (prompts, sandbox policy, CLI checks).
  - `artifacts/<agent>/<file>` (requirements analysis, scaffold manifests, resolved manifests, test results, documentation).
  - `sbom.json` derived from Coding agent dependencies and resolved manifests (entries such as `pip-freeze:fastapi==0.110.0`).
  - `logs/*.log` capturing every sandboxed command executed during the run.
  - `README.txt` describing the bundle contents.
- Inspect bundle contents:
  ```bash
  unzip -l dist/<run_id>.zip
  unzip dist/<run_id>.zip artifacts/documentation/README.md -d /tmp/run-preview
  ```

## 6. Agent Outputs (Sprint 5)

- **Requirements Agent:** reads developer prompt/input docs, calls GPT-5-mini, and persists `requirements.json` plus plaintext analysis alongside prompt provenance.
- **Coding Agent:** classifies project type, writes deterministic scaffolds, records declared dependencies, performs CLI health checks/real command attempts (policy permitting), and captures resolved manifests via `pip freeze` / `npm ls`.
- **Testing Agent:** executes `python -m pytest -q` (or `npm run test -- --watch=false` for Next.js scaffolds), storing stdout/stderr, coverage hints, skip reasons, and markdown summaries in `test_results.json`/`test_plan.*`.
- **Documentation Agent:** compiles README, CHANGELOG, and JSON summaries enriched with dependency details, testing coverage, and provenance metadata.

## 7. Testing & Quality Gates

- Run the automated suite with `pytest`; integration tests validate dry-run behaviour, scaffold execution, packaging outputs (incl. SBOM/logs), and timeline events.
- Pipeline smoke tests (non dry-run runs) execute automatically via the Testing agent; inspect results in `artifacts/testing/test_results.json` or command logs for debugging.
- When a Node-based project is detected, the agent attempts `npm run test -- --watch=false` and falls back gracefully if `npm` is unavailable; Python projects run `python -m pytest -q`.
- Known warning: Windows may raise `PermissionError` during pytest temp-dir cleanup; harmless during local runs.

## 8. Backlog Seeds for Sprint 5

1. Execute real Next.js/FastAPI scaffolding commands when ecosystem tooling is available, governed by sandbox policies.
2. Capture dependency hashes and resolved versions via `pip freeze` / `npm ls` and store them in SBOM + SQLite artifacts.
3. Introduce additional test runners (npm scripts, data validation) with structured log ingestion and provenance.
4. Attach provenance metadata (model call identifiers, prompt excerpts) to generated artifacts and documentation.

Refer to `docs/agent_project_plan.json` for the broader roadmap and acceptance criteria.
