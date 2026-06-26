from pathlib import Path

from typer.testing import CliRunner

from wikidelta.cli import app
from wikidelta.document import WdDocument


def _add_doc(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "a.md"
    source.write_text("# A\n\nOriginal", encoding="utf-8")
    result = CliRunner().invoke(app, ["add", str(source), "--into", str(tmp_path / "raw_sources"), "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 0
    return source, tmp_path / "raw_sources" / "a.wd"


def test_update_changes_snapshot_only_and_status_reports_pending_review(tmp_path: Path):
    source, wd_path = _add_doc(tmp_path)
    source.write_text("# A\n\nChanged", encoding="utf-8")
    runner = CliRunner()

    update = runner.invoke(app, ["update", str(wd_path), "--workspace", str(tmp_path), "--json"])
    status = runner.invoke(app, ["status", "--workspace", str(tmp_path), "--json"])

    assert update.exit_code == 0
    doc = WdDocument.parse(wd_path.read_text(encoding="utf-8"))
    assert doc.section("effective").strip() == "# A\n\nOriginal"
    assert doc.section("source_snapshot").strip() == "# A\n\nChanged"
    assert status.exit_code == 3
    assert '"state": "pending_review"' in status.stdout


def test_update_rejects_non_wd_file_with_json_error(tmp_path: Path):
    source = tmp_path / "source.html"
    source.write_text("<!doctype html><html></html>", encoding="utf-8")
    CliRunner().invoke(app, ["init", "--workspace", str(tmp_path)])

    result = CliRunner().invoke(app, ["update", str(source), "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 1
    assert '"ok": false' in result.stdout
    assert "wd update only accepts .wd files" in result.stdout


def test_update_same_content_keeps_file_clean_without_snapshot(tmp_path: Path):
    _source, wd_path = _add_doc(tmp_path)
    runner = CliRunner()

    update = runner.invoke(app, ["update", str(wd_path), "--workspace", str(tmp_path), "--json"])
    status = runner.invoke(app, ["status", "--workspace", str(tmp_path), "--json"])

    assert update.exit_code == 0
    assert status.exit_code == 0
    doc = WdDocument.parse(wd_path.read_text(encoding="utf-8"))
    assert doc.section("source_snapshot", default=None) is None
    assert doc.meta.sync.state == "up_to_date"


def test_review_without_snapshot_returns_clean_and_suggests_update(tmp_path: Path):
    _source, wd_path = _add_doc(tmp_path)

    result = CliRunner().invoke(app, ["review", str(wd_path), "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert '"state": "clean"' in result.stdout
    assert "wd update" in result.stdout
    assert not (tmp_path / ".wikidelta" / "reviews" / "a.patch").exists()


def test_review_writes_json_and_patch_then_apply_replaces_effective(tmp_path: Path):
    source, wd_path = _add_doc(tmp_path)
    source.write_text("# A\n\nChanged", encoding="utf-8")
    runner = CliRunner()
    assert runner.invoke(app, ["update", str(wd_path), "--workspace", str(tmp_path)]).exit_code == 0

    review = runner.invoke(app, ["review", str(wd_path), "--workspace", str(tmp_path), "--json"])
    apply_result = runner.invoke(app, ["apply", str(wd_path), "--workspace", str(tmp_path), "--strategy", "replace", "--yes", "--json"])

    assert review.exit_code == 0
    assert (tmp_path / ".wikidelta" / "reviews" / "a.json").exists()
    assert (tmp_path / ".wikidelta" / "reviews" / "a.patch").exists()
    assert apply_result.exit_code == 0
    doc = WdDocument.parse(wd_path.read_text(encoding="utf-8"))
    assert doc.section("effective").strip() == "# A\n\nChanged"
    assert doc.section("source_snapshot", default=None) is None
    assert doc.meta.sync.snapshot_hash is None
    assert doc.meta.sync.state == "up_to_date"
