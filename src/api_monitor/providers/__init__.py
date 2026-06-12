from __future__ import annotations

from typing import Type

from api_monitor.providers.anthropic import AnthropicProvider
from api_monitor.providers.base import BaseProvider
from api_monitor.providers.deepseek import DeepSeekProvider, OpenRouterProvider
from api_monitor.providers.gemini import GeminiProvider
from api_monitor.providers.openai_compatible import OpenAICompatibleProvider

PROVIDER_REGISTRY: dict[str, Type[BaseProvider]] = {
    "openai": OpenAICompatibleProvider,
    "openai-compatible": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "openrouter": OpenRouterProvider,
}


def get_provider_class(name: str) -> Type[BaseProvider]:
    key = name.strip().lower()
    if key not in PROVIDER_REGISTRY:
        supported = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(f"未知平台 '{name}'，支持: {supported}")
    return PROVIDER_REGISTRY[key]
