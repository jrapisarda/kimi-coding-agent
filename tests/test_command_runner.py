import subprocess
from pathlib import Path

import pytest

from kimi_agent.config import SandboxPolicy
from kimi_agent.sandbox import CommandRunner


def test_command_runner_dry_run(tmp_path: Path):
    runner = CommandRunner(tmp_path, dry_run=True, policy=SandboxPolicy())
    result = runner.run(["python", "--version"], cwd=tmp_path)
    assert result.skipped is True
    assert result.reason == "dry-run"
    assert result.log_path.read_text(encoding="utf-8").startswith("[dry-run]")


def test_command_runner_missing_executable(monkeypatch, tmp_path: Path):
    """
    Simulate a missing executable scenario so that logs capture the error
    instead of raising a FileNotFoundError to the caller.
    """

    runner = CommandRunner(tmp_path / "run", policy=SandboxPolicy(allow_cli_tools=True))

    # Force _skip_reason to think the executable exists but have subprocess fail.
    monkeypatch.setattr("kimi_agent.sandbox.which", lambda exe: str(tmp_path / "fake-npm"))

    def _raise_file_not_found(*_, **__):
        raise FileNotFoundError("[WinError 2] The system cannot find the file specified")

    monkeypatch.setattr(subprocess, "run", _raise_file_not_found)

    result = runner.run(["npm", "run", "test"], cwd=tmp_path)

    assert result.skipped is True
    assert result.reason == "missing-executable"
    assert result.return_code == 127
    assert result.log_path is not None and result.log_path.exists()
    log_text = result.log_path.read_text(encoding="utf-8")
    assert "missing-executable" in log_text
    assert "npm run test" in log_text


def test_command_runner_cli_allowed(monkeypatch, tmp_path: Path):
    policy = SandboxPolicy(allow_cli_tools=True)
    runner = CommandRunner(tmp_path / "run2", policy=policy)

    monkeypatch.setattr("kimi_agent.sandbox.which", lambda exe: str(tmp_path / "fake-npm"))

    completed = subprocess.CompletedProcess(args=["npm", "--version"], returncode=0, stdout="10.0.0\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed)

    result = runner.run(["npm", "--version"], cwd=tmp_path)
    assert result.skipped is False
    assert result.return_code == 0
    assert result.stdout.strip() == "10.0.0"


def test_command_runner_blocks_package_install(tmp_path: Path):
    runner = CommandRunner(tmp_path / "pkg", policy=SandboxPolicy())
    result = runner.run(["python", "-m", "pip", "install", "foo"], cwd=tmp_path)
    assert result.skipped is True
    assert result.reason == "blocked-package-install"
