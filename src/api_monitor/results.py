from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["OK", "FAILED"]


@dataclass
class CheckResult:
    platform: str
    alias: str
    masked_key: str
    model: str | None
    status: Status
    http_status: int | None
    latency_ms: float | None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "alias": self.alias,
            "masked_key": self.masked_key,
            "model": self.model,
            "status": self.status,
            "http_status": self.http_status,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }
