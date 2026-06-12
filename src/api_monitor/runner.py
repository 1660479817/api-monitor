from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from api_monitor.masking import mask_api_key
from api_monitor.models import AppConfig, KeyEntry
from api_monitor.providers import get_provider_class
from api_monitor.providers.base import BaseProvider
from api_monitor.results import CheckResult


@dataclass(frozen=True)
class CheckTask:
    platform: str
    provider: BaseProvider
    key: KeyEntry


def build_tasks(
    config: AppConfig,
    provider_filter: str | None = None,
) -> list[CheckTask]:
    tasks: list[CheckTask] = []
    for platform, provider_cfg in config.providers.items():
        if provider_filter and platform.lower() != provider_filter.lower():
            continue
        if not provider_cfg.keys:
            continue
        provider_cls = get_provider_class(platform)
        provider = provider_cls(base_url=provider_cfg.base_url)
        for key in provider_cfg.keys:
            tasks.append(CheckTask(platform=platform, provider=provider, key=key))
    return tasks


async def _run_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    task: CheckTask,
    max_auto_models: int,
) -> list[CheckResult]:
    masked = mask_api_key(task.key.api_key)
    return await task.provider.check_key_entry(
        client,
        semaphore,
        alias=task.key.alias,
        api_key=task.key.api_key,
        masked_key=masked,
        models=task.key.models,
        max_auto_models=max_auto_models,
    )


async def run_checks(
    config: AppConfig,
    *,
    timeout: float,
    concurrency: int,
    provider_filter: str | None = None,
) -> list[CheckResult]:
    tasks = build_tasks(config, provider_filter)
    if not tasks:
        return []

    semaphore = asyncio.Semaphore(max(1, concurrency))
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        nested = await asyncio.gather(
            *[_run_one(client, semaphore, task, config.max_auto_models) for task in tasks]
        )
        return [item for group in nested for item in group]
