from __future__ import annotations

import subprocess
import sys


def test_cli_run(tmp_path):
    docs_path = tmp_path / "requirements.md"
    docs_path.write_text("- Build FastAPI service\n- Include pytest suite", encoding="utf-8")
    target_path = tmp_path / "workspace"
    state_dir = tmp_path / "state"

    command = [
        sys.executable,
        "-m",
        "kimi_coding_agent.cli.main",
        "run",
        str(target_path),
        "--input-docs",
        str(docs_path),
        "--prompt",
        "Assemble FastAPI CRUD pipeline",
        "--state-dir",
        str(state_dir),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)

    assert completed.returncode == 0, completed.stderr
    assert (target_path / "agent_plan.json").exists()
    assert (target_path / "agent_run_report.md").exists()
