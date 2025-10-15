# Agentic Architect

Agentic Architect is a multi-agent system that transforms structured JSON specifications into complete, production-ready software projects. It leverages the OpenAI Agentic SDK and the `kimi-k2-0905-preview` model to coordinate specialised agents for requirements analysis, code generation, testing, documentation, quality enforcement, and version control.

## Features

- **Multi-agent pipeline** with dedicated agents for requirements, code generation, testing, documentation, quality assurance, and git operations.
- **SQLite-backed state management** for coordination, caching, and recovery of agent runs.
- **Pattern caching** to reuse proven architectural templates across projects.
- **Web research integration** via DuckDuckGo search for filling specification gaps using current best practices.
- **JSON schema validation** ensuring specifications conform to an expected structure before execution.
- **Quality tooling** including Black, Ruff, MyPy, Bandit, Safety, and pre-commit hooks.
- **Comprehensive testing setup** with pytest, coverage enforcement, and structured test plans.

## Getting Started

### Prerequisites

- Python 3.12+
- Access to an OpenAI-compatible endpoint exposing the `kimi-k2-0905-preview` model
- SQLite (bundled with Python)

### Installation

```bash
pip install -e .[dev]
```

### Configuration

Environment variables prefixed with `AGENTIC_` control runtime behaviour. The most important settings are:

- `AGENTIC_OPENAI__API_KEY` – API key for the OpenAI-compatible service
- `AGENTIC_OPENAI__BASE_URL` – Base URL when targeting a self-hosted gateway
- `AGENTIC_DATABASE__URL` – Path to the SQLite database
- `AGENTIC_WORKSPACE_ROOT` – Root directory where generated projects are created

Settings can also be provided via a `.env` file in the project root.

### Usage

```bash
agentic-architect generate path/to/spec.json --workspace /tmp/workspace
```

This command validates the JSON specification, coordinates all agents, and writes the generated project to the workspace directory.

### Example Specification

An example specification is available at `src/agentic_architect/examples/bioinformatics_etl_cli.json`.

### Development Workflow

- Format code with `black` and `ruff`
- Run static checks with `mypy`
- Execute tests via `pytest`
- Security scans using `bandit` and `safety`

Pre-commit hooks are provided for consistent tooling across contributors.

## Testing

```bash
pytest
```

## License

Distributed under the MIT License. See `LICENSE` for more information.
