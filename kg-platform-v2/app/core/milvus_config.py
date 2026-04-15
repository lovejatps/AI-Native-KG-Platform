"""Utility to load Milvus connection configuration.

The configuration can be provided in two ways:
1. Environment variables ``MILVUS_HOST`` and ``MILVUS_PORT`` (default
   ``localhost`` and ``19530``).
2. A JSON configuration file whose path is supplied via the
   ``MILVUS_CONFIG_PATH`` environment variable.  The JSON must contain the
   keys ``host`` and ``port``.

The helper returns a tuple ``(host, port)`` suitable for ``MilvusClient``.
"""

import json
import os
from .config import get_settings


def load_milvus_config() -> tuple[str, int]:
    settings = get_settings()
    # 1) If a config file path is provided, attempt to read it.
    if getattr(settings, "MILVUS_CONFIG_PATH", None):
        cfg_path = os.path.abspath(settings.MILVUS_CONFIG_PATH)
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                host = data.get("host", settings.MILVUS_HOST)
                port = int(data.get("port", settings.MILVUS_PORT))
                return host, port
            except Exception:
                # If parsing fails we fall back to env vars.
                pass
    # 2) Fallback to environment variables / defaults.
    return settings.MILVUS_HOST, settings.MILVUS_PORT
