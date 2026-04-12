"""Sensor platform — status + last_motion sensors per room."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import get_coordinators
from .const import DOMAIN, STATUS_IDLE, STATUS_OCCUPIED, STATUS_COUNTDOWN, STATUS_TRIGGERED
from .coordinator import RoomCoordinator

_LOGGER = logging.getLogger(__name__)

STATUS_ICONS = {
    STATUS_IDLE:      "mdi:home-outline",
    STATUS_OCCUPIED:  "mdi:account",
    STATUS_COUNTDOWN: "mdi:timer-sand",
    STATUS_TRIGGERED: "mdi:power-off",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators = get_coordinators(hass, entry.entry_id)
    entities = []
    for coord in coordinators.values():
        entities.append(RoomStatusSensor(coord, entry.entry_id))
        entities.append(RoomLastMotionSensor(coord, entry.entry_id))
        entities.append(RoomCountdownSensor(coord, entry.entry_id))
    async_add_entities(entities)


# ── Status sensor ─────────────────────────────────────────────────────────────

class RoomStatusSensor(SensorEntity):
    """Sensor showing current auto-off status: idle / occupied / countdown / triggered."""

    _attr_has_entity_name = True

    def __init__(self, coord: RoomCoordinator, entry_id: str) -> None:
        self._coord    = coord
        self._entry_id = entry_id
        self._attr_unique_id = f"{coord.room_id}_{DOMAIN}_status"
        self._attr_name      = f"{coord.room_title} Status"
        self._unsub = None

    @property
    def native_value(self) -> str:
        return self._coord.status

    @property
    def icon(self) -> str:
        return STATUS_ICONS.get(self._coord.status, "mdi:home-outline")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "room_id":      self._coord.room_id,
            "room_title":   self._coord.room_title,
            "auto_enabled": self._coord.auto_enabled,
            "delay_min":    self._coord.delay_min,
        }

    async def async_added_to_hass(self) -> None:
        self._unsub = self._coord.async_add_listener(self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()

    @callback
    def _on_update(self) -> None:
        self.async_write_ha_state()


# ── Last motion sensor ────────────────────────────────────────────────────────

class RoomLastMotionSensor(SensorEntity):
    """Sensor showing timestamp of last detected motion."""

    _attr_has_entity_name  = True
    _attr_device_class     = SensorDeviceClass.TIMESTAMP
    _attr_icon             = "mdi:motion-sensor"

    def __init__(self, coord: RoomCoordinator, entry_id: str) -> None:
        self._coord    = coord
        self._entry_id = entry_id
        self._attr_unique_id = f"{coord.room_id}_{DOMAIN}_last_motion"
        self._attr_name      = f"{coord.room_title} Last Motion"
        self._unsub = None

    @property
    def native_value(self):
        return self._coord.last_motion_at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "room_id":    self._coord.room_id,
            "room_title": self._coord.room_title,
        }

    async def async_added_to_hass(self) -> None:
        self._unsub = self._coord.async_add_listener(self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()

    @callback
    def _on_update(self) -> None:
        self.async_write_ha_state()


# ── Countdown sensor ──────────────────────────────────────────────────────────

class RoomCountdownSensor(SensorEntity):
    """Sensor showing remaining seconds until auto-off fires."""

    _attr_has_entity_name             = True
    _attr_icon                        = "mdi:timer-outline"
    _attr_native_unit_of_measurement  = "s"

    def __init__(self, coord: RoomCoordinator, entry_id: str) -> None:
        self._coord    = coord
        self._entry_id = entry_id
        self._attr_unique_id = f"{coord.room_id}_{DOMAIN}_countdown"
        self._attr_name      = f"{coord.room_title} Countdown"
        self._unsub = None

    @property
    def native_value(self) -> int | None:
        return self._coord.countdown_remaining_seconds

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "room_id":    self._coord.room_id,
            "room_title": self._coord.room_title,
            "delay_min":  self._coord.delay_min,
        }

    async def async_added_to_hass(self) -> None:
        self._unsub = self._coord.async_add_listener(self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()

    @callback
    def _on_update(self) -> None:
        self.async_write_ha_state()
