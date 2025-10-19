from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..orchestrator import Agent, AgentContext, AgentResult
from ..scaffolding import scaffold_project


@dataclass
class CodingPlan:
    project_type: str
    tasks: List[str]
    commands: List[str]
    files: List[str]
    notes: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        return {
            'project_type': self.project_type,
            'tasks': self.tasks,
            'commands': self.commands,
            'files': self.files,
            'notes': self.notes,
        }


class CodingAgent(Agent):
    name = 'coding'

    def execute(self, context: AgentContext) -> AgentResult:
        requirements = context.outputs.get('requirements')
        requirements_summary = requirements.summary if requirements else 'No requirements summary available.'
        project_type = _classify_project(context.request.prompt, requirements_summary)

        plan_prompt = (
            "You are the Coding Agent. Produce a concise implementation plan for the project described.\n"
            f"Project Type: {project_type}\n"
            f"Requirements Summary: {requirements_summary}\n"
            "List the key coding tasks, recommended commands, and primary files to create.\n"
        )
        context.run_metadata['coding.plan_prompt'] = plan_prompt
        context.run_metadata['coding.model'] = getattr(context.openai, 'model', 'unknown')
        plan_text = context.openai.generate_text(plan_prompt)
        coding_plan = _build_plan(project_type, context.request.target_path, plan_text)
        context.run_metadata['coding.project_type'] = project_type

        scaffold_payload: Dict[str, Any] = {'status': 'skipped', 'files_created': [], 'dependencies': {}}
        cli_checks: List[Dict[str, Any]] = []
        if not context.request.dry_run:
            scaffold_result = scaffold_project(project_type, context.request.target_path)
            dependencies_versions = _merge_dependency_maps(
                scaffold_result.dependencies,
                _collect_dependency_versions(context.request.target_path),
            )
            scaffold_payload = {
                'status': 'generated',
                'files_created': scaffold_result.files_created,
                'notes': scaffold_result.notes,
                'dependencies': dependencies_versions,
            }
            context.run_metadata['coding.dependencies'] = dependencies_versions
            context.run_metadata['coding.files_created'] = scaffold_result.files_created
            context.run_metadata['coding.notes'] = scaffold_result.notes

            context.command_runner.run(
                ['python', '-c', f"print('scaffold completed for {project_type}')"],
                cwd=context.request.target_path,
            )

            cli_runs: List[Dict[str, Any]] = []
            for command in _real_scaffold_commands(project_type, context.config.sandbox):
                result = context.command_runner.run(command, cwd=context.request.target_path)
                cli_runs.append(
                    {
                        'command': ' '.join(command),
                        'status': _result_status(result),
                        'reason': result.reason,
                        'return_code': result.return_code,
                        'log_path': str(result.log_path) if result.log_path else None,
                    }
                )
            if cli_runs:
                scaffold_payload['cli_runs'] = cli_runs
                context.run_metadata['coding.cli_runs'] = cli_runs

            if context.config.sandbox.allow_cli_tools:
                for cli_command in _cli_health_checks(project_type):
                    result = context.command_runner.run(cli_command, cwd=context.request.target_path)
                    cli_checks.append(
                        {
                            'command': ' '.join(cli_command),
                            'status': _result_status(result),
                            'reason': result.reason,
                            'return_code': result.return_code,
                            'log_path': str(result.log_path) if result.log_path else None,
                        }
                    )
                if cli_checks:
                    scaffold_payload['cli_checks'] = cli_checks
                    context.run_metadata['coding.cli_checks'] = cli_checks

            resolved_manifests = _collect_resolved_manifests(context, project_type)
            if resolved_manifests:
                scaffold_payload['resolved_manifests'] = resolved_manifests
                context.run_metadata['coding.resolved_manifests'] = resolved_manifests
        else:
            scaffold_payload['dependencies'] = {}

        details = {
            'project_type': project_type,
            'tasks': coding_plan.tasks,
            'commands': coding_plan.commands,
            'files': coding_plan.files,
            'notes': coding_plan.notes,
            'scaffold_status': scaffold_payload['status'],
            'files_created': scaffold_payload.get('files_created', []),
            'dependencies': scaffold_payload.get('dependencies', {}),
            'cli_checks': scaffold_payload.get('cli_checks', []),
            'cli_runs': scaffold_payload.get('cli_runs', []),
        }
        artifacts: Dict[str, Dict[str, Any]] = {
            'coding_plan.json': {
                'type': 'application/json',
                'payload': coding_plan.as_dict(),
            },
            'coding_plan.md': {
                'type': 'text/markdown',
                'payload': _format_plan_markdown(project_type, coding_plan, plan_text),
            },
            'scaffold.json': {
                'type': 'application/json',
                'payload': scaffold_payload,
            },
        }
        if scaffold_payload.get('dependencies'):
            artifacts['dependencies.json'] = {
                'type': 'application/json',
                'payload': scaffold_payload['dependencies'],
            }
        if not context.request.dry_run and scaffold_payload.get('files_created'):
            artifacts['scaffold.md'] = {
                'type': 'text/markdown',
                'payload': _format_scaffold_markdown(project_type, scaffold_payload),
            }

        return AgentResult(
            name=self.name,
            status='succeeded',
            summary=f'Coding plan prepared for {project_type}.',
            details=details,
            artifacts=artifacts,
        )


def _classify_project(prompt: Optional[str], requirements_summary: str) -> str:
    text = ' '.join(filter(None, [prompt or '', requirements_summary])).lower()
    if any(token in text for token in ('next.js', 'nextjs', 'react dashboard')):
        return 'nextjs-dashboard'
    if 'fastapi' in text or 'crud' in text:
        return 'fastapi-crud-api'
    if 'etl' in text or 'sqlite' in text:
        return 'python-etl-sqlite'
    if 'scikit' in text or 'classifier' in text or 'ml' in text:
        return 'sklearn-ml-experiment'
    return 'generic-software-project'


def _build_plan(project_type: str, target_path: Path, plan_text: str) -> CodingPlan:
    tasks = [
        'Initialise repository structure and configuration.',
        'Generate baseline code scaffolding aligning with requirements.',
        'Create smoke tests to validate critical paths.',
    ]
    commands = ['git init' if project_type != 'generic-software-project' else 'mkdir -p src']
    files = ['README.md', 'tests/'] if project_type != 'generic-software-project' else ['docs/notes.md']
    notes = plan_text

    if project_type == 'nextjs-dashboard':
        commands.extend(
            [
                'npm create next-app@latest . --use-npm --ts --app --eslint',
                'npm install @tanstack/react-table',
            ]
        )
        files.extend(['app/page.tsx', 'app/layout.tsx'])
    elif project_type == 'fastapi-crud-api':
        commands.extend(['python -m pip install fastapi uvicorn', 'mkdir -p app/api'])
        files.extend(['app/main.py', 'app/api/routes.py', 'app/models.py'])
    elif project_type == 'python-etl-sqlite':
        commands.extend(['python -m pip install pandas sqlite-utils', 'mkdir -p jobs'])
        files.extend(['jobs/etl.py', 'data/sample.csv'])
    elif project_type == 'sklearn-ml-experiment':
        commands.extend(['python -m pip install scikit-learn pandas', 'mkdir -p experiments'])
        files.extend(['experiments/train.py', 'experiments/config.yaml'])

    return CodingPlan(
        project_type=project_type,
        tasks=tasks,
        commands=commands,
        files=files,
        notes=notes,
    )


def _real_scaffold_commands(project_type: str, policy) -> List[List[str]]:
    if not getattr(policy, 'allow_cli_tools', False):
        return []
    commands: List[List[str]] = []
    if project_type == 'nextjs-dashboard':
        commands.append(['npm', 'create', 'next-app@latest', '.', '--use-npm', '--ts', '--app', '--eslint'])
        if getattr(policy, 'allow_package_installs', False):
            commands.append(['npm', 'install'])
    elif project_type == 'fastapi-crud-api' and getattr(policy, 'allow_package_installs', False):
        commands.append(['python', '-m', 'pip', 'install', '-r', 'requirements.txt'])
    elif project_type == 'python-etl-sqlite' and getattr(policy, 'allow_package_installs', False):
        commands.append(['python', '-m', 'pip', 'install', '-r', 'requirements.txt'])
    elif project_type == 'sklearn-ml-experiment' and getattr(policy, 'allow_package_installs', False):
        commands.append(['python', '-m', 'pip', 'install', '-r', 'requirements.txt'])
    return commands


def _cli_health_checks(project_type: str) -> List[List[str]]:
    if project_type == 'nextjs-dashboard':
        return [['npm', '--version']]
    if project_type == 'fastapi-crud-api':
        return [['python', '-m', 'pip', '--version']]
    return []


def _dependency_resolvers(project_type: str, allow_cli: bool) -> List[List[str]]:
    commands: List[List[str]] = [['python', '-m', 'pip', 'freeze']]
    if allow_cli and project_type == 'nextjs-dashboard':
        commands.append(['npm', 'ls', '--json', '--depth=0'])
    return commands


def _collect_resolved_manifests(context: AgentContext, project_type: str) -> List[Dict[str, Any]]:
    manifests: List[Dict[str, Any]] = []
    for command in _dependency_resolvers(project_type, context.config.sandbox.allow_cli_tools):
        result = context.command_runner.run(command, cwd=context.request.target_path)
        packages: Dict[str, str] | None = None
        source = 'pip-freeze' if command[:4] == ['python', '-m', 'pip', 'freeze'] else 'npm-ls'
        if not result.skipped and result.return_code == 0:
            if source == 'pip-freeze':
                packages = _parse_pip_freeze(result.stdout)
            elif source == 'npm-ls':
                packages = _parse_npm_ls(result.stdout)
        manifests.append(
            {
                'command': ' '.join(command),
                'source': source,
                'status': _result_status(result),
                'reason': result.reason,
                'return_code': result.return_code,
                'log_path': str(result.log_path) if result.log_path else None,
                'packages': packages or {},
                'stdout_excerpt': (result.stdout or '')[:2000],
            }
        )
    return manifests


def _result_status(result) -> str:
    if result.skipped:
        return 'skipped'
    if result.return_code == 0:
        return 'succeeded'
    return 'failed'


def _format_plan_markdown(project_type: str, plan: CodingPlan, plan_text: str) -> str:
    lines = [
        f'# Coding Plan ({project_type})',
        '',
        '## Primary Tasks',
        '\n'.join(f'- {task}' for task in plan.tasks),
        '',
        '## Suggested Commands',
        '\n'.join(f'- `{cmd}`' for cmd in plan.commands),
        '',
        '## Key Files / Directories',
        '\n'.join(f'- {path}' for path in plan.files),
        '',
        '## Model Notes',
        plan_text,
        '',
    ]
    return '\n'.join(lines)


def _format_scaffold_markdown(project_type: str, payload: Dict[str, object]) -> str:
    files = payload.get('files_created', [])
    dependencies = payload.get('dependencies', {})
    cli_checks = payload.get('cli_checks', [])
    cli_runs = payload.get('cli_runs', [])
    resolved_manifests = payload.get('resolved_manifests', [])
    lines = [
        f'# Scaffold Summary ({project_type})',
        '',
        '## Files Created',
        '\n'.join(f'- {item}' for item in files) if files else '- None',
        '',
        '## Dependencies',
    ]
    if dependencies:
        for source, deps in dependencies.items():
            pretty = ', '.join(f'{pkg}=={version}' for pkg, version in deps.items())
            lines.append(f'- **{source}**: {pretty}')
    else:
        lines.append('- None')
    lines.extend([
        '',
        '## CLI Checks',
    ])
    if cli_checks:
        for check in cli_checks:
            reason = f" (reason: {check['reason']})" if check.get('reason') else ''
            lines.append(f"- {check['command']} -> {check.get('status', 'unknown')}{reason}")
    else:
        lines.append('- None')
    lines.extend([
        '',
        '## CLI Runs',
    ])
    if cli_runs:
        for entry in cli_runs:
            reason = f" (reason: {entry['reason']})" if entry.get('reason') else ''
            lines.append(f"- {entry['command']} -> {entry.get('status', 'unknown')}{reason}")
    else:
        lines.append('- None')
    lines.extend([
        '',
        '## Resolved Manifests',
    ])
    if resolved_manifests:
        for manifest in resolved_manifests:
            status = manifest.get('status', 'unknown')
            source = manifest.get('source', 'unknown-source')
            lines.append(f'- {source} ({status})')
    else:
        lines.append('- None')
    lines.extend([
        '',
        '## Notes',
        str(payload.get('notes', '')),
        '',
    ])
    return '\n'.join(lines)


def _collect_dependency_versions(target_path: Path) -> Dict[str, Dict[str, str]]:
    dependencies: Dict[str, Dict[str, str]] = {}
    package_json = target_path / 'package.json'
    if package_json.exists():
        data = json.loads(package_json.read_text(encoding='utf-8'))
        npm_deps: Dict[str, str] = {}
        for section in ('dependencies', 'devDependencies'):
            for name, version in data.get(section, {}).items():
                npm_deps[name] = version
        if npm_deps:
            dependencies['npm'] = npm_deps

    pip_deps: Dict[str, str] = {}
    for requirements_file in ['requirements.txt', 'requirements-dev.txt']:
        req_path = target_path / requirements_file
        if not req_path.exists():
            continue
        for line in req_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '==' in line:
                name, version = line.split('==', 1)
                pip_deps[name.strip()] = version.strip()
    if pip_deps:
        dependencies['pip'] = pip_deps
    return dependencies


def _merge_dependency_maps(
    primary: Dict[str, Dict[str, str]],
    secondary: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    for source, deps in secondary.items():
        merged[source] = dict(deps)
    for source, deps in primary.items():
        merged.setdefault(source, {})
        merged[source].update(deps)
    return merged


def _parse_pip_freeze(stdout: str) -> Dict[str, str]:
    packages: Dict[str, str] = {}
    for line in stdout.splitlines():
        if '==' in line:
            name, version = line.split('==', 1)
            packages[name.strip()] = version.strip()
    return packages


def _parse_npm_ls(stdout: str) -> Dict[str, str]:
    try:
        data = json.loads(stdout or '{}')
    except json.JSONDecodeError:
        return {}
    deps = data.get('dependencies', {})
    packages: Dict[str, str] = {}
    for name, meta in deps.items():
        version = meta.get('version')
        if version:
            packages[name] = version
    return packages
