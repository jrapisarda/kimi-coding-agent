from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Iterable, List, Optional

from .config import SandboxPolicy


PACKAGE_INSTALL_PREFIXES = [
    ("npm", "install"),
    ("python", "-m", "pip", "install"),
]

CLI_TOOL_PREFIXES = [
    ("npm", "create"),
]


@dataclass
class CommandResult:
    command: List[str]
    cwd: Path
    return_code: int
    stdout: str
    stderr: str
    skipped: bool = False
    log_path: Optional[Path] = None
    reason: Optional[str] = None


class CommandRunner:
    """
    Minimal command runner with dry-run support used by Coding/Testing agents.

    All commands are executed inside the run's sandbox directory and logs are
    persisted per-command under `logs/`.
    """

    def __init__(self, run_dir: Path, dry_run: bool = False, policy: Optional[SandboxPolicy] = None) -> None:
        self._run_dir = Path(run_dir)
        self._dry_run = dry_run
        self._policy = policy or SandboxPolicy()
        self._logs_dir = self._run_dir / "logs"
        self._logs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def logs_dir(self) -> Path:
        return self._logs_dir

    def run(self, command: Iterable[str], cwd: Path) -> CommandResult:
        command_list = list(command)
        cwd = Path(cwd)
        log_path = self._create_log_path(command_list)

        skip_reason = self._skip_reason(command_list)
        if skip_reason:
            log_path.write_text(
                f"[skipped:{skip_reason}] command not executed: {' '.join(command_list)}\n",
                encoding="utf-8",
            )
            return CommandResult(
                command=command_list,
                cwd=cwd,
                return_code=0,
                stdout="",
                stderr="",
                skipped=True,
                log_path=log_path,
                reason=skip_reason,
            )

        if self._dry_run:
            log_path.write_text(
                f"[dry-run] command skipped: {' '.join(command_list)}\n",
                encoding="utf-8",
            )
            return CommandResult(
                command=command_list,
                cwd=cwd,
                return_code=0,
                stdout="",
                stderr="",
                skipped=True,
                log_path=log_path,
                reason="dry-run",
            )

        try:
            completed = subprocess.run(
                command_list,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            message = (
                f"[missing-executable] command failed: {' '.join(command_list)}\n"
                f"{exc}\n"
            )
            log_path.write_text(message, encoding="utf-8")
            return CommandResult(
                command=command_list,
                cwd=cwd,
                return_code=127,
                stdout="",
                stderr=str(exc),
                skipped=True,
                log_path=log_path,
                reason="missing-executable",
            )
        except OSError as exc:
            message = (
                f"[os-error] command failed: {' '.join(command_list)}\n"
                f"{exc}\n"
            )
            log_path.write_text(message, encoding="utf-8")
            return CommandResult(
                command=command_list,
                cwd=cwd,
                return_code=getattr(exc, "errno", 1) or 1,
                stdout="",
                stderr=str(exc),
                skipped=False,
                log_path=log_path,
                reason="os-error",
            )
        log_path.write_text(
            f"$ {' '.join(command_list)}\n\nSTDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}",
            encoding="utf-8",
        )
        return CommandResult(
            command=command_list,
            cwd=cwd,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            skipped=False,
            log_path=log_path,
            reason=None,
        )

    def _skip_reason(self, command: List[str]) -> Optional[str]:
        if not command:
            return "empty-command"
        for prefix in PACKAGE_INSTALL_PREFIXES:
            if len(command) >= len(prefix) and all(a == b for a, b in zip(command, prefix)):
                if not self._policy.allow_package_installs:
                    return "blocked-package-install"
        for prefix in CLI_TOOL_PREFIXES:
            if len(command) >= len(prefix) and all(a == b for a, b in zip(command, prefix)):
                if not self._policy.allow_cli_tools:
                    return "blocked-cli"
        executable = command[0]
        if executable in {"python", "py"}:
            pass
        elif which(executable) is None:
            return "missing-executable"
        return None

    def _create_log_path(self, command: List[str]) -> Path:
        safe = "-".join(part.replace("/", "_").replace(" ", "_") for part in command if part)
        if len(safe) > 60:
            safe = safe[:57] + "..."
        index = len(list(self._logs_dir.glob("*.log"))) + 1
        return self._logs_dir / f"{index:02d}-{safe}.log"
