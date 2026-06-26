from pathlib import Path

from typer.testing import CliRunner

from wikidelta.cli import app


def test_full_wd_lifecycle(tmp_path: Path):
    runner = CliRunner()
    source = tmp_path / "policy.md"
    source.write_text("# Policy\n\nVersion one", encoding="utf-8")

    assert runner.invoke(app, ["init", "--workspace", str(tmp_path), "--json"]).exit_code == 0
    add = runner.invoke(app, ["add", str(source), "--into", str(tmp_path / "raw_sources"), "--workspace", str(tmp_path), "--json"])
    assert add.exit_code == 0

    wd_path = tmp_path / "raw_sources" / "policy.wd"
    source.write_text("# Policy\n\nVersion two", encoding="utf-8")

    assert runner.invoke(app, ["update", str(wd_path), "--workspace", str(tmp_path), "--json"]).exit_code == 0
    status = runner.invoke(app, ["status", "--workspace", str(tmp_path), "--json"])
    assert status.exit_code == 3
    assert '"pending_review"' in status.stdout

    assert runner.invoke(app, ["review", str(wd_path), "--workspace", str(tmp_path), "--json"]).exit_code == 0
    assert runner.invoke(app, ["apply", str(wd_path), "--workspace", str(tmp_path), "--strategy", "replace", "--yes", "--json"]).exit_code == 0
    ingest = runner.invoke(app, ["ingest", str(wd_path), "--workspace", str(tmp_path), "--json"])

    assert ingest.exit_code == 0
    assert "Version two" in ingest.stdout
    assert "source_snapshot" not in ingest.stdout
