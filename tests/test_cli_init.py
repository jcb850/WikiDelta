from typer.testing import CliRunner

from wikidelta.cli import app


def test_init_json_creates_layout(tmp_path):
    runner = CliRunner()

    result = runner.invoke(app, ["init", "--workspace", str(tmp_path), "--mode", "llmwiki_project", "--json"])

    assert result.exit_code == 0
    assert '"ok": true' in result.stdout
    assert '"mode": "llmwiki_project"' in result.stdout
    assert (tmp_path / ".wikidelta" / "config.yaml").exists()
