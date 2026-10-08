"""Tiny timestamped JSON cache shared by all verification components.

Only company-level evidence is cached. Recruiter names/emails are never written here.
"""
import json
import time
from typing import Any, Optional, Tuple

import config


def _load() -> dict:
    try:
        with open(config.CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def cache_get(key: str) -> Optional[Tuple[Any, float]]:
    """Return (value, timestamp) if present and fresh (TTL from config), else None."""
    if not config.CACHE_ENABLED:
        return None
    item = _load().get(key)
    if item and time.time() - item["ts"] < config.CACHE_TTL_HOURS * 3600:
        return item["result"], item["ts"]
    return None


def cache_put(key: str, value: Any) -> None:
    """Store value with the current timestamp; silently ignore IO errors."""
    if not config.CACHE_ENABLED:
        return
    try:
        data = _load()
        now = time.time()
        data = {k: v for k, v in data.items() if now - v.get("ts", 0) < config.CACHE_TTL_HOURS * 3600}
        data[key] = {"ts": now, "result": value}
        with open(config.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except (OSError, TypeError):
        pass
