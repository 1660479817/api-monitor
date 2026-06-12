from __future__ import annotations

from pathlib import Path

import yaml

from api_monitor.models import AppConfig


class ConfigError(Exception):
    """配置加载或校验失败。"""


def load_config(path: Path) -> AppConfig:
    if not path.is_file():
        raise ConfigError(f"配置文件不存在: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML 解析失败: {exc}") from exc

    if raw is None:
        raise ConfigError("配置文件为空")

    if not isinstance(raw, dict):
        raise ConfigError("配置文件根节点必须是 mapping")

    try:
        return AppConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigError(f"配置校验失败: {exc}") from exc
