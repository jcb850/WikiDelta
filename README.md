# WikiDelta

[中文说明](./README.zh-CN.md) | English

WikiDelta is a `.wd` knowledge-source lifecycle tool for llmwiki. It wraps knowledge sources from the file system into maintainable `.wd` files: each file stores the currently effective content and source configuration, and only stores a source snapshot while there is candidate content waiting for review.

The first version follows one clear constraint:

```text
1 .wd file = 1 knowledge unit = 1 source = 1 effective content section
```

## Use Cases

- Knowledge sources are maintained in the file system, but the file types vary, such as Markdown, text, HTML, JSON, PDF, and web pages.
- You want an explicit concept of "currently effective content" to prevent source refreshes from directly polluting the knowledge base.
- The llmwiki project's raw source directory needs a source-file format that is easier to maintain continuously and operate with agents.
- Agents need a stable CLI and JSON output to maintain the knowledge-source lifecycle.

## `.wd` File Structure

A `.wd` file is essentially a Markdown file composed of YAML front matter and named content sections:

```markdown
---
wd_version: 1
id: pricing-policy
title: Pricing Rules
status: active
content_type: markdown
tags:
  - pricing
  - policy
source:
  fetcher: builtin.file
  fetch:
    path: ./pricing.md
  transformer: builtin.markdown
  transform: {}
sync:
  strategy: review_before_apply
---

<!-- wd:effective -->
# Pricing Rules

This is the currently effective content and will be imported into llmwiki.
<!-- /wd:effective -->

<!-- wd:notes -->
Maintenance notes, review decisions, and why certain source changes were accepted or rejected.
<!-- /wd:notes -->
```

When `wd update` finds source content that differs from `wd:effective`, WikiDelta adds a temporary candidate section:

```markdown
<!-- wd:source_snapshot -->
# Pricing Rules

This is the latest candidate content fetched and transformed from the source.
<!-- /wd:source_snapshot -->
```

Core rules:

- `wd:effective` is the only content imported into the knowledge base by default.
- `wd:source_snapshot` is optional candidate content for review and diffing, and is not imported directly.
- `wd:notes` contains maintenance notes and is not imported into llmwiki by default.
- `id` is the stable identity of the knowledge unit, used for status, caching, review, and future upsert operations.
- The first `wd add` writes only `effective`; later `wd update` creates `source_snapshot` only when source content differs.

## Installation and Running

This project is currently a Python CLI package. In a development environment, you can run it directly with `PYTHONPATH`:

```bash
PYTHONPATH=src python3 -m wikidelta.cli --help
```

Install it as a local executable command:

```bash
pip install -e .
wd --help
```

## Quick Start

Initialize a workspace:

```bash
wd init --mode llmwiki_project
```

Wrap a local Markdown file into a `.wd` file:

```bash
wd add ./policy.md --into raw_sources/policy
```

Refresh candidate snapshots after source files change. Without a path, WikiDelta updates every `.wd` file in the workspace:

```bash
wd update
```

Pass a path when you only want to update one `.wd` file:

```bash
wd update raw_sources/policy/policy.wd
```

Check status:

```bash
wd status --json
```

Generate review materials:

```bash
wd review raw_sources/policy/policy.wd --json
```

Accept the candidate content as the effective content:

```bash
wd apply raw_sources/policy/policy.wd --strategy replace --yes
```

Extract only `wd:effective` as an llmwiki-compatible bridge:

```bash
wd ingest raw_sources/policy/policy.wd --json
```

## CLI Commands

```text
wd init      Initialize the .wikidelta state directory
wd add       Create a .wd file from a local file or URL
wd update    Refresh all .wd files, or one .wd file when a path is provided
wd status    Scan .wd status
wd review    Generate review JSON and patch files
wd apply     Apply candidate content to effective
wd ingest    Extract effective as an llmwiki-compatible bridge
```

When `wd status` succeeds but pending review content exists, it returns exit code `3`. This is not an execution failure; it tells agents or scripts that pending review needs to be handled.

## Built-in Sources and Transforms

`wd add` automatically infers common source pipelines from the input:

```text
*.md        builtin.file + builtin.markdown
*.txt       builtin.file + builtin.text
*.html      builtin.file + builtin.text
*.json      builtin.file + builtin.json_to_markdown
*.pdf       builtin.file + builtin.pdf_to_markdown
http(s)://  builtin.http + builtin.html_to_markdown
```

You can also maintain the source configuration manually in a `.wd` file:

```yaml
source:
  fetcher: builtin.http
  fetch:
    url: https://example.com/policy
  transformer: builtin.html_to_markdown
  transform:
    selector: main
```

## llmwiki Project Mode

The recommended layout is to place `.wd` files directly inside the raw source file structure of an llmwiki project:

```text
llmwiki-project/
  raw_sources/
    pricing/pricing-policy.wd
    policy/refund-policy.wd
```

In this mode, the project a `.wd` file belongs to is determined by directory context. You do not need to configure llmwiki `base_url` or `project` for every `.wd` file.

The import rule is: llmwiki or a compatible bridge may only read `wd:effective`; it must not import the entire `.wd` file as ordinary Markdown, otherwise the source configuration, candidate snapshot, and notes will pollute the knowledge base.

## Agent-Friendly Conventions

Main commands support JSON output and an explicit workspace:

```bash
wd status --workspace /path/to/repo --json
```

Lifecycle operations that affect `effective` require explicit confirmation:

```bash
wd apply path/to/file.wd --strategy replace --yes
```

Recommended agent workflow:

```text
1. wd status --json
2. Run wd review --json for files in pending_review
3. Read .wikidelta/reviews/<id>.json and .patch
4. Decide whether to accept the changes
5. wd apply <file.wd> --strategy replace --yes
6. wd ingest <file.wd> --json
```

## Script Extensions

Complex sources can use `script.python`. The script reads JSON from stdin and writes JSON to stdout.

`.wd` example:

```yaml
source:
  fetcher: script.python
  fetch:
    entry: ./fetchers/feishu_doc.py
    args:
      doc_id: abc123
  transformer: builtin.markdown
  transform: {}
```

Successful output:

```json
{
  "ok": true,
  "contentType": "text/plain",
  "content": "Fetched content",
  "metadata": {}
}
```

Failed output:

```json
{
  "ok": false,
  "error": {
    "code": "AUTH_FAILED",
    "message": "Missing token",
    "retryable": false
  }
}
```

Credentials should be passed to scripts through environment variables and should not be written into `.wd` files.

## Testing

Run the full test suite:

```bash
pytest -v
```

Current tests cover `.wd` parsing, repository initialization, source inference, `wd add/update/status/review/apply/ingest`, the script protocol, and the end-to-end lifecycle.
