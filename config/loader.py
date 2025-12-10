from __future__ import annotations

from functools import lru_cache

from .schemas import Settings


@lru_cache
def get_settings() -> Settings:
    """
    Load settings using pydantic BaseSettings.

    - Reads from .env (because Settings.model_config has env_file=".env")
    - Uses env_nested_delimiter="__" for nested keys
    """
    return Settings()
