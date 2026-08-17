"""Общие зависимости FastAPI.

Настройки прокидываются зависимостью, а не читаются модулем напрямую: так их
можно подменить в тестах через `app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from navigator.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]
