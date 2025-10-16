"""Orchestrate the multi-agent workflow."""

from __future__ import annotations

import json
import uuid
import copy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.progress import Progress

from .agents.base import AgentOutput, BasePersonaAgent
from .agents.coding import CodingAgent, CodingOutput
from .agents.documentation import DocumentationAgent, DocumentationOutput
from .agents.requirements import RequirementsAgent, RequirementsOutput
from .agents.testing import TestingAgent, TestingOutput
from .config import AgentConfig, RunConfig
from .ingest import load_documents
from .openai_client import create_agent_if_needed, get_openai_client, prepare_tools
from .persistence import RunRecord, RunStore
from .sandbox import SandboxManager

console = Console()


@dataclass
class RunResult:
    run_id: str
    requirements: RequirementsOutput
    coding: CodingOutput
    testing: TestingOutput
    documentation: DocumentationOutput
    summary: str


class AgentOrchestrator:
    """High-level runner that wires together persona agents."""

    def __init__(
        self,
        run_config: RunConfig,
        requirements_config: AgentConfig,
        coding_config: AgentConfig,
        testing_config: AgentConfig,
        documentation_config: AgentConfig,
        store: Optional[RunStore] = None,
    ) -> None:
        self.run_config = run_config.resolved()
        self.requirements_config = requirements_config
        self.coding_config = coding_config
        self.testing_config = testing_config
        self.documentation_config = documentation_config
        self.store = store or RunStore()
        self.client = get_openai_client()
        self.run_id = uuid.uuid4().hex
        self.output_dir = self._prepare_output_directory()

    def execute(self) -> RunResult:
        console.rule(f"Starting Kimi Coding Agent run {self.run_id}")
        self.store.upsert_run(
            RunRecord(
                run_id=self.run_id,
                status="running",
                started_at=datetime.utcnow(),
                finished_at=None,
                summary="",
                metadata={"target_path": str(self.run_config.target_path)},
            )
        )

        documents = load_documents(self.run_config.input_documents)
        context: Dict[str, Any] = {
            "prompt": self.run_config.prompt,
            "documents": [doc.to_dict() for doc in documents],
        }

        sandbox = SandboxManager(self.run_config.target_path)
        snapshot = sandbox.create_snapshot()
        console.log(f"Snapshot created at {snapshot.path}")

        try:
            with Progress() as progress:
                requirements_task = progress.add_task("Requirements", total=None)
                requirements_agent = self._instantiate_agent(
                    self.requirements_config, RequirementsAgent, RequirementsOutput
                )
                requirements_output = self._run_persona_step(
                    "requirements",
                    requirements_agent,
                    context,
                    sequence=1,
                )
                context["requirements"] = json.loads(requirements_output.model_dump_json())
                progress.update(requirements_task, completed=1)

                coding_task = progress.add_task("Coding", total=None)
                coding_agent = self._instantiate_agent(self.coding_config, CodingAgent, CodingOutput)
                coding_output = self._run_persona_step(
                    "coding",
                    coding_agent,
                    context,
                    sequence=2,
                )
                context["coding"] = json.loads(coding_output.model_dump_json())
                progress.update(coding_task, completed=1)

                testing_task = progress.add_task("Testing", total=None)
                testing_agent = self._instantiate_agent(self.testing_config, TestingAgent, TestingOutput)
                testing_output = self._run_persona_step(
                    "testing",
                    testing_agent,
                    context,
                    sequence=3,
                )
                context["testing"] = json.loads(testing_output.model_dump_json())
                progress.update(testing_task, completed=1)

                documentation_task = progress.add_task("Documentation", total=None)
                summary = self._summarize(requirements_output, coding_output, testing_output)
                context["summary"] = summary
                documentation_agent = self._instantiate_agent(
                    self.documentation_config, DocumentationAgent, DocumentationOutput
                )
                documentation_output = self._run_persona_step(
                    "documentation",
                    documentation_agent,
                    context,
                    sequence=4,
                    extra_output={"summary": summary},
                )
                progress.update(documentation_task, completed=1)

            sandbox.cleanup()
            self._persist_success(requirements_output, coding_output, testing_output, documentation_output, summary)
            console.log(f"Deliverables written to {self.output_dir}")
            console.rule("Run completed successfully")
            return RunResult(
                run_id=self.run_id,
                requirements=requirements_output,
                coding=coding_output,
                testing=testing_output,
                documentation=documentation_output,
                summary=summary,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            console.print(f"[red]Run failed: {exc}")
            sandbox.restore_snapshot()
            sandbox.cleanup()
            self.store.upsert_run(
                RunRecord(
                    run_id=self.run_id,
                    status="failed",
                    started_at=datetime.utcnow(),
                    finished_at=datetime.utcnow(),
                    summary=str(exc),
                    metadata={"target_path": str(self.run_config.target_path)},
                )
            )
            raise

    def _instantiate_agent(self, config: AgentConfig, cls, output_model) -> Any:
        instructions = config.instructions or config.system_prompt
        tools = prepare_tools(
            self.run_config.enable_code_interpreter,
            self.run_config.enable_web_search,
            self.run_config.enable_file_search,
        )
        agent_handle = create_agent_if_needed(
            self.client,
            name=config.name,
            instructions=instructions,
            tools=tools,
            model=config.model,
        )
        return cls(
            self.client,
            agent_handle.agent_id,
            agent_handle.model,
            agent_handle.instructions,
            output_model,
            config.name,
        )

    def _summarize(
        self,
        requirements: RequirementsOutput,
        coding: CodingOutput,
        testing: TestingOutput,
    ) -> str:
        return (
            "Requirements: "
            + "; ".join(requirements.extracted_requirements)
            + " | Coding tasks: "
            + "; ".join(coding.tasks)
            + " | Tests: "
            + "; ".join(testing.tests)
        )

    def _persist_success(
        self,
        requirements: RequirementsOutput,
        coding: CodingOutput,
        testing: TestingOutput,
        documentation: DocumentationOutput,
        summary: str,
    ) -> None:
        finished_at = datetime.utcnow()
        record = RunRecord(
            run_id=self.run_id,
            status="succeeded",
            started_at=finished_at,
            finished_at=finished_at,
            summary=summary,
            metadata={
                "prompt": self.run_config.prompt,
                "target_path": str(self.run_config.target_path),
            },
        )
        self.store.upsert_run(record)
        self.store.add_artifact(self.run_id, "requirements", json.loads(requirements.model_dump_json()))
        self.store.add_artifact(self.run_id, "coding", json.loads(coding.model_dump_json()))
        self.store.add_artifact(self.run_id, "testing", json.loads(testing.model_dump_json()))
        self.store.add_artifact(self.run_id, "documentation", json.loads(documentation.model_dump_json()))

    def _prepare_output_directory(self) -> Path:
        output_dir = self.run_config.target_path / ".kimi_agent" / "runs" / self.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _run_persona_step(
        self,
        step_name: str,
        agent: BasePersonaAgent,
        context: Dict[str, Any],
        *,
        sequence: int,
        extra_output: Optional[Dict[str, Any]] = None,
    ) -> AgentOutput:
        handoff_payload = self._extract_handoff(step_name, context)
        output_model = agent.run(context)
        output_payload = json.loads(output_model.model_dump_json())
        if extra_output:
            output_payload.update(extra_output)
        self.store.add_step(self.run_id, step_name, sequence, handoff_payload, output_payload)
        self._write_step_outputs(step_name, handoff_payload, output_model, output_payload)
        return output_model

    def _extract_handoff(self, step_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        def _clone(value: Any) -> Any:
            try:
                return json.loads(json.dumps(value))
            except (TypeError, ValueError):
                return copy.deepcopy(value)

        if step_name == "requirements":
            return {
                "prompt": context.get("prompt"),
                "documents": _clone(context.get("documents", [])),
            }
        if step_name == "coding":
            return {"requirements": _clone(context.get("requirements"))}
        if step_name == "testing":
            return {"coding": _clone(context.get("coding"))}
        if step_name == "documentation":
            return {
                "summary": context.get("summary"),
                "testing": _clone(context.get("testing")),
            }
        return {}

    def _write_step_outputs(
        self,
        step_name: str,
        handoff_payload: Dict[str, Any],
        output_model: AgentOutput,
        output_payload: Dict[str, Any],
    ) -> None:
        step_dir = self.output_dir / step_name
        step_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(step_dir / "input.json", handoff_payload)
        self._write_json(step_dir / "output.json", output_payload)

        if step_name == "requirements" and isinstance(output_model, RequirementsOutput):
            self._write_json(step_dir / "requirements.json", output_model.model_dump())
        elif step_name == "coding" and isinstance(output_model, CodingOutput):
            self._materialize_coding_outputs(step_dir, output_model)
        elif step_name == "testing" and isinstance(output_model, TestingOutput):
            self._write_json(step_dir / "test_plan.yaml", output_model.model_dump())
        elif step_name == "documentation" and isinstance(output_model, DocumentationOutput):
            self._write_json(step_dir / "documentation.json", output_model.model_dump())
            self._write_documentation(step_dir, output_model)

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, indent=2, sort_keys=True)
        path.write_text(text + "\n", encoding="utf-8")

    def _materialize_coding_outputs(self, step_dir: Path, coding_output: CodingOutput) -> None:
        self._write_json(step_dir / "plan.yaml", coding_output.model_dump())
        files_dir = step_dir / "files"
        for relative_path, content in coding_output.files.items():
            file_path = files_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.rstrip() + "\n", encoding="utf-8")

        if coding_output.commands:
            commands_path = step_dir / "commands.sh"
            commands_lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""] + coding_output.commands
            commands_path.write_text("\n".join(commands_lines) + "\n", encoding="utf-8")

        if coding_output.dependencies:
            requirements_path = step_dir / "requirements.txt"
            requirements_path.write_text("\n".join(coding_output.dependencies) + "\n", encoding="utf-8")

    def _write_documentation(self, step_dir: Path, documentation_output: DocumentationOutput) -> None:
        readme_path = step_dir / "README.generated.md"
        lines = ["# Generated README", ""]
        if documentation_output.summary:
            lines.extend(["## Summary", documentation_output.summary.strip(), ""])

        if documentation_output.quickstart:
            lines.extend(["## Quickstart", documentation_output.quickstart.strip(), ""])

        if documentation_output.commands:
            lines.append("## Commands")
            lines.extend([f"- {command}" for command in documentation_output.commands])
            lines.append("")

        if documentation_output.limitations:
            lines.append("## Known Limitations")
            lines.extend([f"- {item}" for item in documentation_output.limitations])
            lines.append("")

        readme_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
