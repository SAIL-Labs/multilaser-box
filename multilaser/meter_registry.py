"""
Known power meters and their friendly names.

Meters are keyed by the meter's own serial number (the serial field of its
USB VISA resource, e.g. ``P0012345``), which is the same under NI-VISA and
pyvisa-py and doesn't change when the sensor head is swapped. A friendly
name can match the label stuck on the meter ("Ref tap", "Bench B").

Stored as one JSON value under ``power_meter/known_meters`` in the app's
QSettings, alongside the other settings::

    {"P0012345": {"name": "Ref tap", "model": "PM100USB",
                  "sensor": "S120C,...", "resource": "USB0::...",
                  "last_seen": 1730790000.0}}

Works with any object offering QSettings-style ``value()``/``setValue()``.
"""

import json
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

SETTINGS_KEY = "power_meter/known_meters"


class MeterRegistry:
    """Friendly names and last-seen details for power meters."""

    def __init__(self, settings):
        self.settings = settings

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, dict]:
        raw = self.settings.value(SETTINGS_KEY, "")
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Ignoring unreadable %s setting", SETTINGS_KEY)
            return {}
        return {str(k): dict(v) for k, v in data.items() if isinstance(v, dict)}

    def _save(self, data: Dict[str, dict]) -> None:
        self.settings.setValue(SETTINGS_KEY, json.dumps(data, sort_keys=True))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def devices(self) -> Dict[str, dict]:
        """All known meters, keyed by serial."""
        return self._load()

    def name(self, serial: str) -> str:
        """Friendly name for a serial, or "" if none set."""
        if not serial:
            return ""
        return str(self._load().get(serial, {}).get("name", ""))

    def label(self, serial: str, fallback: Optional[str] = None) -> str:
        """Display label: "Ref tap (P0012345)", or just the serial."""
        name = self.name(serial)
        ident = serial or fallback or "unknown"
        return f"{name} ({ident})" if name else ident

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------

    def set_name(self, serial: str, name: str) -> None:
        """Set (or clear, with "") a meter's friendly name."""
        if not serial:
            return
        data = self._load()
        entry = data.setdefault(serial, {})
        entry["name"] = name.strip()
        self._save(data)

    def record_seen(
        self,
        serial: str,
        model: str = "",
        resource: str = "",
        sensor: str = "",
    ) -> None:
        """Remember a meter that answered, keeping its name."""
        if not serial:
            return
        data = self._load()
        entry = data.setdefault(serial, {"name": ""})
        if model:
            entry["model"] = model
        if resource:
            entry["resource"] = resource
        if sensor:
            entry["sensor"] = sensor
        entry["last_seen"] = time.time()
        self._save(data)

    def remove(self, serial: str) -> None:
        data = self._load()
        if data.pop(serial, None) is not None:
            self._save(data)
