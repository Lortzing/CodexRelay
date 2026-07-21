from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Annotated, Any

import typer
from typer._completion_classes import completion_init
from rich.console import Console
from rich.live import Live
from rich.table import Table

from .completion import ensure_completion
from .errors import RelayError
from .manager import RelayManager
from .models import ProbeResult, Profile
from .storage import (
    Paths,
    default_app_home,
    default_codex_home,
    migrate_legacy_app_home,
)

app = typer.Typer(
    name="coder-relay",
    help="Manage Codex ChatGPT and API-key profiles with health checks and automatic failover.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


class AppContext:
    def __init__(
        self,
        manager: RelayManager,
        *,
        bootstrap_profile: Profile | None = None,
        bootstrap_error: str | None = None,
    ):
        self.manager = manager
        self.bootstrap_profile = bootstrap_profile
        self.bootstrap_error = bootstrap_error


@app.callback()
def callback(
    ctx: typer.Context,
    home: Annotated[
        Path | None,
        typer.Option("--home", help="CoderRelay data directory."),
    ] = None,
    codex_home: Annotated[
        Path | None,
        typer.Option("--codex-home", help="Codex configuration directory."),
    ] = None,
) -> None:
    app_home = (home or default_app_home()).expanduser()
    if home is None:
        migrate_legacy_app_home(app_home)
    paths = Paths(
        app_home,
        (codex_home or default_codex_home()).expanduser(),
    )
    manager = RelayManager(paths)
    bootstrap_profile: Profile | None = None
    bootstrap_error: str | None = None
    completion_request = bool(
        os.environ.get("_CDY_COMPLETE")
        or os.environ.get("_CODER_RELAY_COMPLETE")
    )
    if (
        not ctx.resilient_parsing
        and not completion_request
        and ctx.invoked_subcommand not in {None, "import-current", "uninstall"}
    ):
        try:
            bootstrap_profile = manager.bootstrap_current_profile()
        except (RelayError, OSError) as exc:
            # First-run import is best-effort. An invalid or missing current
            # Codex configuration must not block commands that can repair it.
            bootstrap_error = str(exc)
    ctx.obj = AppContext(
        manager,
        bootstrap_profile=bootstrap_profile,
        bootstrap_error=bootstrap_error,
    )


def _manager(ctx: typer.Context) -> RelayManager:
    return ctx.obj.manager


def _fail(exc: Exception) -> None:
    console.print(f"[bold red]Error:[/bold red] {exc}")
    raise typer.Exit(1)


@app.command("import-current")
def import_current(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Argument(help="Profile name. Omit it to infer a name from the current account/provider."),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Replace an existing named profile.")] = False,
    health_mode: Annotated[
        str | None,
        typer.Option("--health-mode", help="API probe mode override: responses or models."),
    ] = None,
    balance_url: Annotated[str | None, typer.Option("--balance-url")] = None,
    balance_path: Annotated[str | None, typer.Option("--balance-path")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
) -> None:
    """Detect and import the active CODEX_HOME auth.json and config.toml."""
    try:
        profile = _manager(ctx).import_current_profile(
            name,
            force=force,
            health_mode=health_mode,
            balance_url=balance_url,
            balance_path=balance_path,
            notes=notes,
        )
    except (RelayError, OSError) as exc:
        _fail(exc)
    if profile.kind == "chatgpt":
        detail = profile.account_email or "ChatGPT account"
    else:
        detail = f"{profile.provider_id} · {profile.base_url} · {profile.model or 'default model'}"
    console.print(
        f"Imported current Codex configuration as [bold green]{profile.name}[/bold green] "
        f"([cyan]{profile.kind}[/cyan], {detail})."
    )
    console.print("The imported profile is registered as the active managed profile.")


@app.command("add-auth")
def add_auth(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name.")],
    auth_json: Annotated[Path, typer.Argument(help="Path to a ChatGPT auth.json file.")],
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Base config.toml. Defaults to the active Codex config."),
    ] = None,
    model: Annotated[str | None, typer.Option("--model", help="Optional model override.")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
    force: Annotated[bool, typer.Option("--force", help="Replace an existing profile.")] = False,
) -> None:
    """Import a ChatGPT login from auth.json."""
    try:
        profile = _manager(ctx).add_auth_profile(
            name,
            auth_json.expanduser(),
            config=config.expanduser() if config else None,
            model=model,
            notes=notes,
            force=force,
        )
    except (RelayError, OSError) as exc:
        _fail(exc)
    console.print(f"Added ChatGPT profile [bold]{profile.name}[/bold].")


@app.command("add-api")
def add_api(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name.")],
    url: Annotated[str, typer.Option("--url", help="OpenAI-compatible API base URL.")],
    model: Annotated[str, typer.Option("--model", help="Model name used by Codex and health checks.")],
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="API key. Prefer --api-key-stdin to avoid shell history."),
    ] = None,
    api_key_stdin: Annotated[
        bool,
        typer.Option("--api-key-stdin", help="Read the API key from standard input."),
    ] = False,
    config: Annotated[Path | None, typer.Option("--config", help="Base config.toml.")] = None,
    provider_id: Annotated[str | None, typer.Option("--provider-id")] = None,
    health_mode: Annotated[
        str,
        typer.Option("--health-mode", help="responses, models, or custom."),
    ] = "responses",
    health_endpoint: Annotated[str | None, typer.Option("--health-endpoint")] = None,
    health_method: Annotated[str, typer.Option("--health-method")] = "GET",
    expected_text: Annotated[str | None, typer.Option("--expected-text")] = None,
    timeout: Annotated[float, typer.Option("--timeout", min=1.0)] = 15.0,
    balance_url: Annotated[str | None, typer.Option("--balance-url")] = None,
    balance_path: Annotated[
        str | None,
        typer.Option("--balance-path", help="Dotted JSON path, for example data.balance."),
    ] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Create an API-key + URL Codex profile."""
    if api_key and api_key_stdin:
        _fail(RelayError("Use either --api-key or --api-key-stdin, not both."))
    if api_key_stdin:
        resolved_key = sys.stdin.read().strip()
    elif api_key:
        resolved_key = api_key
    else:
        resolved_key = typer.prompt("API key", hide_input=True).strip()
    try:
        profile = _manager(ctx).add_api_profile(
            name,
            base_url=url,
            api_key=resolved_key,
            model=model,
            config=config.expanduser() if config else None,
            provider_id=provider_id,
            health_mode=health_mode,
            health_endpoint=health_endpoint,
            health_method=health_method,
            expected_text=expected_text,
            timeout_seconds=timeout,
            balance_url=balance_url,
            balance_path=balance_path,
            notes=notes,
            force=force,
        )
    except (RelayError, OSError) as exc:
        _fail(exc)
    console.print(
        f"Added API profile [bold]{profile.name}[/bold] using provider "
        f"[cyan]{profile.provider_id}[/cyan]."
    )


@app.command("use")
def use_profile(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile to activate.")],
) -> None:
    """Manually activate a profile."""
    try:
        backup = _manager(ctx).switch(name, reason="manual")
    except (RelayError, OSError) as exc:
        _fail(exc)
    console.print(f"Activated [bold green]{name}[/bold green].")
    if backup:
        console.print(f"Previous active files backed up to {backup}.")
    console.print("Restart existing Codex CLI/App processes so they reload auth and config files.")


def _usage_text(result: ProbeResult) -> str:
    if result.usage:
        parts: list[str] = []
        primary = result.usage.get("primary")
        secondary = result.usage.get("secondary")
        if isinstance(primary, dict) and primary.get("used_percent") is not None:
            parts.append(f"primary {primary['used_percent']:.1f}%")
        if isinstance(secondary, dict) and secondary.get("used_percent") is not None:
            parts.append(f"secondary {secondary['used_percent']:.1f}%")
        credits = result.usage.get("credits")
        if isinstance(credits, dict):
            if credits.get("unlimited") is True:
                parts.append("credits unlimited")
            elif credits.get("balance") not in (None, ""):
                parts.append(f"credits {credits['balance']}")
        return ", ".join(parts) or "available"
    if result.balance is not None:
        rendered = json.dumps(result.balance, ensure_ascii=False)
        return rendered[:80]
    return "—"


def _status_table(
    profiles: list[Profile],
    active: str | None,
    results: list[ProbeResult] | None,
    active_state: str,
) -> Table:
    result_map = {item.profile: item for item in (results or [])}
    table = Table(title=f"Codex profiles and status · active state: {active_state}")
    table.add_column("Active", justify="center")
    table.add_column("Profile", style="bold")
    table.add_column("Type")
    table.add_column("Model")
    table.add_column("Endpoint / account", overflow="fold")
    table.add_column("Check")
    table.add_column("Health")
    table.add_column("Latency")
    table.add_column("Usage / balance")
    table.add_column("Detail", overflow="fold")
    for profile in profiles:
        result = result_map.get(profile.name)
        endpoint = profile.base_url or (profile.account_email or "ChatGPT")
        if result is None:
            health = "[dim]not checked[/dim]"
            latency = "—"
            usage = "—"
            detail = "network probe disabled"
        else:
            health = "[green]healthy[/green]" if result.healthy else f"[red]{result.status}[/red]"
            latency = f"{result.latency_ms:.0f} ms" if result.latency_ms is not None else "—"
            usage = _usage_text(result)
            detail = result.message or ""
        table.add_row(
            "●" if profile.name == active else "",
            profile.name,
            profile.kind,
            profile.model or "—",
            endpoint,
            profile.health.mode,
            health,
            latency,
            usage,
            detail,
        )
    return table


def _status_snapshot(manager: RelayManager, probe: bool) -> tuple[list[Profile], str | None, str, list[ProbeResult] | None]:
    profiles = manager.list_profiles()
    active, active_state = manager.current_profile()
    results = manager.probe_many([profile.name for profile in profiles]) if probe else None
    return profiles, active, active_state, results


@app.command("status")
def status(
    ctx: typer.Context,
    no_probe: Annotated[bool, typer.Option("--no-probe", help="Do not make network requests.")] = False,
    watch: Annotated[bool, typer.Option("--watch", help="Continuously refresh status.")] = False,
    interval: Annotated[float, typer.Option("--interval", min=1.0)] = 30.0,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List profiles and show active state, health, usage, and optional API balance."""
    manager = _manager(ctx)

    def render_once() -> tuple[Table, dict[str, Any]]:
        profiles, active, active_state, results = _status_snapshot(manager, not no_probe)
        payload = {
            "active_profile": active,
            "active_state": active_state,
            "profiles": [profile.to_dict() for profile in profiles],
            "results": [result.to_dict() for result in (results or [])],
        }
        return _status_table(profiles, active, results, active_state), payload

    if not watch:
        table, payload = render_once()
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            console.print(table)
            app_context: AppContext = ctx.obj
            if app_context.bootstrap_error and not payload["profiles"]:
                console.print(
                    "[yellow]Current Codex configuration was not auto-imported:[/yellow] "
                    + app_context.bootstrap_error
                )
        return

    if json_output:
        try:
            while True:
                _, payload = render_once()
                typer.echo(json.dumps(payload, ensure_ascii=False))
                time.sleep(interval)
        except KeyboardInterrupt:
            return

    table, _ = render_once()
    try:
        with Live(table, console=console, refresh_per_second=4) as live:
            while True:
                time.sleep(interval)
                table, _ = render_once()
                live.update(table)
    except KeyboardInterrupt:
        return


@app.command("auto")
def auto_switch(
    ctx: typer.Context,
    order: Annotated[
        list[str] | None,
        typer.Argument(help="Profiles in priority order. Defaults to all profiles by name."),
    ] = None,
    watch: Annotated[bool, typer.Option("--watch", help="Run continuously.")] = False,
    interval: Annotated[float, typer.Option("--interval", min=1.0)] = 60.0,
    cooldown: Annotated[int, typer.Option("--cooldown", min=0)] = 300,
    fail_threshold: Annotated[int, typer.Option("--fail-threshold", min=1)] = 1,
    recover_threshold: Annotated[int, typer.Option("--recover-threshold", min=1)] = 2,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Select the first healthy profile and optionally keep monitoring for failover/recovery."""
    manager = _manager(ctx)
    selected_order = order or []

    def run_once() -> dict[str, Any]:
        return manager.auto_once(
            selected_order,
            cooldown_seconds=cooldown,
            fail_threshold=fail_threshold,
            recover_threshold=recover_threshold,
        )

    try:
        while True:
            result = run_once()
            if json_output:
                typer.echo(json.dumps(result, ensure_ascii=False))
            else:
                target = result.get("target") or "none"
                console.print(
                    f"[{result['checked_at']}] action=[bold]{result['action']}[/bold] "
                    f"target=[cyan]{target}[/cyan] · {result['reason']}"
                )
                for item in result["results"]:
                    mark = "[green]healthy[/green]" if item["healthy"] else f"[red]{item['status']}[/red]"
                    console.print(f"  {item['profile']}: {mark}")
            if not watch:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        return
    except (RelayError, OSError) as exc:
        _fail(exc)


@app.command(
    "launch",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def launch_codex(
    ctx: typer.Context,
    profiles: Annotated[
        list[str] | None,
        typer.Option("--profile", "-p", help="Profile priority; repeat this option."),
    ] = None,
    cooldown: Annotated[int, typer.Option("--cooldown", min=0)] = 0,
) -> None:
    """Select a healthy profile, then launch a fresh Codex process with remaining arguments."""
    manager = _manager(ctx)
    if shutil.which("codex") is None:
        _fail(RelayError("The codex executable was not found on PATH."))
    try:
        result = manager.auto_once(
            profiles or [],
            cooldown_seconds=cooldown,
            fail_threshold=1,
            recover_threshold=1,
        )
    except (RelayError, OSError) as exc:
        _fail(exc)
    if not result.get("target"):
        _fail(RelayError("No healthy profile is available."))
    argv = ["codex", *ctx.args]
    console.print(
        f"Launching Codex with [bold green]{result['target']}[/bold green]: "
        + " ".join(argv)
    )
    os.execvp("codex", argv)


@app.command("remove")
def remove(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    force_active: Annotated[bool, typer.Option("--force-active")] = False,
) -> None:
    """Remove a stored profile. This does not delete active Codex files unless they are later replaced."""
    try:
        _manager(ctx).remove_profile(name, force_active=force_active)
    except (RelayError, OSError) as exc:
        _fail(exc)
    console.print(f"Removed profile [bold]{name}[/bold].")


@app.command("doctor")
def doctor(
    ctx: typer.Context,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Check paths, Codex installation, active state, and profile validity."""
    checks = _manager(ctx).doctor()
    if json_output:
        typer.echo(json.dumps(checks, ensure_ascii=False, indent=2))
        raise typer.Exit(0 if all(item["ok"] for item in checks) else 1)
    table = Table(title="CoderRelay doctor")
    table.add_column("Result", justify="center")
    table.add_column("Check")
    table.add_column("Detail")
    for item in checks:
        table.add_row("[green]PASS[/green]" if item["ok"] else "[red]FAIL[/red]", item["name"], item["detail"])
    console.print(table)
    raise typer.Exit(0 if all(item["ok"] for item in checks) else 1)


def main() -> None:
    """Run the CLI after silently ensuring shell completion is configured."""
    completion_init()
    if "uninstall" not in sys.argv[1:]:
        ensure_completion(app)
    app()
