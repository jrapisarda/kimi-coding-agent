from __future__ import annotations

import json
import shutil
from datetime import datetime
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .orchestrator import AgentResult


@dataclass
class PackagingResult:
    """Metadata describing the artifact bundle produced for a run."""

    status: str
    output_path: Path
    files: List[str]


class ArtifactPackager:
    """Produce a `dist/<run_id>.zip` bundle with manifest, artifacts, and SBOM."""

    def __init__(self, dist_dir: Path) -> None:
        self._dist_dir = Path(dist_dir)
        self._dist_dir.mkdir(parents=True, exist_ok=True)

    def package(
        self,
        run_id: str,
        target_path: Path,
        agent_results: Iterable["AgentResult"],
        metadata: dict,
    ) -> PackagingResult:
        run_zip = self._dist_dir / f"{run_id}.zip"
        agent_results_list = list(agent_results)
        manifest = {
            "run_id": run_id,
            "target_path": str(target_path),
            "metadata": metadata,
            "agents": [
                {
                    "name": result.name,
                    "status": result.status,
                    "summary": result.summary,
                    "details": result.details,
                    "artifacts": result.artifacts,
                }
                for result in agent_results_list
            ],
        }

        files: List[str] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            manifest_path = tmpdir_path / "manifest.json"
            provenance_path = tmpdir_path / "provenance.json"
            provenance_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            files.append("provenance.json")
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            files.append("manifest.json")

            notes_path = tmpdir_path / "README.txt"
            notes_path.write_text(
                "Sprint 5 bundle containing manifest, agent artifacts, SBOM, dependency manifests, and execution logs.",
                encoding="utf-8",
            )
            files.append("README.txt")

            artifacts_root = tmpdir_path / "artifacts"
            artifacts_root.mkdir(parents=True, exist_ok=True)
            for result in agent_results_list:
                agent_dir = artifacts_root / result.name
                agent_dir.mkdir(parents=True, exist_ok=True)
                for filename, artifact in result.artifacts.items():
                    payload = artifact.get("payload")
                    if payload is None:
                        continue
                    artifact_path = agent_dir / filename
                    artifact_type = artifact.get("type", "")
                    if artifact_type.endswith("json") or filename.endswith(".json"):
                        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    else:
                        artifact_path.write_text(str(payload), encoding="utf-8")
                    files.append(str(Path("artifacts") / result.name / filename))

            sbom_path = tmpdir_path / "sbom.json"
            sbom_path.write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "generated_at": datetime.utcnow().isoformat(),
                        "project_type": metadata.get("coding.project_type"),
                        "dependencies": _extract_dependencies(agent_results_list),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            files.append("sbom.json")

            logs_dir_value = metadata.get("run.logs_dir")
            if logs_dir_value:
                logs_path = Path(logs_dir_value)
                if logs_path.exists():
                    logs_archive_dir = tmpdir_path / "logs"
                    logs_archive_dir.mkdir(parents=True, exist_ok=True)
                    for log_file in sorted(logs_path.glob("*.log")):
                        shutil.copy(log_file, logs_archive_dir / log_file.name)
                        files.append(str(Path("logs") / log_file.name))

            with zipfile.ZipFile(run_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file_path in tmpdir_path.rglob("*"):
                    if file_path.is_file():
                        archive.write(file_path, arcname=str(file_path.relative_to(tmpdir_path)))

        return PackagingResult(status="succeeded", output_path=run_zip, files=sorted(set(files)))


def _extract_dependencies(agent_results: Iterable["AgentResult"]) -> List[str]:
    dependencies: List[str] = []
    for result in agent_results:
        if result.name != "coding":
            continue
        scaffold = result.artifacts.get("scaffold.json", {}).get("payload", {})
        for source, deps in scaffold.get("dependencies", {}).items():
            for name, version in deps.items():
                dependencies.append(f"{source}:{name}=={version}")
        for manifest in scaffold.get("resolved_manifests", []):
            packages = manifest.get("packages", {}) or {}
            source = manifest.get("source", manifest.get("command", "unknown"))
            for name, version in packages.items():
                dependencies.append(f"{source}:{name}=={version}")
    return sorted(set(dependencies))
