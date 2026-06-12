from __future__ import annotations


def mask_api_key(api_key: str) -> str:
    """将 API Key 脱敏，仅保留首尾少量字符。"""
    key = api_key.strip()
    if not key:
        return "(empty)"

    if len(key) <= 8:
        return key[:2] + "..." + key[-1:]

    return f"{key[:6]}...{key[-3:]}"
