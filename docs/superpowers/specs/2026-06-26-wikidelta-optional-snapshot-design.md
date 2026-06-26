# WikiDelta Optional Snapshot Design

Date: 2026-06-26
Status: Approved design update

## Purpose

This document updates the original WikiDelta lifecycle design. The original design required every `.wd` file to store both `wd:effective` and `wd:source_snapshot`, even when both sections contained identical content. That duplicates large knowledge content in the common clean state.

The updated design keeps `wd:effective` as the stable llmwiki ingest interface and makes `wd:source_snapshot` optional. A `.wd` file only stores a snapshot when there is candidate source content waiting for review.

## Core Rule

```text
wd:effective       required
wd:source_snapshot optional, present only when sync.state = pending_review
```

`wd:effective` remains the only default content imported into llmwiki. `wd:source_snapshot` remains review-only candidate content and is never imported directly.

## File States

### Up To Date

When source content and effective content are aligned, the file stores a single body section:

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
  state: up_to_date
  source_hash: sha256:abc
  effective_hash: sha256:abc
  snapshot_hash: null
---

<!-- wd:effective -->
# Pricing Policy

Approved content.
<!-- /wd:effective -->

<!-- wd:notes -->
Maintenance notes.
<!-- /wd:notes -->
```

There is no `wd:source_snapshot` section because there is no candidate content to review.

### Pending Review

When refreshed source content differs from effective content, the file stores the candidate snapshot:

```markdown
---
sync:
  state: pending_review
  source_hash: sha256:new
  effective_hash: sha256:old
  snapshot_hash: sha256:new
---

<!-- wd:effective -->
# Pricing Policy

Approved content.
<!-- /wd:effective -->

<!-- wd:source_snapshot -->
# Pricing Policy

Candidate refreshed content.
<!-- /wd:source_snapshot -->

<!-- wd:notes -->
Maintenance notes.
<!-- /wd:notes -->
```

`pending_review` is the only normal state where both content sections are present.

## Command Behavior

### `wd add`

`wd add` fetches and transforms the source, then writes only `wd:effective`.

```text
sync.state = up_to_date
effective_hash = hash(effective)
source_hash = hash(fetched source or transformed content, depending on implementation)
snapshot_hash = null
```

It must not create a `wd:source_snapshot` section during initial creation.

### `wd update`

`wd update` fetches and transforms the source and compares the transformed content with `wd:effective`.

If the transformed content matches `wd:effective`:

```text
remove wd:source_snapshot if present
sync.state = up_to_date
snapshot_hash = null
effective_hash = hash(effective)
```

If the transformed content differs from `wd:effective`:

```text
write wd:source_snapshot
sync.state = pending_review
snapshot_hash = hash(source_snapshot)
effective_hash = hash(effective)
```

`wd update` must not overwrite `wd:effective`.

### `wd status`

Status is derived from sections and hashes:

```text
no source_snapshot                      -> clean / up_to_date
source_snapshot differs from effective  -> pending_review
source_snapshot equals effective        -> clean, eligible for cleanup on next write
invalid required sections or metadata   -> invalid
```

The implementation may normalize stale files by removing a redundant `source_snapshot` when it writes the file for another lifecycle operation.

### `wd review`

`wd review` is review-only and must not fetch or transform sources.

If `wd:source_snapshot` is absent:

```text
return clean
do not generate patch
include a machine-readable next action suggesting wd update
```

If `wd:source_snapshot` is present:

```text
generate .wikidelta/reviews/<id>.json
generate .wikidelta/reviews/<id>.patch
```

### `wd apply --strategy replace --yes`

`wd apply` requires `wd:source_snapshot` to exist.

When applying:

```text
effective = source_snapshot
remove wd:source_snapshot
sync.state = up_to_date
effective_hash = hash(effective)
snapshot_hash = null
```

If `wd:source_snapshot` is absent, `wd apply` should fail with a clear message such as `No source_snapshot to apply`.

### `wd ingest`

No behavior change. `wd ingest` reads only `wd:effective`.

## Backward Compatibility

Existing `.wd` files remain readable.

If an existing `.wd` has `wd:source_snapshot` equal to `wd:effective`:

```text
status = clean
sync.state = up_to_date
the redundant source_snapshot may be removed on the next write
```

If an existing `.wd` has `wd:source_snapshot` different from `wd:effective`:

```text
status = pending_review
sync.state = pending_review
```

Parsers must require `wd:effective` but must not require `wd:source_snapshot`.

## Test Requirements

The implementation should cover:

1. `wd add` creates a `.wd` without `wd:source_snapshot`.
2. `wd update` does not create `wd:source_snapshot` when refreshed content equals `wd:effective`.
3. `wd update` creates `wd:source_snapshot` and `pending_review` when refreshed content differs.
4. `wd review` without `wd:source_snapshot` returns clean and suggests `wd update`.
5. `wd apply` removes `wd:source_snapshot` after accepting it.
6. Existing duplicated clean files remain readable and are treated as clean.
7. `wd ingest` continues to output only `wd:effective`.
