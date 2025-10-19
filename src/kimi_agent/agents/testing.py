from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ..orchestrator import Agent, AgentContext, AgentResult


LOGGER = logging.getLogger("kimi_agent.testing")
MAX_LOG_SNIPPET = 1200


class TestingAgent(Agent):
    name = "testing"

    def execute(self, context: AgentContext) -> AgentResult:
        project_type = context.run_metadata.get("coding.project_type", "generic-software-project")
        target_path = context.request.target_path
        command, command_label = _determine_test_command(project_type, target_path)
        smoke_tests = _default_smoke_tests(project_type)

        if context.request.dry_run:
            context.run_metadata["testing.command"] = command_label
            context.run_metadata["testing.status"] = "skipped"
            details = {
                "command": command_label,
                "smoke_tests": smoke_tests,
                "status": "skipped",
                "notes": "Dry-run mode; tests not executed.",
                "log_path": None,
            }
            artifacts = _build_artifacts(command_label, smoke_tests, details, None)
            return AgentResult(
                name=self.name,
                status="succeeded",
                summary=f"Testing skipped (dry-run) for {project_type}.",
                details=details,
                artifacts=artifacts,
            )

        context.run_metadata["testing.command"] = command_label
        result = context.command_runner.run(command, cwd=target_path)
        if result.skipped:
            status = "skipped"
            agent_status = "succeeded"
        else:
            status = "succeeded" if result.return_code == 0 else "failed"
            agent_status = status

        details = {
            "command": command_label,
            "smoke_tests": smoke_tests,
            "status": status,
            "return_code": result.return_code if not result.skipped else None,
            "log_path": str(result.log_path) if result.log_path else None,
        }
        coverage = _extract_coverage(result.stdout, result.stderr) if not result.skipped else None
        if coverage:
            details["coverage"] = coverage
            context.run_metadata["testing.coverage"] = coverage
        if result.reason:
            details["skip_reason"] = result.reason

        analysis = _generate_test_analysis(
            openai_client=context.openai,
            project_type=project_type,
            command_label=command_label,
            smoke_tests=smoke_tests,
            details=details,
            result=result,
        )
        if analysis:
            details["analysis"] = analysis
            context.run_metadata["testing.analysis"] = analysis
        context.run_metadata["testing.analysis_model"] = getattr(context.openai, "model", "unknown")
        context.run_metadata["testing.status"] = status
        artifacts = _build_artifacts(command_label, smoke_tests, details, result)

        if status == "succeeded":
            summary = f"Smoke tests passed for {project_type}."
        elif status == "skipped":
            summary = f"Testing skipped for {project_type} (see details)."
        else:
            summary = f"Smoke tests failed for {project_type}."

        return AgentResult(
            name=self.name,
            status=agent_status,
            summary=summary,
            details=details,
            artifacts=artifacts,
        )


def _determine_test_command(project_type: str, target_path: Path) -> Tuple[List[str], str]:
    package_json = target_path / "package.json"
    if package_json.exists() or project_type == "nextjs-dashboard":
        command = ["npm", "run", "test", "--", "--watch=false"]
        return command, "npm run test -- --watch=false"
    return ["python", "-m", "pytest", "-q"], "python -m pytest -q"


def _default_smoke_tests(project_type: str) -> Dict[str, List[str]]:
    mapping = {
        "nextjs-dashboard": [
            "renders dashboard page placeholder",
            "README scaffold present",
        ],
        "fastapi-crud-api": [
            "GET /items returns sample payload",
            "FastAPI application instantiates",
        ],
        "python-etl-sqlite": [
            "ETL loads CSV into SQLite",
            "Second run remains idempotent",
        ],
        "sklearn-ml-experiment": [
            "Model trains and writes metrics",
            "Accuracy exceeds baseline threshold",
        ],
    }
    return {"tests": mapping.get(project_type, ["Smoke tests to be defined."])}


def _build_artifacts(
    command_label: str,
    smoke_tests: Dict[str, List[str]],
    details: Dict[str, object],
    result,
) -> Dict[str, Dict[str, object]]:
    artifacts = {
        "test_plan.json": {
            "type": "application/json",
            "payload": {
                "command": command_label,
                "smoke_tests": smoke_tests,
                "status": details.get("status"),
            },
        },
        "test_plan.md": {
            "type": "text/markdown",
            "payload": _format_test_markdown(command_label, smoke_tests, details.get("status", "skipped")),
        },
    }
    payload = {
        "coverage": details.get("coverage"),
        "status": details.get("status"),
        "return_code": details.get("return_code"),
        "log_path": details.get("log_path"),
        "skip_reason": details.get("skip_reason"),
    }
    analysis = details.get("analysis")
    if analysis:
        payload["analysis"] = analysis
    if result is not None and not result.skipped:
        payload.update(
            {
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    artifacts["test_results.json"] = {
        "type": "application/json",
        "payload": payload,
    }
    if analysis:
        artifacts["test_analysis.txt"] = {
            "type": "text/plain",
            "payload": analysis,
        }
    return artifacts


def _format_test_markdown(command_label: str, smoke_tests: Dict[str, List[str]], status: str) -> str:
    tests = "\n".join(f"- {test}" for test in smoke_tests["tests"])
    status_line = "Tests executed automatically." if status != "skipped" else "Tests not executed (dry-run/skipped)."
    return "\n".join(
        [
            "# Testing Plan",
            "",
            f"Command: `{command_label}`",
            "",
            "## Smoke Tests",
            tests,
            "",
            status_line,
            "",
        ]
    )



def _extract_coverage(stdout: Optional[str], stderr: Optional[str]) -> Optional[str]:
    for stream in filter(None, [stdout, stderr]):
        lower = stream.lower()
        if "coverage" in lower:
            lines = stream.splitlines()
            for line in lines:
                if "coverage" in line.lower():
                    return line.strip()[:200]
    return None


def _generate_test_analysis(
    openai_client,
    project_type: str,
    command_label: str,
    smoke_tests: Dict[str, List[str]],
    details: Dict[str, object],
    result,
) -> Optional[str]:
    prompt = _build_testing_analysis_prompt(
        project_type=project_type,
        command_label=command_label,
        smoke_tests=smoke_tests.get("tests", []),
        details=details,
        stdout=_trim_output(getattr(result, "stdout", ""), MAX_LOG_SNIPPET),
        stderr=_trim_output(getattr(result, "stderr", ""), MAX_LOG_SNIPPET),
    )
    try:
        analysis = openai_client.generate_text(prompt).strip()
    except RuntimeError as exc:  # pragma: no cover - defensive guard for unexpected SDK failure
        LOGGER.warning("OpenAI analysis failed: %s", exc)
        return None
    return analysis or None


def _build_testing_analysis_prompt(
    project_type: str,
    command_label: str,
    smoke_tests: List[str],
    details: Dict[str, object],
    stdout: Optional[str],
    stderr: Optional[str],
) -> str:
    smoke_lines = "\n".join(f"- {item}" for item in smoke_tests) or "- (not specified)"
    coverage = details.get("coverage") or "Not reported"
    skip_reason = details.get("skip_reason") or "None"
    status = details.get("status") or "unknown"
    return_code = details.get("return_code")
    rc_text = "not executed" if return_code is None else str(return_code)
    sections = [
        "You are the Testing Agent in a multi-agent coding assistant pipeline.",
        "Craft a concise summary of the smoke test outcome, highlight notable findings, "
        "and recommend the single most important next action.",
        "",
        f"Project Type: {project_type}",
        f"Command Executed: {command_label}",
        f"Status: {status}",
        f"Return Code: {rc_text}",
        f"Coverage Detail: {coverage}",
        f"Skip Reason: {skip_reason}",
        "",
        "Smoke Tests Considered:",
        smoke_lines,
    ]
    if stdout:
        sections.extend(["", "Captured STDOUT (truncated):", stdout])
    if stderr:
        sections.extend(["", "Captured STDERR (truncated):", stderr])
    sections.extend(
        [
            "",
            "Respond with:",
            "1. A one-sentence verdict on the testing outcome.",
            "2. Bullet points for critical observations (max 3 bullets).",
            "3. One recommended next action.",
        ]
    )
    return "\n".join(sections)


def _trim_output(output: Optional[str], limit: int) -> Optional[str]:
    if not output:
        return None
    snippet = output.strip()
    if not snippet:
        return None
    if len(snippet) <= limit:
        return snippet
    return snippet[:limit].rstrip() + "...\n[truncated]"
