# WikiDelta Optional Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change `.wd` files so `wd:source_snapshot` is optional and only appears while a file is in `pending_review`.

**Architecture:** Keep `wd:effective` as the stable ingest interface. Update the document parser/writer to allow missing `source_snapshot`, then update lifecycle services so `add` and clean `update/apply` remove redundant snapshots while `update` creates one only when source content differs.

**Tech Stack:** Python 3.11, pytest, Typer CLI, existing `wikidelta.document` and `wikidelta.service` modules.

---

## File Structure

- Modify `src/wikidelta/models.py`: add `sync.state` if needed.
- Modify `src/wikidelta/document.py`: require only `effective`; render optional `source_snapshot`; add section helpers.
- Modify `src/wikidelta/service.py`: update add/update/status/review/apply behavior.
- Modify `README.md` and `README.zh-CN.md`: document optional snapshot behavior.
- Modify tests under `tests/`: update existing expectations and add backward compatibility coverage.

## Task 1: Optional Section Parser And Renderer

**Files:**
- Modify: `src/wikidelta/models.py`
- Modify: `src/wikidelta/document.py`
- Test: `tests/test_document.py`

- [ ] **Step 1: Write failing parser/renderer tests**

Add tests showing:

```python
def test_parse_allows_missing_source_snapshot():
    text = """---
wd_version: 1
id: clean-doc
title: Clean Doc
source:
  fetcher: builtin.file
  fetch:
    path: ./clean.md
  transformer: builtin.markdown
  transform: {}
sync:
  state: up_to_date
---

<!-- wd:effective -->
# Clean
<!-- /wd:effective -->
"""

    doc = WdDocument.parse(text)

    assert doc.section("effective").strip() == "# Clean"
    assert doc.section("source_snapshot", default=None) is None


def test_render_wd_omits_source_snapshot_for_initial_clean_file():
    text = render_wd(
        wd_id="a-doc",
        title="A Doc",
        source={"fetcher": "builtin.file", "fetch": {"path": "./a.md"}, "transformer": "builtin.markdown", "transform": {}},
        content="# A",
    )

    assert "wd:effective" in text
    assert "wd:source_snapshot" not in text
```

Run: `pytest tests/test_document.py -v`
Expected: FAIL because parser still requires `source_snapshot` and renderer still emits it.

- [ ] **Step 2: Implement optional section support**

Implement:

```python
def section(self, name: str, default: str | None = None) -> str | None:
    return self.sections.get(name, default)

def remove_section(self, name: str) -> None:
    self.sections.pop(name, None)
```

Parser should require only `effective`. Writer should output sections in order: `effective`, optional `source_snapshot`, optional `notes`, then any extra sections. `render_wd` should set `sync.state = "up_to_date"`, `snapshot_hash = None`, and only include `effective` and `notes`.

Run: `pytest tests/test_document.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/wikidelta/models.py src/wikidelta/document.py tests/test_document.py
git commit -m "feat: support optional wd source snapshots"
```

## Task 2: Lifecycle Semantics

**Files:**
- Modify: `src/wikidelta/service.py`
- Modify: `src/wikidelta/cli.py` only if command output needs clearer messages.
- Test: `tests/test_cli_add.py`
- Test: `tests/test_lifecycle.py`

- [ ] **Step 1: Write failing lifecycle tests**

Add or update tests showing:

```python
def test_add_does_not_write_source_snapshot(tmp_path):
    source = tmp_path / "a.md"
    source.write_text("# A\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["add", str(source), "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 0
    text = (tmp_path / "raw_source" / "a.wd").read_text(encoding="utf-8")
    assert "wd:effective" in text
    assert "wd:source_snapshot" not in text


def test_update_same_content_keeps_file_clean_without_snapshot(tmp_path):
    source, wd_path = _add_doc(tmp_path)

    result = CliRunner().invoke(app, ["update", str(wd_path), "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 0
    doc = WdDocument.parse(wd_path.read_text(encoding="utf-8"))
    assert doc.section("source_snapshot", default=None) is None
    assert doc.meta.sync.state == "up_to_date"


def test_review_without_snapshot_returns_clean_and_suggests_update(tmp_path):
    source, wd_path = _add_doc(tmp_path)

    result = CliRunner().invoke(app, ["review", str(wd_path), "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert '"state": "clean"' in result.stdout
    assert "wd update" in result.stdout
    assert not (tmp_path / ".wikidelta" / "reviews" / "a.patch").exists()
```

Run: `pytest tests/test_cli_add.py tests/test_lifecycle.py -v`
Expected: FAIL because current lifecycle still writes and requires `source_snapshot`.

- [ ] **Step 2: Implement lifecycle behavior**

Change service behavior:

- `add_source` keeps using `render_wd`; no separate snapshot should be created.
- `update_document` compares transformed content with `effective`.
- If equal: remove `source_snapshot`, set `sync.state = "up_to_date"`, `snapshot_hash = None`.
- If different: set `source_snapshot`, set `sync.state = "pending_review"`, update `snapshot_hash`.
- `status_items` treats missing `source_snapshot` as clean.
- `write_review` returns a clean review payload with an action suggesting `wd update` when snapshot is missing and does not write patch files.
- `apply_review` fails clearly when snapshot is missing; after replace, remove snapshot and set state to `up_to_date`.

Run: `pytest tests/test_cli_add.py tests/test_lifecycle.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/wikidelta/service.py src/wikidelta/cli.py tests/test_cli_add.py tests/test_lifecycle.py
git commit -m "feat: apply optional snapshot lifecycle"
```

## Task 3: Compatibility, Docs, And End-To-End Verification

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `tests/test_cli_e2e.py`
- Modify: `tests/test_ingest.py`

- [ ] **Step 1: Write compatibility and e2e tests**

Add concrete tests with these assertions:

- `test_existing_duplicate_snapshot_is_treated_as_clean`: write a legacy `.wd` file containing both `wd:effective` and an identical `wd:source_snapshot`, run `wd status --json`, and assert the state is `clean`.
- `test_apply_removes_snapshot_and_ingest_outputs_only_effective`: create a `.wd`, change the source, run `wd update`, assert `wd:source_snapshot` exists, run `wd apply --strategy replace --yes`, assert `wd:source_snapshot` is removed, then run `wd ingest --json` and assert output contains the accepted content but not `source_snapshot`.

Run: `pytest tests/test_cli_e2e.py tests/test_ingest.py -v`
Expected: FAIL until lifecycle and docs expectations are aligned.

- [ ] **Step 2: Update docs and fix e2e wiring**

Update README examples so initial `.wd` examples omit `wd:source_snapshot`, and explain that snapshot appears only during `pending_review`.

Run: `pytest -v`
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add README.md README.zh-CN.md tests/test_cli_e2e.py tests/test_ingest.py
git commit -m "docs: document optional snapshot lifecycle"
```

## Final Verification

Run:

```bash
pytest -v
wd add /tmp/example.md --json
```

Expected:

- Test suite exits 0.
- New `.wd` files created by `wd add` contain `wd:effective` and no `wd:source_snapshot` until source content changes and `wd update` runs.
