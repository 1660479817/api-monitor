from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from api_monitor.config import ConfigError, load_config
from api_monitor.providers import PROVIDER_REGISTRY, get_provider_class
from api_monitor.runner import run_checks

app = typer.Typer(
    name="api-monitor",
    help="批量检测多个 AI 平台 API Key 是否可用",
    add_completion=False,
    invoke_without_command=True,
)
console = Console(stderr=True)


def _render_table(results) -> None:
    table = Table(title="API Key 检测结果", show_lines=False)
    table.add_column("Platform", style="cyan")
    table.add_column("Alias")
    table.add_column("Model")
    table.add_column("Key (masked)", style="dim")
    table.add_column("Status")
    table.add_column("HTTP", justify="right")
    table.add_column("Latency", justify="right")
    table.add_column("Error", overflow="fold")

    for item in results:
        status_style = "green" if item.status == "OK" else "red"
        http = str(item.http_status) if item.http_status is not None else "-"
        latency = f"{item.latency_ms:.0f}ms" if item.latency_ms is not None else "-"
        table.add_row(
            item.platform,
            item.alias,
            item.model or "-",
            item.masked_key,
            f"[{status_style}]{item.status}[/{status_style}]",
            http,
            latency,
            item.error or "-",
        )

    console.print(table)


def _exit_code(results) -> int:
    if any(r.status == "FAILED" for r in results):
        return 1
    return 0


@app.callback()
def main(
    ctx: typer.Context,
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="配置文件路径"),
    ] = Path("config.yaml"),
    provider: Annotated[
        Optional[str],
        typer.Option("--provider", "-p", help="仅检测指定平台"),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="以 JSON 格式输出结果"),
    ] = False,
    timeout: Annotated[
        Optional[float],
        typer.Option("--timeout", "-t", help="单次请求超时（秒）"),
    ] = None,
    concurrency: Annotated[
        Optional[int],
        typer.Option("--concurrency", "-n", help="并发检测数"),
    ] = None,
) -> None:
    """批量检测配置文件中各平台 API Key 是否可用。"""
    if ctx.invoked_subcommand is not None:
        return

    try:
        cfg = load_config(config)
    except ConfigError as exc:
        console.print(f"[red]配置错误:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if provider:
        try:
            get_provider_class(provider)
        except ValueError as exc:
            console.print(f"[red]配置错误:[/red] {exc}")
            raise typer.Exit(code=2) from exc
        if provider.lower() not in {k.lower() for k in cfg.providers}:
            console.print(f"[red]配置错误:[/red] 配置中未找到平台 '{provider}'")
            raise typer.Exit(code=2)

    effective_timeout = timeout if timeout is not None else cfg.timeout
    effective_concurrency = concurrency if concurrency is not None else cfg.concurrency

    if effective_concurrency < 1:
        console.print("[red]配置错误:[/red] concurrency 必须 >= 1")
        raise typer.Exit(code=2)

    pcfg = None
    if provider:
        pcfg = cfg.providers.get(provider) or next(
            (v for k, v in cfg.providers.items() if k.lower() == provider.lower()),
            None,
        )
    has_tasks = bool(pcfg.keys) if provider else any(
        p.keys for p in cfg.providers.values()
    )

    if not has_tasks:
        console.print("[yellow]警告:[/yellow] 没有可检测的 API Key")
        raise typer.Exit(code=0)

    try:
        results = asyncio.run(
            run_checks(
                cfg,
                timeout=effective_timeout,
                concurrency=effective_concurrency,
                provider_filter=provider,
            )
        )
    except ValueError as exc:
        console.print(f"[red]配置错误:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if as_json:
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    else:
        _render_table(results)
        ok = sum(1 for r in results if r.status == "OK")
        failed = len(results) - ok
        console.print(f"\n合计: {len(results)} 项检测，成功 {ok}，失败 {failed}")

    raise typer.Exit(code=_exit_code(results))


@app.command("providers")
def providers_command() -> None:
    """列出支持的平台名称。"""
    for name in sorted(PROVIDER_REGISTRY):
        console.print(name)
