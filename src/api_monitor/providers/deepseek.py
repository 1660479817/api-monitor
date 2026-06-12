from __future__ import annotations

from api_monitor.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    default_base_url = "https://api.deepseek.com/v1"


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"
