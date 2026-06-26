from __future__ import annotations

import json
from pathlib import Path

import typer

from wikidelta.repository import Repository
from wikidelta.service import add_source


app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Manage WikiDelta .wd lifecycle files."""


def emit(payload: dict, *, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload.get("message", json.dumps(payload, ensure_ascii=False)))


@app.command()
def init(
    workspace: Path = typer.Option(Path.cwd(), "--workspace", help="Workspace root."),
    mode: str = typer.Option("llmwiki_project", "--mode", help="Repository mode."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    repo = Repository(workspace)
    repo.ensure_layout(mode=mode)
    emit(
        {
            "ok": True,
            "workspace": str(repo.root),
            "mode": mode,
            "config": str(repo.config_path),
            "message": f"Initialized WikiDelta workspace at {repo.root}",
        },
        as_json=json_output,
    )


@app.command()
def add(
    target: str = typer.Argument(..., help="Local file path or URL to wrap as a .wd source."),
    into: Path | None = typer.Option(None, "--into", help="Directory where the .wd file is written."),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", help="Workspace root."),
    title: str | None = typer.Option(None, "--title", help="Knowledge title."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    wd_path = add_source(target, workspace=workspace, into=into, title=title)
    emit(
        {
            "ok": True,
            "path": str(wd_path),
            "message": f"Created {wd_path}",
        },
        as_json=json_output,
    )


if __name__ == "__main__":
    app()
