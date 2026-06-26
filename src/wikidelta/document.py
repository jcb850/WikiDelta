from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import yaml

from wikidelta.models import WdMeta


FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
SECTION_RE = re.compile(r"<!-- wd:([a-z_]+) -->\n?(.*?)\n?<!-- /wd:\1 -->", re.DOTALL)


class WdParseError(ValueError):
    pass


def content_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class WdDocument:
    meta: WdMeta
    sections: dict[str, str]

    @classmethod
    def parse(cls, text: str) -> "WdDocument":
        match = FRONT_MATTER_RE.match(text)
        if not match:
            raise WdParseError("Missing YAML front matter")

        raw_meta = yaml.safe_load(match.group(1)) or {}
        meta = WdMeta.model_validate(raw_meta)
        body = text[match.end() :]
        sections = {name: content.strip("\n") for name, content in SECTION_RE.findall(body)}

        if "effective" not in sections:
            raise WdParseError("Missing wd:effective section")

        return cls(meta=meta, sections=sections)

    def section(self, name: str, default: str | None = None) -> str | None:
        return self.sections.get(name, default)

    def set_section(self, name: str, content: str) -> None:
        self.sections[name] = content.strip("\n")

    def remove_section(self, name: str) -> None:
        self.sections.pop(name, None)

    def to_text(self) -> str:
        meta_dict = self.meta.model_dump(mode="json", exclude_none=True)
        front_matter = yaml.safe_dump(meta_dict, sort_keys=False, allow_unicode=True).strip()
        section_names = ["effective"]
        if "source_snapshot" in self.sections:
            section_names.append("source_snapshot")
        if "notes" in self.sections:
            section_names.append("notes")
        section_names.extend(name for name in self.sections if name not in section_names)

        body_parts = []
        for name in section_names:
            body_parts.append(f"<!-- wd:{name} -->\n{self.sections[name].strip()}\n<!-- /wd:{name} -->")
        return f"---\n{front_matter}\n---\n\n" + "\n\n".join(body_parts) + "\n"


def render_wd(*, wd_id: str, title: str, source: dict[str, Any], content: str) -> str:
    body = content.strip("\n")
    hash_value = content_hash(body)
    meta = WdMeta.model_validate(
        {
            "wd_version": 1,
            "id": wd_id,
            "title": title,
            "status": "active",
            "content_type": "markdown",
            "tags": [],
            "source": source,
            "sync": {
                "strategy": "review_before_apply",
                "state": "up_to_date",
                "source_hash": hash_value,
                "snapshot_hash": None,
                "effective_hash": hash_value,
                "last_ingested_at": None,
            },
        }
    )
    doc = WdDocument(
        meta=meta,
        sections={
            "effective": body,
            "notes": "",
        },
    )
    return doc.to_text()
