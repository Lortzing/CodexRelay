from __future__ import annotations

import sys
from typing import Annotated

import typer
from typer._completion_classes import completion_init

from . import cli as base_cli
from .completion import ensure_completion
from .lifecycle import cleanup_relay, uninstall_and_exit, update_and_exit

app = base_cli.app
console = base_cli.console

# Remove commands that existed solely for historical compatibility or whose
# lifecycle behavior is replaced by this module.
app.registered_commands[:] = [
    command
    for command in app.registered_commands
    if command.name not in {"list", "uninstall"}
]


@app.command("update")
def update(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Update CoderRelay from the GitHub main branch without changing profile data."""
    if not yes and not typer.confirm("Update CoderRelay from GitHub main?", default=True):
        console.print("Update cancelled.")
        raise typer.Exit(0)
    console.print("Updating the installed package; profile data will be preserved...")
    console.file.flush()
    update_and_exit()


@app.command("uninstall")
def uninstall(
    ctx: typer.Context,
    purge: Annotated[
        bool,
        typer.Option(
            "--purge",
            help="Delete profiles, backups, state, and cached metadata during uninstall.",
        ),
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Uninstall CoderRelay and choose whether managed profile data is preserved."""
    manager = base_cli._manager(ctx)
    should_purge = purge

    if purge:
        if not yes and not typer.confirm(
            "Permanently delete all CoderRelay profiles, backups, and state?",
            default=False,
        ):
            console.print("Uninstall cancelled.")
            raise typer.Exit(0)
    elif not yes:
        keep_data = typer.confirm(
            "Preserve CoderRelay profile data, backups, and state?",
            default=True,
        )
        should_purge = not keep_data
        if should_purge and not typer.confirm(
            "Profile data will be permanently deleted. Continue?",
            default=False,
        ):
            console.print("Uninstall cancelled.")
            raise typer.Exit(0)

    result = cleanup_relay(app_home=manager.paths.app_home, purge=should_purge)
    console.print(f"Removed {result.completion_files_removed} completion artifact(s).")
    if result.data_removed:
        console.print("Managed profiles, backups, and state were deleted.")
    else:
        console.print(f"Managed profile data was preserved at {manager.paths.app_home}.")
    console.print("The active ~/.codex/auth.json and config.toml were not removed.")
    console.print("Removing the installed package...")
    console.file.flush()
    uninstall_and_exit()


def main() -> None:
    """Run the public CoderRelay CLI."""
    completion_init()
    if "uninstall" not in sys.argv[1:]:
        ensure_completion(app)
    app()
