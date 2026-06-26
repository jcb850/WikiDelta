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
    assert doc.meta.sync.effective_hash == doc.meta.sync.snapshot_hash
