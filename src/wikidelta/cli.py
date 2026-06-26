from __future__ import annotations

import json
from pathlib import Path

import typer

from wikidelta.repository import Repository
from wikidelta.service import add_source, apply_review, status_items, update_document, write_review


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


@app.command()
def update(
    path: Path = typer.Argument(..., help=".wd file to update."),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    emit(update_document(path, workspace=workspace), as_json=json_output)


@app.command()
def status(
    workspace: Path = typer.Option(Path.cwd(), "--workspace", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    items = status_items(workspace=workspace)
    payload = {"ok": True, "workspace": str(workspace), "items": items}
    emit(payload, as_json=json_output)
    if any(item.get("state") in {"pending_review", "effective_changed"} for item in items):
        raise typer.Exit(3)


@app.command()
def review(
    path: Path = typer.Argument(..., help=".wd file to review."),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", help="Workspace root."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    emit({"ok": True, "review": write_review(path, workspace=workspace)}, as_json=json_output)


@app.command("apply")
def apply_cmd(
    path: Path = typer.Argument(..., help=".wd file to apply."),
    workspace: Path = typer.Option(Path.cwd(), "--workspace", help="Workspace root."),
    strategy: str = typer.Option("replace", "--strategy", help="Apply strategy."),
    yes: bool = typer.Option(False, "--yes", help="Confirm lifecycle mutation."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    emit(apply_review(path, workspace=workspace, strategy=strategy, yes=yes), as_json=json_output)


if __name__ == "__main__":
    app()
