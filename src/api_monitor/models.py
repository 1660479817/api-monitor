from __future__ import annotations

from pydantic import BaseModel, Field


class KeyEntry(BaseModel):
    alias: str
    api_key: str
    models: list[str] = Field(default_factory=list)


class ProviderConfig(BaseModel):
    base_url: str | None = None
    keys: list[KeyEntry] = Field(default_factory=list)


class AppConfig(BaseModel):
    timeout: float = 10.0
    concurrency: int = 5
    max_auto_models: int = 20
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
