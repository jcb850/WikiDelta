from pathlib import Path

from typer.testing import CliRunner

from wikidelta.cli import app


def test_ingest_outputs_only_effective_content(tmp_path: Path):
    source = tmp_path / "a.md"
    source.write_text("# A\n\nEffective", encoding="utf-8")
    runner = CliRunner()
    add = runner.invoke(app, ["add", str(source), "--into", str(tmp_path / "raw_sources"), "--workspace", str(tmp_path), "--json"])
    assert add.exit_code == 0
    wd_path = tmp_path / "raw_sources" / "a.wd"

    result = runner.invoke(app, ["ingest", str(wd_path), "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert '"content": "# A\\n\\nEffective"' in result.stdout
    assert "source_snapshot" not in result.stdout
    assert "builtin.file" not in result.stdout
