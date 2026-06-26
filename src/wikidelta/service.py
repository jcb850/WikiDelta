from __future__ import annotations

import re
from pathlib import Path

from wikidelta.document import render_wd
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
    output_dir = into if into is not None else repo.root
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
