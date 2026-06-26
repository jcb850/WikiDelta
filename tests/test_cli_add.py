from pathlib import Path

from typer.testing import CliRunner

from wikidelta.cli import app
from wikidelta.document import WdDocument


def test_add_markdown_file_creates_wd_with_initial_effective_and_snapshot(tmp_path: Path):
    source = tmp_path / "a.md"
    source.write_text("# A\n\nBody", encoding="utf-8")
    into = tmp_path / "raw_sources"
    runner = CliRunner()

    result = runner.invoke(app, ["add", str(source), "--into", str(into), "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert '"ok": true' in result.stdout
    wd_path = into / "a.wd"
    assert wd_path.exists()
    doc = WdDocument.parse(wd_path.read_text(encoding="utf-8"))
    assert doc.meta.id == "a"
    assert doc.meta.source.fetcher == "builtin.file"
    assert doc.meta.source.transformer == "builtin.markdown"
    assert doc.section("effective").strip() == "# A\n\nBody"
    assert doc.section("source_snapshot").strip() == "# A\n\nBody"


def test_add_defaults_to_raw_source_directory_when_into_is_omitted(tmp_path: Path):
    source = tmp_path / "a.md"
    source.write_text("# A\n\nBody", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["add", str(source), "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert '"path":' in result.stdout
    wd_path = tmp_path / "raw_source" / "a.wd"
    assert wd_path.exists()
    assert not (tmp_path / "a.wd").exists()
