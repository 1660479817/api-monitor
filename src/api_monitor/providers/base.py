from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from api_monitor.results import CheckResult

_PROBE_PROMPT = "1"


@dataclass
class ModelsListResult:
    models: list[str]
    http_status: int | None = None
    latency_ms: float | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class BaseProvider(ABC):
    name: str
    default_base_url: str

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or self.default_base_url).rstrip("/")

    @abstractmethod
    async def fetch_models(
        self,
        client: httpx.AsyncClient,
        api_key: str,
    ) -> ModelsListResult:
        raise NotImplementedError

    @abstractmethod
    async def probe_model(
        self,
        client: httpx.AsyncClient,
        alias: str,
        api_key: str,
        masked_key: str,
        model: str,
    ) -> CheckResult:
        raise NotImplementedError

    async def check_key_entry(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        alias: str,
        api_key: str,
        masked_key: str,
        models: list[str],
        max_auto_models: int,
    ) -> list[CheckResult]:
        listed = await self.fetch_models(client, api_key)
        if not listed.ok:
            return [
                self._failed(
                    alias,
                    masked_key,
                    model="-",
                    http_status=listed.http_status,
                    latency_ms=listed.latency_ms,
                    error=f"List models failed: {listed.error}",
                )
            ]

        if models:
            targets = models
        else:
            targets = listed.models[:max_auto_models]

        if not targets:
            return [
                self._failed(
                    alias,
                    masked_key,
                    model="-",
                    http_status=listed.http_status,
                    latency_ms=listed.latency_ms,
                    error="No models to probe",
                )
            ]

        async def _probe(model: str) -> CheckResult:
            async with semaphore:
                return await self.probe_model(
                    client, alias, api_key, masked_key, model
                )

        return list(await asyncio.gather(*[_probe(model) for model in targets]))

    async def _request(
        self,
        alias: str,
        masked_key: str,
        model: str | None,
        send: Callable[[], Awaitable[httpx.Response]],
    ) -> CheckResult:
        started = time.perf_counter()
        try:
            response = await send()
        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - started) * 1000
            return self._failed(
                alias,
                masked_key,
                model=model,
                latency_ms=latency_ms,
                error="Request timed out",
            )
        except httpx.RequestError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return self._failed(
                alias,
                masked_key,
                model=model,
                latency_ms=latency_ms,
                error=str(exc),
            )

        latency_ms = (time.perf_counter() - started) * 1000
        if response.is_success:
            return self._ok(
                alias,
                masked_key,
                model=model,
                http_status=response.status_code,
                latency_ms=latency_ms,
            )
        return self._failed(
            alias,
            masked_key,
            model=model,
            http_status=response.status_code,
            latency_ms=latency_ms,
            error=self._extract_error(response),
        )

    async def _fetch(
        self,
        send: Callable[[], Awaitable[httpx.Response]],
        parse: Callable[[httpx.Response], list[str]],
    ) -> ModelsListResult:
        started = time.perf_counter()
        try:
            response = await send()
        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - started) * 1000
            return ModelsListResult(
                models=[],
                latency_ms=latency_ms,
                error="Request timed out",
            )
        except httpx.RequestError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return ModelsListResult(
                models=[],
                latency_ms=latency_ms,
                error=str(exc),
            )

        latency_ms = (time.perf_counter() - started) * 1000
        if not response.is_success:
            return ModelsListResult(
                models=[],
                http_status=response.status_code,
                latency_ms=latency_ms,
                error=self._extract_error(response),
            )

        try:
            models = parse(response)
        except Exception as exc:
            return ModelsListResult(
                models=[],
                http_status=response.status_code,
                latency_ms=latency_ms,
                error=f"Failed to parse models: {exc}",
            )

        return ModelsListResult(
            models=models,
            http_status=response.status_code,
            latency_ms=latency_ms,
        )

    @staticmethod
    def probe_prompt() -> str:
        return _PROBE_PROMPT

    def _failed(
        self,
        alias: str,
        masked_key: str,
        *,
        model: str | None,
        http_status: int | None = None,
        latency_ms: float | None = None,
        error: str,
    ) -> CheckResult:
        return CheckResult(
            platform=self.name,
            alias=alias,
            masked_key=masked_key,
            model=model,
            status="FAILED",
            http_status=http_status,
            latency_ms=latency_ms,
            error=error,
        )

    def _ok(
        self,
        alias: str,
        masked_key: str,
        *,
        model: str | None,
        http_status: int,
        latency_ms: float,
    ) -> CheckResult:
        return CheckResult(
            platform=self.name,
            alias=alias,
            masked_key=masked_key,
            model=model,
            status="OK",
            http_status=http_status,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                err = payload.get("error")
                if isinstance(err, dict):
                    message = err.get("message") or err.get("type")
                    if message:
                        return str(message)
                message = payload.get("message")
                if message:
                    return str(message)
        except Exception:
            pass

        text = response.text.strip()
        if text:
            return text[:200]
        return response.reason_phrase or "Unknown error"

    @staticmethod
    def parse_openai_models(response: httpx.Response) -> list[str]:
        payload = response.json()
        data = payload.get("data", [])
        return [item["id"] for item in data if isinstance(item, dict) and "id" in item]
