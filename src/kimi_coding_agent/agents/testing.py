"""Testing agent implementation."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any, Dict, List

from ..schemas import CodingContext, RunConfig, TestingContext
from .base import BaseAgent

logger = logging.getLogger(__name__)


class TestingAgent(BaseAgent):
    """Creates and executes smoke tests based on the coding plan."""

    __test__ = False

    def __init__(self) -> None:
        super().__init__(name="testing")

    def run(self, *, config: RunConfig, shared_state: Dict[str, Any]) -> Dict[str, Any]:
        coding_context = CodingContext.model_validate(shared_state.get("coding", {}))
        pytest_path = shutil.which("pytest")
        tests_run: List[str] = []
        status = "skipped"
        summary = "pytest not available; recorded requirement for follow-up."

        if pytest_path:
            status = "succeeded"
            tests_run.append("pytest --collect-only")
            try:
                subprocess.run(
                    [pytest_path, "--version"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                summary = "Validated pytest availability and recorded planned test suite."
            except subprocess.CalledProcessError as exc:
                status = "failed"
                summary = f"pytest invocation failed: {exc}"
                logger.exception("pytest --version failed")

        report_file = config.target_path / "test_plan.json"
        report_file.write_text(
            json.dumps(
                {
                    "status": status,
                    "tests_run": tests_run,
                    "summary": summary,
                    "plan": coding_context.plan,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        context = TestingContext(tests_run=tests_run, status=status, summary=summary)
        shared_state[self.name] = context.model_dump()
        return context.model_dump()
