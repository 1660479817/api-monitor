from __future__ import annotations

import httpx

from api_monitor.providers.base import BaseProvider, ModelsListResult
from api_monitor.results import CheckResult


class GeminiProvider(BaseProvider):
    name = "gemini"
    default_base_url = "https://generativelanguage.googleapis.com"

    async def fetch_models(
        self,
        client: httpx.AsyncClient,
        api_key: str,
    ) -> ModelsListResult:
        url = f"{self.base_url}/v1beta/models"
        return await self._fetch(
            send=lambda: client.get(url, params={"key": api_key}),
            parse=self._parse_gemini_models,
        )

    async def probe_model(
        self,
        client: httpx.AsyncClient,
        alias: str,
        api_key: str,
        masked_key: str,
        model: str,
    ) -> CheckResult:
        model_id = model.removeprefix("models/")
        url = f"{self.base_url}/v1beta/models/{model_id}:generateContent"
        body = {
            "contents": [{"parts": [{"text": self.probe_prompt()}]}],
            "generationConfig": {"maxOutputTokens": 1},
        }
        return await self._request(
            alias,
            masked_key,
            model=model,
            send=lambda: client.post(url, params={"key": api_key}, json=body),
        )

    @staticmethod
    def _parse_gemini_models(response: httpx.Response) -> list[str]:
        payload = response.json()
        models: list[str] = []
        for item in payload.get("models", []):
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            if not name:
                continue
            models.append(name.removeprefix("models/"))
        return models
