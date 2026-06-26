from __future__ import annotations

import re
import json
import difflib
from pathlib import Path

from wikidelta.document import WdDocument, content_hash, render_wd
from wikidelta.repository import Repository
from wikidelta.sources import fetch_source, infer_source_config, transform_content


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "document"


def add_source(target: str, *, workspace: Path, into: Path | None = None, title: str | None = None) -> Path:
    repo = Repository(workspace)
    repo.ensure_layout()
    source_config = infer_source_config(target)
    raw = fetch_source(source_config["fetcher"], source_config["fetch"], workspace=repo.root, wd_id="new")
    transformed = transform_content(source_config["transformer"], source_config.get("transform", {}), raw)

    parsed_target = Path(target)
    stem = parsed_target.stem if parsed_target.suffix else slugify(target.rstrip("/"))
    wd_id = slugify(stem)
    output_dir = into if into is not None else repo.root / "raw_source"
    if not output_dir.is_absolute():
        output_dir = repo.root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    wd_path = output_dir / f"{wd_id}.wd"
    wd_path.write_text(
        render_wd(
            wd_id=wd_id,
            title=title or stem.replace("-", " ").replace("_", " ").title(),
            source=source_config,
            content=transformed.content,
        ),
        encoding="utf-8",
    )
    return wd_path


def update_document(path: Path, *, workspace: Path) -> dict:
    repo = Repository(workspace)
    doc = WdDocument.parse(path.read_text(encoding="utf-8"))
    source = doc.meta.source
    raw = fetch_source(source.fetcher, source.fetch, workspace=repo.root, wd_id=doc.meta.id)
    transformed = transform_content(source.transformer, source.transform, raw)
    snapshot = transformed.content.strip("\n")
    effective = doc.section("effective", default="").strip("\n")
    doc.meta.sync.source_hash = content_hash(raw.content)
    doc.meta.sync.effective_hash = content_hash(effective)
    if snapshot == effective:
        doc.remove_section("source_snapshot")
        doc.meta.sync.state = "up_to_date"
        doc.meta.sync.snapshot_hash = None
    else:
        doc.set_section("source_snapshot", snapshot)
        doc.meta.sync.state = "pending_review"
        doc.meta.sync.snapshot_hash = content_hash(snapshot)
    path.write_text(doc.to_text(), encoding="utf-8")
    return {"ok": True, "path": str(path), "id": doc.meta.id, "snapshotHash": doc.meta.sync.snapshot_hash}


def status_items(*, workspace: Path) -> list[dict]:
    repo = Repository(workspace)
    items: list[dict] = []
    for path in repo.iter_wd_files():
        try:
            doc = WdDocument.parse(path.read_text(encoding="utf-8"))
            effective_hash = content_hash(doc.section("effective", default="").strip("\n"))
            snapshot = doc.section("source_snapshot", default=None)
            snapshot_hash = content_hash(snapshot.strip("\n")) if snapshot is not None else None
            state = "pending_review" if snapshot_hash is not None and effective_hash != snapshot_hash else "clean"
            items.append(
                {
                    "path": str(path.relative_to(repo.root)),
                    "id": doc.meta.id,
                    "state": state,
                    "effectiveChanged": effective_hash != doc.meta.sync.effective_hash,
                    "sourceChanged": snapshot_hash is not None and effective_hash != snapshot_hash,
                    "lastError": None,
                }
            )
        except Exception as exc:  # noqa: BLE001 - status must report invalid files.
            items.append({"path": str(path.relative_to(repo.root)), "id": None, "state": "invalid", "lastError": str(exc)})
    return items


def write_review(path: Path, *, workspace: Path) -> dict:
    repo = Repository(workspace)
    repo.ensure_layout()
    doc = WdDocument.parse(path.read_text(encoding="utf-8"))
    effective = doc.section("effective", default="").strip("\n")
    maybe_snapshot = doc.section("source_snapshot", default=None)
    if maybe_snapshot is None:
        return {
            "wdId": doc.meta.id,
            "path": str(path.relative_to(repo.root) if path.is_relative_to(repo.root) else path),
            "state": "clean",
            "effectiveHash": content_hash(effective),
            "snapshotHash": None,
            "summary": {"addedLines": 0, "removedLines": 0},
            "actions": [{"name": "update", "command": f"wd update {path}"}],
        }
    snapshot = maybe_snapshot.strip("\n")
    patch = "".join(
        difflib.unified_diff(
            effective.splitlines(keepends=True),
            snapshot.splitlines(keepends=True),
            fromfile="effective",
            tofile="source_snapshot",
        )
    )
    review = {
        "wdId": doc.meta.id,
        "path": str(path.relative_to(repo.root) if path.is_relative_to(repo.root) else path),
        "state": "pending_review" if effective != snapshot else "clean",
        "effectiveHash": content_hash(effective),
        "snapshotHash": content_hash(snapshot),
        "summary": {
            "addedLines": sum(1 for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")),
            "removedLines": sum(1 for line in patch.splitlines() if line.startswith("-") and not line.startswith("---")),
        },
        "actions": [{"name": "replace_effective", "command": f"wd apply {path} --strategy replace --yes"}],
    }
    (repo.state_dir / "reviews" / f"{doc.meta.id}.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    (repo.state_dir / "reviews" / f"{doc.meta.id}.patch").write_text(patch, encoding="utf-8")
    return review


def apply_review(path: Path, *, workspace: Path, strategy: str, yes: bool) -> dict:
    if strategy != "replace":
        raise ValueError("Only replace strategy is supported")
    if not yes:
        raise ValueError("--yes is required to apply changes")
    doc = WdDocument.parse(path.read_text(encoding="utf-8"))
    maybe_snapshot = doc.section("source_snapshot", default=None)
    if maybe_snapshot is None:
        raise ValueError("No source_snapshot to apply")
    snapshot = maybe_snapshot.strip("\n")
    doc.set_section("effective", snapshot)
    doc.remove_section("source_snapshot")
    doc.meta.sync.state = "up_to_date"
    doc.meta.sync.effective_hash = content_hash(snapshot)
    doc.meta.sync.snapshot_hash = None
    path.write_text(doc.to_text(), encoding="utf-8")
    return {"ok": True, "path": str(path), "id": doc.meta.id, "strategy": strategy}


def extract_effective(path: Path, *, workspace: Path) -> dict:
    repo = Repository(workspace)
    doc = WdDocument.parse(path.read_text(encoding="utf-8"))
    relative_path = str(path.relative_to(repo.root) if path.is_relative_to(repo.root) else path)
    return {
        "ok": True,
        "items": [
            {
                "external_id": f"wd:{doc.meta.id}",
                "id": doc.meta.id,
                "title": doc.meta.title,
                "path": relative_path,
                "content_type": doc.meta.content_type,
                "tags": doc.meta.tags,
                "effective_hash": content_hash(doc.section("effective", default="").strip("\n")),
                "content": doc.section("effective", default="").strip("\n"),
            }
        ],
    }
