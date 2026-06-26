# WikiDelta .wd Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that manages `.wd` lifecycle files for llmwiki raw-source workflows.

**Architecture:** The implementation is a small Python package with focused modules: document parsing/writing, repository discovery, source fetching/transforming, lifecycle services, and Typer CLI commands. The first version supports one source per `.wd`, review-before-apply semantics, JSON-friendly agent output, and local llmwiki extraction via `wd ingest`.

**Tech Stack:** Python 3.11+, Typer, Pydantic, PyYAML, pytest, requests, BeautifulSoup/html2text, pypdf.

---

## File Structure

- Create `pyproject.toml`: package metadata, console script, dependencies, pytest config.
- Create `src/wikidelta/__init__.py`: package version.
- Create `src/wikidelta/models.py`: Pydantic models for front matter, source config, command results, review/error records.
- Create `src/wikidelta/document.py`: marker-based `.wd` parser/writer, hash helpers, template rendering.
- Create `src/wikidelta/repository.py`: workspace discovery, `.wikidelta` layout, `.wd` scanning.
- Create `src/wikidelta/sources.py`: built-in fetchers/transformers and script protocol runner.
- Create `src/wikidelta/service.py`: lifecycle operations used by CLI: add, status, update, review, apply, extract effective.
- Create `src/wikidelta/cli.py`: Typer commands and JSON/text output handling.
- Create `tests/`: focused pytest modules mirroring the package modules.

## Task 1: Project Skeleton And Document Parser

**Files:**
- Create: `pyproject.toml`
- Create: `src/wikidelta/__init__.py`
- Create: `src/wikidelta/models.py`
- Create: `src/wikidelta/document.py`
- Test: `tests/test_document.py`

- [ ] **Step 1: Write parser tests first**

Create tests for parsing YAML front matter, required `wd:effective` and `wd:source_snapshot` sections, preserving notes, writing updated sections, and computing sha256 hashes.

Run: `pytest tests/test_document.py -v`
Expected: FAIL because `wikidelta.document` does not exist.

- [ ] **Step 2: Implement minimal models and parser**

Implement `WdDocument.parse(text)`, `WdDocument.to_text()`, `WdDocument.set_section(name, content)`, `content_hash(text)`, and `render_wd(...)`.

Run: `pytest tests/test_document.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml src/wikidelta tests/test_document.py
git commit -m "feat: add wd document parser"
```

## Task 2: Repository Discovery And Init

**Files:**
- Create: `src/wikidelta/repository.py`
- Modify: `src/wikidelta/cli.py`
- Test: `tests/test_repository.py`
- Test: `tests/test_cli_init.py`

- [ ] **Step 1: Write failing tests**

Test `.wikidelta` path creation, scanning nested `.wd` files, ignoring `.wikidelta/cache`, and `wd init --mode llmwiki_project --json` creating config directories.

Run: `pytest tests/test_repository.py tests/test_cli_init.py -v`
Expected: FAIL because repository and CLI are missing.

- [ ] **Step 2: Implement repository and init command**

Implement `Repository`, `find_workspace`, `ensure_layout`, `iter_wd_files`, and Typer `init` command with `--json`, `--workspace`, and `--mode`.

Run: `pytest tests/test_repository.py tests/test_cli_init.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/wikidelta/repository.py src/wikidelta/cli.py tests/test_repository.py tests/test_cli_init.py
git commit -m "feat: add repository init workflow"
```

## Task 3: Built-In Sources And `wd add`

**Files:**
- Create: `src/wikidelta/sources.py`
- Create: `src/wikidelta/service.py`
- Modify: `src/wikidelta/cli.py`
- Test: `tests/test_sources.py`
- Test: `tests/test_cli_add.py`

- [ ] **Step 1: Write failing tests**

Test local Markdown and text transforms, HTML selector extraction, JSON-to-Markdown rendering, fetch errors, and `wd add ./a.md --into raw_sources --json` creating a `.wd` whose effective and snapshot match.

Run: `pytest tests/test_sources.py tests/test_cli_add.py -v`
Expected: FAIL because source and add services are missing.

- [ ] **Step 2: Implement built-ins and add workflow**

Implement `builtin.file`, `builtin.http`, Markdown/text/html/json transformers, PDF best-effort transformer, source inference, slug/id generation, and `wd add`.

Run: `pytest tests/test_sources.py tests/test_cli_add.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/wikidelta/sources.py src/wikidelta/service.py src/wikidelta/cli.py tests/test_sources.py tests/test_cli_add.py
git commit -m "feat: add source pipelines and wd add"
```

## Task 4: Status, Update, Review, Apply

**Files:**
- Modify: `src/wikidelta/service.py`
- Modify: `src/wikidelta/cli.py`
- Test: `tests/test_lifecycle.py`

- [ ] **Step 1: Write failing lifecycle tests**

Test `wd update` changes only `source_snapshot`, `wd status --json` reports `pending_review`, `wd review --json` writes JSON and patch artifacts, and `wd apply --strategy replace --yes` replaces effective.

Run: `pytest tests/test_lifecycle.py -v`
Expected: FAIL because lifecycle operations are missing.

- [ ] **Step 2: Implement lifecycle operations**

Implement status calculation, update snapshot, review artifact generation with unified diff, replace apply, and structured errors under `.wikidelta/errors`.

Run: `pytest tests/test_lifecycle.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/wikidelta/service.py src/wikidelta/cli.py tests/test_lifecycle.py
git commit -m "feat: add wd lifecycle commands"
```

## Task 5: Script Protocol And Effective Extraction

**Files:**
- Modify: `src/wikidelta/sources.py`
- Modify: `src/wikidelta/service.py`
- Modify: `src/wikidelta/cli.py`
- Test: `tests/test_script_protocol.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write failing tests**

Test `script.python` receives JSON on stdin, returns content on stdout, timeout/failure writes structured error records, and `wd ingest <path> --json` extracts only `wd:effective` without snapshot/config/notes.

Run: `pytest tests/test_script_protocol.py tests/test_ingest.py -v`
Expected: FAIL because script protocol and ingest extraction are missing.

- [ ] **Step 2: Implement script runner and ingest extraction**

Implement subprocess JSON protocol, timeout handling, error normalization, and local `wd ingest` that emits extracted records for llmwiki compatibility.

Run: `pytest tests/test_script_protocol.py tests/test_ingest.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/wikidelta/sources.py src/wikidelta/service.py src/wikidelta/cli.py tests/test_script_protocol.py tests/test_ingest.py
git commit -m "feat: add script protocol and effective extraction"
```

## Task 6: End-To-End Verification And Docs

**Files:**
- Create: `README.md`
- Modify: `docs/superpowers/specs/2026-06-26-wikidelta-wd-lifecycle-design.md` only if implementation discovers a required clarification.
- Test: `tests/test_cli_e2e.py`

- [ ] **Step 1: Write e2e tests**

Test the full path: `init`, `add`, source file edit, `update`, `status`, `review`, `apply`, and `ingest` using Typer's CliRunner.

Run: `pytest tests/test_cli_e2e.py -v`
Expected: FAIL until any missing wiring is fixed.

- [ ] **Step 2: Fix wiring and write README**

Document `.wd` format, common CLI commands, agent flags, and llmwiki project mode.

Run: `pytest -v`
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add README.md tests/test_cli_e2e.py src/wikidelta docs/superpowers/plans/2026-06-26-wikidelta-wd-lifecycle.md
git commit -m "docs: add wikidelta usage guide"
```

## Final Verification

Run:

```bash
pytest -v
python -m wikidelta.cli --help
```

Expected: pytest exits 0, and CLI help lists `init`, `add`, `status`, `update`, `review`, `apply`, and `ingest`.
