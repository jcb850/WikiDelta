# WikiDelta .wd Lifecycle Design

Date: 2026-06-26
Status: Draft approved for review

## Purpose

WikiDelta defines a `.wd` file format and CLI workflow for maintaining llmwiki knowledge sources on the filesystem. The core product goal is to make one knowledge source feel like a maintained file: it has current effective content, knows where its source comes from, can refresh a candidate snapshot, and can be reviewed before it affects the knowledge base.

The first version focuses on this invariant:

```text
1 .wd file = 1 knowledge unit = 1 source = 1 effective content block
```

The CLI must be comfortable for humans and predictable for agents. Most llmwiki knowledge bases are expected to be created or maintained by agents, so commands must support non-interactive operation, structured output, stable exit codes, and review artifacts.

## Product Model

`.wd` is a packaged knowledge source file. It is not only an index pointing to external content. It contains the currently effective content that may enter llmwiki, plus source configuration and the latest source snapshot used for review.

The preferred deployment model is llmwiki embedded mode: `.wd` files live directly inside an llmwiki project's raw source tree. In that mode, the surrounding llmwiki project gives the import context, and WikiDelta does not require a remote `base_url` or project name.

An external repository mode is supported as a secondary use case. In that mode, `.wd` files live outside llmwiki and can be pushed to a configured llmwiki instance through an API or compatibility bridge.

## `.wd` File Format

`.wd` is Markdown with YAML front matter and named content sections. Markdown is used because users and agents can edit it directly, diffs are readable, and the effective content can be passed to llmwiki with minimal transformation.

Example:

```markdown
---
wd_version: 1
id: pricing-policy
title: Product pricing policy
status: active
content_type: markdown
tags:
  - pricing
  - policy

source:
  fetcher: builtin.http
  fetch:
    url: https://example.com/pricing
  transformer: builtin.html_to_markdown
  transform:
    selector: main

sync:
  strategy: review_before_apply
  last_refreshed_at: 2026-06-26T16:00:00+08:00
  source_hash: sha256:...
  snapshot_hash: sha256:...
  effective_hash: sha256:...
  last_ingested_at: null
---

<!-- wd:effective -->
# Product pricing policy

This is the current effective content. It is the default content imported into llmwiki.
<!-- /wd:effective -->

<!-- wd:source_snapshot -->
# Latest source snapshot

This is the latest fetched and transformed candidate content. It is not imported directly.
<!-- /wd:source_snapshot -->

<!-- wd:notes -->
Maintenance notes, review decisions, and source interpretation notes.
<!-- /wd:notes -->
```

Rules:

- `wd:effective` is the only default content imported into llmwiki.
- `wd:source_snapshot` may be overwritten by `wd update`; it is candidate content, not approved knowledge.
- `wd:notes` is for human and agent maintenance context and is never imported by default.
- `id` is the stable identity used for status, cache, review, and upsert. File paths may change; `id` should not change casually.
- Initial `wd add` may write the same converted content to both `effective` and `source_snapshot`, because initial creation establishes the first effective version.
- Subsequent refreshes update only `source_snapshot` until the user or agent applies changes.

## Repository State

WikiDelta stores generated state under `.wikidelta/`. The `.wd` file stores human-auditable source configuration and lifecycle metadata; `.wikidelta/` stores generated artifacts that can be recreated or inspected by tools.

```text
.wikidelta/
  config.yaml
  cache/<wd-id>/
    raw/<hash>.bin
    transformed/<hash>.md
  reviews/<wd-id>.json
  reviews/<wd-id>.patch
  errors/<wd-id>.json
  ingest/<wd-id>.json
```

Cache artifacts should normally be ignored by git. Review, error, and ingest records may be kept or ignored depending on the repository's audit policy.

## CLI Lifecycle

The CLI has product-level commands for daily use and lower-level commands for debugging.

Daily commands:

```bash
wd init
wd add <file-or-url>
wd status
wd update
wd review
wd apply <path> --strategy replace --yes
wd ingest --changed
```

Advanced commands:

```bash
wd fetch <path>
wd transform <path>
wd diff <path>
wd validate <path>
```

`wd add` is the main product entry point. Users should not need to write fetcher and transformer configuration by hand for common cases. The CLI infers the default source pipeline:

```text
*.md        builtin.file + builtin.markdown
*.txt       builtin.file + builtin.text
*.html      builtin.file + builtin.html_to_markdown
*.pdf       builtin.file + builtin.pdf_to_markdown
*.json      builtin.file + builtin.json_to_markdown
http(s)://  builtin.http + builtin.html_to_markdown
```

`wd update` refreshes source snapshots. It fetches and transforms the source, updates `wd:source_snapshot`, updates source and snapshot hashes, and leaves `wd:effective` unchanged.

`wd status` reports state for all `.wd` files by default. Important states include:

```text
clean              source snapshot, effective content, and ingest state are consistent
pending_review     source_snapshot differs from effective
effective_changed  effective changed since last ingest
not_ingested       no ingest record exists
invalid            file format or source configuration is invalid
error              last update/review/ingest failed
```

`wd review` creates structured review artifacts instead of requiring interactive editing. `wd apply --strategy replace --yes` can then accept a snapshot into effective content. Initial versions should not implement automatic semantic merging.

## Agent-Friendly CLI Contract

All primary commands must support:

```text
--json
--no-color
--non-interactive
--workspace <path>
--dry-run
--yes
```

Commands must not open an editor or wait for TTY input by default in non-interactive mode. Agent-facing output should be stable JSON, for example:

```json
{
  "ok": true,
  "workspace": "/repo",
  "items": [
    {
      "path": "raw_sources/pricing-policy.wd",
      "id": "pricing-policy",
      "state": "pending_review",
      "effectiveChanged": false,
      "sourceChanged": true,
      "lastError": null
    }
  ]
}
```

Recommended exit codes:

```text
0 success and no pending work
1 command failure
2 validation failure
3 success with pending_review or effective_changed items
4 partial success
```

## Fetcher And Transformer Protocol

The source pipeline has two steps:

```text
.wd source config -> Fetcher -> RawArtifact -> Transformer -> SnapshotContent -> wd:source_snapshot
```

Built-in fetchers:

```text
builtin.file      read a local file
builtin.http      fetch a URL or HTTP API
builtin.command   execute a configured command and capture stdout
```

Built-in transformers:

```text
builtin.markdown
builtin.text
builtin.html_to_markdown
builtin.pdf_to_markdown
builtin.json_to_markdown
```

`builtin.command` is only used when explicitly configured. `wd add` should not infer command execution from user input.

Custom extension is script-based in the first version. A `.wd` file can reference a local Python script:

```yaml
source:
  fetcher: script.python
  fetch:
    entry: ./fetchers/feishu_doc.py
    args:
      doc_id: abc123
  transformer: script.python
  transform:
    entry: ./transformers/normalize_policy.py
    args:
      format: policy
```

Scripts communicate through JSON on stdin and stdout. Stderr is reserved for logs.

Fetcher input:

```json
{
  "kind": "fetch",
  "wdId": "pricing-policy",
  "workspace": "/repo",
  "config": {
    "doc_id": "abc123"
  }
}
```

Fetcher success output:

```json
{
  "ok": true,
  "contentType": "text/html",
  "content": "<html>...</html>",
  "metadata": {
    "sourceVersion": "v42",
    "fetchedAt": "2026-06-26T16:30:00+08:00"
  }
}
```

Transformer input:

```json
{
  "kind": "transform",
  "wdId": "pricing-policy",
  "contentType": "text/html",
  "content": "<html>...</html>",
  "metadata": {
    "sourceVersion": "v42"
  },
  "config": {
    "format": "policy"
  }
}
```

Transformer success output:

```json
{
  "ok": true,
  "contentType": "text/markdown",
  "content": "# Product pricing policy\n...",
  "metadata": {
    "transformerVersion": "normalize_policy@1"
  }
}
```

Failure output:

```json
{
  "ok": false,
  "error": {
    "code": "AUTH_FAILED",
    "message": "Missing FEISHU_TOKEN",
    "retryable": false
  }
}
```

Scripts must have timeouts. Relative script paths are resolved from the workspace root. Secrets should be referenced through environment variables and must not be written into `.wd`.

## llmwiki Integration

WikiDelta supports two integration modes.

### llmwiki Project Mode

This is the preferred mode. `.wd` files live in the llmwiki project's raw source tree:

```text
llmwiki-project/
  raw_sources/
    pricing/pricing-policy.wd
    policy/refund-policy.wd
```

In this mode, the project context is derived from the directory. No `llmwiki.base_url` or `llmwiki.project` is required. WikiDelta maintains source lifecycle. llmwiki must either:

- natively load `.wd` as a raw source format and import only `wd:effective`, or
- call a local compatibility bridge such as `wd ingest` that extracts `wd:effective` for llmwiki.

The key rule is that llmwiki must never ingest the whole `.wd` file as normal Markdown.

### Remote llmwiki Mode

This is for external WikiDelta repositories:

```yaml
mode: remote_llmwiki
llmwiki:
  base_url: http://127.0.0.1:8000
  project: business-policy
  auth:
    token_env: LLMWIKI_TOKEN
```

`base_url` identifies the llmwiki service, `project` identifies the target knowledge project, and `token_env` names the environment variable containing credentials.

Context detection order:

```text
1. Explicit --mode wins.
2. If the current directory or an ancestor is recognized as an llmwiki project, use llmwiki_project mode.
3. If .wikidelta/config.yaml has mode=remote_llmwiki, use remote_llmwiki mode.
4. Otherwise ask the user to run wd init and choose a mode.
```

## Error Handling And Audit

Failures must be visible, structured, and non-destructive.

If `wd update` fails during fetch or transform, it must not modify `wd:source_snapshot`. It writes an error artifact:

```json
{
  "wdId": "pricing-policy",
  "path": "raw_sources/pricing-policy.wd",
  "stage": "fetch",
  "code": "AUTH_FAILED",
  "message": "Missing FEISHU_TOKEN",
  "retryable": false,
  "occurredAt": "2026-06-26T17:00:00+08:00"
}
```

`wd review` writes both a human-readable patch and a machine-readable JSON file:

```json
{
  "wdId": "pricing-policy",
  "path": "raw_sources/pricing-policy.wd",
  "state": "pending_review",
  "effectiveHash": "sha256:old",
  "snapshotHash": "sha256:new",
  "summary": {
    "addedLines": 12,
    "removedLines": 3
  },
  "actions": [
    {
      "name": "replace_effective",
      "command": "wd apply raw_sources/pricing-policy.wd --strategy replace --yes"
    }
  ]
}
```

## First-Version Scope

In scope:

- `.wd` parser and writer.
- Repository discovery and `.wikidelta/` state directory.
- `wd init`, `wd add`, `wd status`, `wd update`, `wd review`, `wd apply --strategy replace --yes`.
- `wd ingest` or llmwiki loader compatibility bridge.
- Built-in file, HTTP, Markdown, text, HTML, PDF, and JSON handling.
- `script.python` fetcher and transformer protocol.
- Agent-friendly flags, JSON output, and stable exit codes.

Out of scope for the first version:

- Multiple sources per `.wd`.
- Background scheduler or daemon.
- Web UI.
- Automatic semantic merging.
- Complex approval workflows.
- Plugin package marketplace.
- Remote credential management.

## Implementation Recommendation

Implement the CLI in Python first. Python fits llmwiki-style tooling, has mature PDF/HTML/Markdown libraries, and maps naturally to script-based extensions.

Suggested libraries:

- `typer` for CLI commands.
- `pydantic` for config and protocol models.
- `PyYAML` or `ruamel.yaml` for front matter.
- A clear marker-based parser for named Markdown sections.

Avoid fuzzy whole-document regexes for `.wd` parsing. Section markers should be parsed explicitly so writing back a `.wd` file is deterministic.

## Acceptance Tests

The first implementation should pass these user-path tests:

1. `wd add ./a.md` creates a `.wd` file whose `effective` and `source_snapshot` sections initially match.
2. After modifying `a.md`, `wd update` updates only `source_snapshot` and leaves `effective` unchanged.
3. `wd status --json` reports `pending_review` when snapshot and effective differ.
4. `wd review --json` creates `.wikidelta/reviews/<wd-id>.json` and `.patch`.
5. `wd apply <path> --strategy replace --yes` replaces `effective` with `source_snapshot`.
6. llmwiki project mode or the compatibility bridge imports only `wd:effective` and excludes source configuration, source snapshot, and notes.
7. A failing `script.python` fetcher writes `.wikidelta/errors/<wd-id>.json` and returns a stable failure status.
8. Primary commands work with `--json --non-interactive --workspace <path>` and never block waiting for editor input.
