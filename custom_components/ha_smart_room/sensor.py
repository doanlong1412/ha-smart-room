"""Sensor platform — status, last_motion, and countdown sensors per room."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from . import get_coordinators
from .const import (
    DOMAIN,
    STATUS_COUNTDOWN,
    STATUS_IDLE,
    STATUS_OCCUPIED,
    STATUS_TRIGGERED,
)
from .coordinator import RoomCoordinator

_LOGGER = logging.getLogger(__name__)

STATUS_ICONS: dict[str, str] = {
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

    hass.data[DOMAIN].setdefault(f"{entry.entry_id}_add_entities", {})
    hass.data[DOMAIN][f"{entry.entry_id}_add_entities"]["sensor"] = async_add_entities

    entities = []
    for coord in coordinators.values():
        entities.append(RoomStatusSensor(coord, entry.entry_id))
        entities.append(RoomLastMotionSensor(coord, entry.entry_id))
        entities.append(RoomCountdownSensor(coord, entry.entry_id))
    async_add_entities(entities)


class _RoomSensorBase(SensorEntity):
    """Shared lifecycle for all room sensors."""

    _attr_has_entity_name = False   # tên đầy đủ để entity_id đoán được

    def __init__(self, coord: RoomCoordinator, entry_id: str) -> None:
        self._coord    = coord
        self._entry_id = entry_id
        self._unsub: callable | None = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coord.room_id)},
            name=coord.room_title,
            manufacturer="HA Smart Room",
        )

    async def async_added_to_hass(self) -> None:
        self._unsub = self._coord.async_add_listener(self._on_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()

    @callback
    def _on_update(self) -> None:
        self.async_write_ha_state()


class RoomStatusSensor(_RoomSensorBase):
    def __init__(self, coord: RoomCoordinator, entry_id: str) -> None:
        super().__init__(coord, entry_id)
        self._attr_unique_id = f"{coord.room_id}_{DOMAIN}_status"
        self._attr_name      = f"{coord.room_id}_status"

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


class RoomLastMotionSensor(_RoomSensorBase):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon         = "mdi:motion-sensor"

    def __init__(self, coord: RoomCoordinator, entry_id: str) -> None:
        super().__init__(coord, entry_id)
        self._attr_unique_id = f"{coord.room_id}_{DOMAIN}_last_motion"
        self._attr_name      = f"{coord.room_id}_last_motion"

    @property
    def native_value(self):
        return self._coord.last_motion_at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "room_id":    self._coord.room_id,
            "room_title": self._coord.room_title,
        }


class RoomCountdownSensor(_RoomSensorBase):
    _attr_icon                       = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "s"

    def __init__(self, coord: RoomCoordinator, entry_id: str) -> None:
        super().__init__(coord, entry_id)
        self._attr_unique_id = f"{coord.room_id}_{DOMAIN}_countdown"
        self._attr_name      = f"{coord.room_id}_countdown"

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
