from __future__ import annotations

import httpx

from api_monitor.providers.base import BaseProvider, ModelsListResult
from api_monitor.results import CheckResult

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    default_base_url = "https://api.anthropic.com"

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }

    async def fetch_models(
        self,
        client: httpx.AsyncClient,
        api_key: str,
    ) -> ModelsListResult:
        url = f"{self.base_url}/v1/models"
        return await self._fetch(
            send=lambda: client.get(url, headers=self._headers(api_key)),
            parse=self.parse_openai_models,
        )

    async def probe_model(
        self,
        client: httpx.AsyncClient,
        alias: str,
        api_key: str,
        masked_key: str,
        model: str,
    ) -> CheckResult:
        url = f"{self.base_url}/v1/messages"
        body = {
            "model": model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": self.probe_prompt()}],
        }
        return await self._request(
            alias,
            masked_key,
            model=model,
            send=lambda: client.post(url, headers=self._headers(api_key), json=body),
        )
