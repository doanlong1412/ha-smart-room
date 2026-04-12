"""Persistent storage for HA Smart Room — keeps room registry across restarts."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class RoomRegistry:
    """Stores and loads room definitions from HA persistent storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass  = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._rooms: dict[str, dict[str, Any]] = {}   # room_id → room data

    # ── Public API ────────────────────────────────────────────────────────────

    async def async_load(self) -> None:
        """Load rooms from disk."""
        data = await self._store.async_load()
        if data and "rooms" in data:
            self._rooms = data["rooms"]
            _LOGGER.debug("Loaded %d room(s) from storage", len(self._rooms))

    async def async_save(self) -> None:
        """Persist rooms to disk."""
        await self._store.async_save({"rooms": self._rooms})

    @property
    def rooms(self) -> dict[str, dict[str, Any]]:
        """Return a copy of the current room map."""
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
        """Register or update a room. Returns True if something changed."""
        existing = self._rooms.get(room_id)
        new_data: dict[str, Any] = {
            "room_id":        room_id,
            "room_title":     room_title,
            "delay_min":      delay_min,
            "motion_entity":  motion_entity or "",
            "device_entities": device_entities or [],
        }
        if existing == new_data:
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
