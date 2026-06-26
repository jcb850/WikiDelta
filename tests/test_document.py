from wikidelta.document import WdDocument, content_hash, render_wd


SAMPLE = """---
wd_version: 1
id: pricing-policy
title: Pricing Policy
status: active
content_type: markdown
tags:
  - pricing
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
# Effective

Approved text.
<!-- /wd:effective -->

<!-- wd:source_snapshot -->
# Snapshot

Candidate text.
<!-- /wd:source_snapshot -->

<!-- wd:notes -->
Keep this note.
<!-- /wd:notes -->
"""


def test_parse_front_matter_and_sections():
    doc = WdDocument.parse(SAMPLE)

    assert doc.meta.id == "pricing-policy"
    assert doc.meta.source.fetcher == "builtin.file"
    assert doc.section("effective").strip() == "# Effective\n\nApproved text."
    assert doc.section("source_snapshot").strip() == "# Snapshot\n\nCandidate text."
    assert doc.section("notes").strip() == "Keep this note."


def test_write_updates_only_named_section_and_preserves_notes():
    doc = WdDocument.parse(SAMPLE)
    doc.set_section("source_snapshot", "# Snapshot\n\nNew candidate.")

    written = doc.to_text()
    reparsed = WdDocument.parse(written)

    assert reparsed.section("effective").strip() == "# Effective\n\nApproved text."
    assert reparsed.section("source_snapshot").strip() == "# Snapshot\n\nNew candidate."
    assert reparsed.section("notes").strip() == "Keep this note."


def test_render_wd_initializes_effective_without_snapshot():
    text = render_wd(
        wd_id="a-doc",
        title="A Doc",
        source={
            "fetcher": "builtin.file",
            "fetch": {"path": "./a.md"},
            "transformer": "builtin.markdown",
            "transform": {},
        },
        content="# A\n\nBody",
    )

    doc = WdDocument.parse(text)

    assert doc.meta.id == "a-doc"
    assert doc.section("effective").strip() == "# A\n\nBody"
    assert doc.section("source_snapshot", default=None) is None
    assert doc.meta.sync.effective_hash == content_hash("# A\n\nBody")
    assert doc.meta.sync.snapshot_hash is None


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
        source={
            "fetcher": "builtin.file",
            "fetch": {"path": "./a.md"},
            "transformer": "builtin.markdown",
            "transform": {},
        },
        content="# A",
    )

    assert "wd:effective" in text
    assert "wd:source_snapshot" not in text
    doc = WdDocument.parse(text)
    assert doc.meta.sync.state == "up_to_date"
    assert doc.meta.sync.snapshot_hash is None


def test_content_hash_is_stable_sha256():
    assert content_hash("hello") == "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
