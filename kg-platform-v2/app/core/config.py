"""Compatibility shim for Settings.

The original ``app.core.config`` module defined a ``Settings`` class and a
``get_settings`` function.  Phase‑2 introduces ``SettingsV2`` with additional
environment handling and feature‑flag support (see ``settings_v2.py``).

To avoid touching every import throughout the codebase, this module now simply
re‑exports the new class under the old name.  Existing code continues to call
``get_settings()`` and receives a ``SettingsV2`` instance, while new code can
import ``SettingsV2`` directly from ``app.core.settings_v2``.
"""

from .settings_v2 import (
    SettingsV2,
    get_settings,
)  # re‑export for backward compatibility

# Backward‑compatible alias – some modules still refer to ``Settings``
Settings = SettingsV2
