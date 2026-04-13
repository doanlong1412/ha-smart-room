"""Persistent storage for HA Smart Room — keeps room registry across restarts."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DEFAULT_DELAY_MIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

# Required keys every room record must have (with fallback defaults)
_ROOM_DEFAULTS: dict[str, Any] = {
    "room_id":         "",
    "room_title":      "Smart Room",
    "delay_min":       DEFAULT_DELAY_MIN,
    "motion_entity":   "",
    "device_entities": [],
}


def _validate_room(raw: Any) -> dict[str, Any] | None:
    """Return a sanitised room dict, or None if the record is unusable."""
    if not isinstance(raw, dict):
        return None
    room_id = raw.get("room_id", "")
    if not room_id or not isinstance(room_id, str):
        return None
    # Fill every missing / wrong-type field with its default
    out: dict[str, Any] = {}
    for key, default in _ROOM_DEFAULTS.items():
        value = raw.get(key, default)
        # Coerce types silently rather than rejecting the whole record
        if key == "delay_min":
            try:
                value = max(1, int(value))
            except (TypeError, ValueError):
                value = default
        elif key == "device_entities":
            if not isinstance(value, list):
                value = []
            else:
                value = [e for e in value if isinstance(e, str)]
        elif not isinstance(value, type(default)) and default is not None:
            value = default
        out[key] = value
    return out


class RoomRegistry:
    """Stores and loads room definitions from HA persistent storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass  = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._rooms: dict[str, dict[str, Any]] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def async_load(self) -> None:
        """Load rooms from disk, silently skipping any corrupted entries."""
        data = await self._store.async_load()
        if not data or "rooms" not in data:
            return

        loaded: dict[str, dict[str, Any]] = {}
        raw_rooms = data["rooms"]

        if isinstance(raw_rooms, dict):
            items = raw_rooms.values()
        elif isinstance(raw_rooms, list):
            items = raw_rooms
        else:
            _LOGGER.warning("Unexpected rooms format in storage — resetting")
            return

        for raw in items:
            room = _validate_room(raw)
            if room is None:
                _LOGGER.warning("Skipping invalid room record: %s", raw)
                continue
            loaded[room["room_id"]] = room

        self._rooms = loaded
        _LOGGER.debug("Loaded %d room(s) from storage", len(self._rooms))

    async def async_save(self) -> None:
        """Persist rooms to disk."""
        await self._store.async_save({"rooms": self._rooms})

    @property
    def rooms(self) -> dict[str, dict[str, Any]]:
        """Return a shallow copy so callers cannot mutate internal state."""
        return dict(self._rooms)

    def get(self, room_id: str) -> dict[str, Any] | None:
        return self._rooms.get(room_id)

    async def async_register(
        self,
        room_id: str,
        room_title: str,
        delay_min: int,
        motion_entity: str | None = None,
        device_entities: list[str] | None = None,
    ) -> bool:
        """Register or update a room.  Returns True if anything changed."""
        new_data: dict[str, Any] = {
            "room_id":         room_id,
            "room_title":      room_title,
            "delay_min":       max(1, int(delay_min)),
            "motion_entity":   motion_entity or "",
            "device_entities": list(device_entities or []),
        }
        if self._rooms.get(room_id) == new_data:
            return False
        self._rooms[room_id] = new_data
        await self.async_save()
        _LOGGER.info("Registered room '%s' (id=%s)", room_title, room_id)
        return True

    async def async_unregister(self, room_id: str) -> bool:
        """Remove a room. Returns True if it existed."""
        if room_id not in self._rooms:
            return False
        del self._rooms[room_id]
        await self.async_save()
        _LOGGER.info("Unregistered room id=%s", room_id)
        return True
