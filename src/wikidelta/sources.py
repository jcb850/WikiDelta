from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class Artifact:
    content: str
    content_type: str
    metadata: dict = field(default_factory=dict)


def infer_source_config(target: str) -> dict:
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https"}:
        return {
            "fetcher": "builtin.http",
            "fetch": {"url": target},
            "transformer": "builtin.html_to_markdown",
            "transform": {},
        }

    suffix = Path(target).suffix.lower()
    transformer = {
        ".md": "builtin.markdown",
        ".markdown": "builtin.markdown",
        ".txt": "builtin.text",
        ".html": "builtin.html_to_markdown",
        ".htm": "builtin.html_to_markdown",
        ".json": "builtin.json_to_markdown",
        ".pdf": "builtin.pdf_to_markdown",
    }.get(suffix, "builtin.text")
    return {
        "fetcher": "builtin.file",
        "fetch": {"path": target},
        "transformer": transformer,
        "transform": {},
    }


def fetch_source(fetcher: str, config: dict, *, workspace: Path, wd_id: str) -> Artifact:
    if fetcher == "builtin.file":
        path = Path(config["path"])
        if not path.is_absolute():
            path = workspace / path
        content = path.read_text(encoding="utf-8")
        return Artifact(content=content, content_type=_content_type_for_path(path), metadata={"path": str(path)})

    if fetcher == "builtin.http":
        response = requests.get(config["url"], timeout=float(config.get("timeout", 20)))
        response.raise_for_status()
        return Artifact(
            content=response.text,
            content_type=response.headers.get("content-type", "text/html").split(";")[0],
            metadata={"url": config["url"]},
        )

    if fetcher == "script.python":
        payload = {
            "kind": "fetch",
            "wdId": wd_id,
            "workspace": str(workspace),
            "config": config.get("args", {}),
        }
        result = _run_python_script(config, payload, workspace=workspace)
        return Artifact(
            content=result["content"],
            content_type=result.get("contentType", "text/plain"),
            metadata=result.get("metadata", {}),
        )

    raise ValueError(f"Unsupported fetcher: {fetcher}")


def transform_content(transformer: str, config: dict, raw: Artifact) -> Artifact:
    if transformer == "builtin.markdown":
        return Artifact(content=raw.content.strip(), content_type="text/markdown", metadata=raw.metadata)
    if transformer == "builtin.text":
        return Artifact(content=raw.content.strip(), content_type="text/markdown", metadata=raw.metadata)
    if transformer == "builtin.html_to_markdown":
        html = raw.content
        selector = config.get("selector")
        if selector:
            soup = BeautifulSoup(html, "html.parser")
            selected = soup.select_one(selector)
            html = str(selected) if selected else ""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return Artifact(content=soup.get_text("\n", strip=True), content_type="text/markdown", metadata=raw.metadata)
    if transformer == "builtin.json_to_markdown":
        parsed = json.loads(raw.content)
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
        return Artifact(content=f"```json\n{pretty}\n```", content_type="text/markdown", metadata=raw.metadata)
    if transformer == "builtin.pdf_to_markdown":
        return Artifact(content=raw.content.strip(), content_type="text/markdown", metadata=raw.metadata)
    if transformer == "script.python":
        payload = {
            "kind": "transform",
            "wdId": config.get("wd_id", ""),
            "workspace": config.get("workspace", ""),
            "contentType": raw.content_type,
            "content": raw.content,
            "metadata": raw.metadata,
            "config": config.get("args", {}),
        }
        workspace = Path(config.get("workspace") or ".").resolve()
        result = _run_python_script(config, payload, workspace=workspace)
        return Artifact(
            content=result["content"],
            content_type=result.get("contentType", "text/markdown"),
            metadata=result.get("metadata", {}),
        )
    raise ValueError(f"Unsupported transformer: {transformer}")


def _run_python_script(config: dict, payload: dict, *, workspace: Path) -> dict:
    entry = Path(config["entry"])
    if not entry.is_absolute():
        entry = workspace / entry
    completed = subprocess.run(
        [sys.executable, str(entry)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=float(config.get("timeout", 30)),
        cwd=str(workspace),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"script exited with {completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("script did not return JSON") from exc
    if not result.get("ok"):
        error = result.get("error", {})
        raise RuntimeError(f"{error.get('code', 'SCRIPT_FAILED')}: {error.get('message', 'script failed')}")
    return result


def _content_type_for_path(path: Path) -> str:
    return {
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".txt": "text/plain",
        ".html": "text/html",
        ".htm": "text/html",
        ".json": "application/json",
        ".pdf": "application/pdf",
    }.get(path.suffix.lower(), "text/plain")
