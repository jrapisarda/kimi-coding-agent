"""Orchestrate the multi-agent workflow."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from rich.console import Console
from rich.progress import Progress

from .agents.base import AgentOutput
from .agents.coding import CodingAgent, CodingOutput
from .agents.documentation import DocumentationAgent, DocumentationOutput
from .agents.requirements import RequirementsAgent, RequirementsOutput
from .agents.testing import TestingAgent, TestingOutput
from .config import AgentConfig, RunConfig
from .ingest import Document, load_documents
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
                requirements_agent = self._instantiate_agent(self.requirements_config, RequirementsAgent, RequirementsOutput)
                requirements_output = requirements_agent.run(context)
                progress.update(requirements_task, completed=1)

                coding_task = progress.add_task("Coding", total=None)
                context["requirements"] = json.loads(requirements_output.model_dump_json())
                coding_agent = self._instantiate_agent(self.coding_config, CodingAgent, CodingOutput)
                coding_output = coding_agent.run(context)
                progress.update(coding_task, completed=1)

                testing_task = progress.add_task("Testing", total=None)
                context["coding"] = json.loads(coding_output.model_dump_json())
                testing_agent = self._instantiate_agent(self.testing_config, TestingAgent, TestingOutput)
                testing_output = testing_agent.run(context)
                progress.update(testing_task, completed=1)

                documentation_task = progress.add_task("Documentation", total=None)
                summary = self._summarize(requirements_output, coding_output, testing_output)
                context["testing"] = json.loads(testing_output.model_dump_json())
                context["summary"] = summary
                documentation_agent = self._instantiate_agent(
                    self.documentation_config, DocumentationAgent, DocumentationOutput
                )
                documentation_output = documentation_agent.run(context)
                progress.update(documentation_task, completed=1)

            sandbox.cleanup()
            self._persist_success(requirements_output, coding_output, testing_output, documentation_output, summary)
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
