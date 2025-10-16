# Kimi Coding Agent

A local-first, multi-agent coding orchestrator built on the latest OpenAI Agents SDK and GPT-5 models. The tool ingests Markdown and JSON source documents, distills requirements, plans implementation and testing steps, and emits documentation—all while persisting provenance to SQLite and protecting the target workspace via snapshots.

## Features

- **Four-agent pipeline**: Requirements → Coding → Testing → Documentation personas share structured context across the run.
- **OpenAI Agents SDK**: Uses the `OpenAI` Python SDK with the Responses API and GPT-5 (`gpt-5.0` by default). Tooling integrates Code Interpreter, optional Web Search, and File Search.
- **Document ingestion**: Reads Markdown (`.md`, `.markdown`) and JSON files, normalizes them, and feeds them into the Requirements agent.
- **Local-first execution**: Takes a filesystem snapshot before modifications and automatically rolls back on failure.
- **Persistence**: Saves run metadata, structured outputs, handoff inputs, and artifacts to a local SQLite database (`~/.kimi_agent/runs.db`).
- **Step deliverables**: Writes per-agent inputs/outputs plus generated code objects, requirements JSON, helper manifests, and README drafts to `.kimi_agent/runs/<run_id>/` in the target workspace.
- **Packaging hooks**: Provides structured outputs that can be zipped into `dist/<run_id>.zip` as a follow-up.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Set the required environment variables before running:

```bash
export OPENAI_API_KEY=sk-...
# Optional overrides
export KIMI_AGENT_MODEL=gpt-5.0
```

## Usage

```bash
kimi-agent run ./target-project \
  --input-docs docs/agent_project_plan.json docs/implementation_plan.md \
  --prompt "Build a FastAPI CRUD service" \
  --enable-web-search
```

During the run the CLI prints a progress bar for each persona and finishes with a summary plus the generated documentation payload.

### Arguments

| Option | Description |
| ------ | ----------- |
| `target_path` | Workspace to operate on. A snapshot is taken automatically. |
| `--input-docs` | One or more `.md` or `.json` files to ingest as context. |
| `--prompt` | Natural-language prompt describing the desired output. |
| `--enable-web-search` | Enable OpenAI Web Search tool for up-to-date references. |
| `--enable-file-search` | Enable the File Search tool for large repositories. |
| `--enable-code-interpreter` | Toggle Code Interpreter tool (enabled by default). |

## Architecture

```
RunConfig → AgentOrchestrator
      │           │
      │           ├─ RequirementsAgent (Responses API → RequirementsOutput)
      │           ├─ CodingAgent (Responses API → CodingOutput)
      │           ├─ TestingAgent (Responses API → TestingOutput)
      │           └─ DocumentationAgent (Responses API → DocumentationOutput)
      │
SandboxManager (snapshot/rollback)
RunStore (SQLite persistence)
Document ingestion utilities (Markdown/JSON)
```

- **Agents** use `responses.parse` to request structured outputs defined via Pydantic models. Each persona is provisioned via an ephemeral entry in the Agents API so they can call built-in tools like Code Interpreter and Web Search.
- **Sandbox manager** copies the target workspace to a temporary directory before the pipeline mutates anything, ensuring rollbacks are clean.
- **Persistence layer** stores run status, metadata, and each persona’s structured output as JSON for audit and reproducibility.

## Extending

- Add new personas by subclassing `BasePersonaAgent` and defining a Pydantic output schema.
- Override prompts/instructions by editing the `AgentConfig` instances in `cli.py` or by constructing a custom orchestrator.
- Integrate packaging by creating a `dist/<run_id>.zip` that bundles the workspace, logs, and SQLite artifacts.

## Testing

Future iterations should add automated tests (e.g., `pytest`) that exercise the orchestrator using mocked OpenAI responses and temporary workspaces. Deterministic seeds and snapshot verification keep the runs reproducible.

## Security & Compliance

- Secrets are never persisted to SQLite; redact sensitive data before logging.
- License guardrails should be enforced by validating fetched snippets against MIT/Apache/BSD-compatible sources and storing provenance alongside artifacts.

## Roadmap

- Implement retry-and-fix-forward loops before triggering rollbacks.
- Expand artifact packaging to generate SBOM and zipped deliverables automatically.
- Add CLI subcommands for inspecting past runs and exporting artifacts.
- Provide templates for the four reference projects described in `docs/agent_project_plan.json`.
