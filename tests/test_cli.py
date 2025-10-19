from click.testing import CliRunner

from kimi_agent.cli import main


def test_cli_dry_run():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "run",
                "projects/sample",
                "--dry-run",
                "--prompt",
                "Generate Next.js 15 dashboard",
            ],
        )
        assert result.exit_code == 0
        assert "status: succeeded" in result.output.lower()
