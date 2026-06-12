from __future__ import annotations

import httpx

from api_monitor.providers.base import BaseProvider, ModelsListResult
from api_monitor.results import CheckResult


class OpenAICompatibleProvider(BaseProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"

    def _auth_headers(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    async def fetch_models(
        self,
        client: httpx.AsyncClient,
        api_key: str,
    ) -> ModelsListResult:
        url = f"{self.base_url}/models"
        return await self._fetch(
            send=lambda: client.get(url, headers=self._auth_headers(api_key)),
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
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": model,
            "messages": [{"role": "user", "content": self.probe_prompt()}],
            "max_tokens": 1,
        }
        return await self._request(
            alias,
            masked_key,
            model=model,
            send=lambda: client.post(
                url, headers=self._auth_headers(api_key), json=body
            ),
        )
