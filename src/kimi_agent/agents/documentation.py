from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from ..orchestrator import Agent, AgentContext, AgentResult


class DocumentationAgent(Agent):
    name = "documentation"

    def execute(self, context: AgentContext) -> AgentResult:
        run_id = context.request.run_id
        project_type = context.run_metadata.get("coding.project_type", "generic-software-project")
        timestamp = datetime.utcnow().isoformat()
        context.run_metadata["documentation.timestamp"] = timestamp
        context.run_metadata["documentation.project_type"] = project_type

        requirements = context.outputs.get("requirements")
        coding = context.outputs.get("coding")
        testing = context.outputs.get("testing")

        requirements_summary = requirements.summary if requirements else "No requirements summary available."
        acceptance = requirements.details.get("acceptance_criteria", {}) if requirements else {}
        assumptions = requirements.details.get("assumptions", {}) if requirements else {}

        coding_details = coding.details if coding else {}
        coding_artifacts = coding.artifacts if coding else {}
        scaffold_payload = coding_artifacts.get("scaffold.json", {}).get("payload", {})

        testing_details = testing.details if testing else {}

        readme_payload = _build_readme(
            run_id=run_id,
            project_type=project_type,
            timestamp=timestamp,
            overview=requirements_summary,
            acceptance=acceptance,
            assumptions=assumptions,
            coding_details=coding_details,
            scaffold_payload=scaffold_payload,
            testing_details=testing_details,
        )
        changelog_payload = _build_changelog(
            run_id=run_id,
            timestamp=timestamp,
            coding_details=coding_details,
            testing_details=testing_details,
        )

        summary = f"Documentation generated for {project_type}."
        details = {
            "run_id": run_id,
            "project_type": project_type,
            "timestamp": timestamp,
            "files_documented": coding_details.get("files_created", []),
            "testing_status": testing_details.get("status"),
            "testing_coverage": testing_details.get("coverage"),
        }
        provenance_payload = {
            "run_id": run_id,
            "project_type": project_type,
            "timestamp": timestamp,
            "sections": list(_default_sections(project_type).keys()),
        }
        context.run_metadata["documentation.sections"] = provenance_payload["sections"]

        artifacts = {
            "README.md": {
                "type": "text/markdown",
                "payload": readme_payload,
            },
            "CHANGELOG.md": {
                "type": "text/markdown",
                "payload": changelog_payload,
            },
            "docs_summary.json": {
                "type": "application/json",
                "payload": {
                    "run_id": run_id,
                    "project_type": project_type,
                    "overview": requirements_summary,
                    "acceptance": acceptance,
                    "assumptions": assumptions,
                    "testing_status": testing_details.get("status"),
                    "testing_coverage": testing_details.get("coverage"),
                    "generated_at": timestamp,
                },
            },
            "docs_provenance.json": {
                "type": "application/json",
                "payload": provenance_payload,
            },
        }

        return AgentResult(
            name=self.name,
            status="succeeded",
            summary=summary,
            details=details,
            artifacts=artifacts,
        )


def _build_readme(
    run_id: str,
    project_type: str,
    timestamp: str,
    overview: str,
    acceptance: Dict[str, str],
    assumptions: Dict[str, str],
    coding_details: Dict[str, object],
    scaffold_payload: Dict[str, object],
    testing_details: Dict[str, object],
) -> str:
    dependencies_map = scaffold_payload.get("dependencies", {}) if scaffold_payload else {}
    dependencies = {
        source: [f"{pkg}=={version}" for pkg, version in deps.items()]
        for source, deps in dependencies_map.items()
    }
    files_created = scaffold_payload.get("files_created", coding_details.get("files_created", [])) or []
    testing_status = testing_details.get("status", "unknown")
    testing_command = testing_details.get("command", "python -m pytest -q")
    testing_log = testing_details.get("log_path")
    testing_coverage = testing_details.get("coverage")

    lines = [
        f"# Generated Project Documentation ({project_type})",
        "",
        f"_Run ID: {run_id} - Generated: {timestamp}_",
        "",
        "## Overview",
        overview,
        "",
        "### Acceptance Criteria",
    ]
    if acceptance:
        lines.extend(f"- **{key}**: {value}" for key, value in acceptance.items())
    else:
        lines.append("- Not specified.")

    lines.extend(["", "### Assumptions"])
    if assumptions:
        lines.extend(f"- **{key}**: {value}" for key, value in assumptions.items())
    else:
        lines.append("- Not specified.")

    lines.extend(["", "## Generated Files"])
    if files_created:
        lines.extend(f"- {item}" for item in files_created)
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Dependencies"])
    if dependencies:
        for source, entries in dependencies.items():
            lines.append(f"- **{source}**: {', '.join(entries)}")
    else:
        lines.append("- Not captured.")

    lines.extend(
        [
            "",
            "## Testing",
            f"- Status: **{testing_status}**",
            f"- Command: `{testing_command}`",
        ]
    )
    if testing_log:
        lines.append(f"- Log: `{testing_log}`")
    if testing_coverage:
        lines.append(f"- Coverage: {testing_coverage}")

    lines.extend(
        [
            "",
            "## Next Steps",
            "- Review generated code and tests.",
            "- Run packaging bundle located in `dist/` for deliverables.",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def _build_changelog(
    run_id: str,
    timestamp: str,
    coding_details: Dict[str, object],
    testing_details: Dict[str, object],
) -> str:
    files_created = coding_details.get("files_created", [])
    testing_status = testing_details.get("status", "unknown")
    testing_coverage = testing_details.get("coverage")
    coverage_line = f" (coverage: {testing_coverage})" if testing_coverage else ""
    return "\n".join(
        [
            "# Changelog",
            "",
            f"- {timestamp}: Generated scaffold for run `{run_id}`.",
            f"- Files created: {', '.join(files_created) if files_created else 'None'}.",
            f"- Testing outcome: {testing_status}{coverage_line}.",
            "",
        ]
    )


def _default_sections(project_type: str) -> Dict[str, List[str]]:
    base = {
        "Quickstart": [
            "Install dependencies",
            "Run the agent pipeline",
            "Execute smoke tests",
        ],
        "Architecture": [
            "Multi-agent workflow overview",
            "Key generated components",
        ],
        "Testing": [
            "Commands to run test suites",
            "Interpreting report artifacts",
        ],
        "Limitations": [
            "AI-generated code caveats",
            "Manual review checklist",
        ],
    }
    if project_type == "nextjs-dashboard":
        base["Quickstart"].append("Start Next.js dev server with `npm run dev`.")
    elif project_type == "fastapi-crud-api":
        base["Quickstart"].append("Start API with `uvicorn app.main:app --reload`.")
    elif project_type == "python-etl-sqlite":
        base["Quickstart"].append("Run ETL with `python jobs/etl.py inputs/sample.csv`.")
    elif project_type == "sklearn-ml-experiment":
        base["Quickstart"].append("Train pipeline with `python experiments/train.py`.")
    return base
