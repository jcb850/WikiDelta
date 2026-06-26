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
    assert "source_snapshot" not in wd_path.read_text(encoding="utf-8")
    ingest = runner.invoke(app, ["ingest", str(wd_path), "--workspace", str(tmp_path), "--json"])

    assert ingest.exit_code == 0
    assert "Version two" in ingest.stdout
    assert "source_snapshot" not in ingest.stdout


def test_existing_duplicate_snapshot_is_treated_as_clean(tmp_path: Path):
    runner = CliRunner()
    assert runner.invoke(app, ["init", "--workspace", str(tmp_path), "--json"]).exit_code == 0
    raw_sources = tmp_path / "raw_source"
    raw_sources.mkdir()
    wd_path = raw_sources / "legacy.wd"
    wd_path.write_text(
        """---
wd_version: 1
id: legacy
title: Legacy
source:
  fetcher: builtin.file
  fetch:
    path: ./legacy.md
  transformer: builtin.markdown
  transform: {}
sync:
  strategy: review_before_apply
  effective_hash: sha256:unused
  snapshot_hash: sha256:unused
---

<!-- wd:effective -->
# Legacy
<!-- /wd:effective -->

<!-- wd:source_snapshot -->
# Legacy
<!-- /wd:source_snapshot -->
""",
        encoding="utf-8",
    )

    status = runner.invoke(app, ["status", "--workspace", str(tmp_path), "--json"])

    assert status.exit_code == 0
    assert '"state": "clean"' in status.stdout
