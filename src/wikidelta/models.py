from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    fetcher: str
    fetch: dict[str, Any] = Field(default_factory=dict)
    transformer: str
    transform: dict[str, Any] = Field(default_factory=dict)


class SyncState(BaseModel):
    state: str = "up_to_date"
    strategy: str = "review_before_apply"
    last_refreshed_at: str | None = None
    source_hash: str | None = None
    snapshot_hash: str | None = None
    effective_hash: str | None = None
    last_ingested_at: str | None = None


class WdMeta(BaseModel):
    wd_version: int = 1
    id: str
    title: str
    status: str = "active"
    content_type: str = "markdown"
    tags: list[str] = Field(default_factory=list)
    source: SourceConfig
    sync: SyncState = Field(default_factory=SyncState)
