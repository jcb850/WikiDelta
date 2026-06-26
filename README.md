# WikiDelta

WikiDelta manages `.wd` files for llmwiki knowledge sources. A `.wd` file packages one knowledge unit with one source, one current effective content block, and one latest source snapshot for review.

The first version focuses on this rule:

```text
1 .wd file = 1 knowledge unit = 1 source = 1 effective content block
```

## `.wd` Shape

`.wd` files are Markdown files with YAML front matter and named sections:

```markdown
---
wd_version: 1
id: pricing-policy
title: Pricing Policy
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
# Pricing Policy
Approved content imported into llmwiki.
<!-- /wd:effective -->

<!-- wd:source_snapshot -->
# Pricing Policy
Latest fetched candidate content.
<!-- /wd:source_snapshot -->

<!-- wd:notes -->
Maintenance notes.
<!-- /wd:notes -->
```

Only `wd:effective` is extracted for llmwiki ingest. Source configuration, snapshots, and notes are maintenance data.

## Common Commands

```bash
wd init --mode llmwiki_project
wd add ./policy.md --into raw_sources/policy
wd update raw_sources/policy/policy.wd
wd status --json
wd review raw_sources/policy/policy.wd --json
wd apply raw_sources/policy/policy.wd --strategy replace --yes
wd ingest raw_sources/policy/policy.wd --json
```

`wd add` infers common source pipelines:

```text
*.md        builtin.file + builtin.markdown
*.txt       builtin.file + builtin.text
*.html      builtin.file + builtin.html_to_markdown
*.json      builtin.file + builtin.json_to_markdown
*.pdf       builtin.file + builtin.pdf_to_markdown
http(s)://  builtin.http + builtin.html_to_markdown
```

## Agent-Friendly Operation

Primary commands support JSON output and explicit workspace selection:

```bash
wd status --workspace /path/to/repo --json
```

Lifecycle mutations that affect effective content require explicit confirmation:

```bash
wd apply path/to/file.wd --strategy replace --yes
```

`wd status` exits with code `3` when it succeeds but finds pending review work.

## llmwiki Project Mode

The preferred layout is to place `.wd` files in an llmwiki raw source tree:

```text
llmwiki-project/
  raw_sources/
    pricing/pricing-policy.wd
```

In this mode, WikiDelta maintains the lifecycle file and `wd ingest` acts as a local compatibility bridge that extracts only `wd:effective`.

## Script Extensions

Custom fetchers can use `script.python`. The script reads JSON from stdin and writes JSON to stdout:

```json
{
  "ok": true,
  "contentType": "text/plain",
  "content": "Fetched content",
  "metadata": {}
}
```

Failures should return:

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
