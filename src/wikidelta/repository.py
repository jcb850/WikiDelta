from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


STATE_DIRS = ("cache", "reviews", "errors", "ingest")


def find_workspace(start: Path | str) -> Path | None:
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".wikidelta").is_dir():
            return candidate
    return None


@dataclass(frozen=True)
class Repository:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).resolve())

    @property
    def state_dir(self) -> Path:
        return self.root / ".wikidelta"

    @property
    def config_path(self) -> Path:
        return self.state_dir / "config.yaml"

    def ensure_layout(self, *, mode: str = "llmwiki_project") -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        for dirname in STATE_DIRS:
            (self.state_dir / dirname).mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            self.config_path.write_text(yaml.safe_dump({"mode": mode}, sort_keys=False), encoding="utf-8")

    def iter_wd_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.root.rglob("*.wd"):
            if ".wikidelta" in path.relative_to(self.root).parts:
                continue
            files.append(path)
        return sorted(files)
