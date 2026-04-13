"""Switch platform — one auto-off toggle per room."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from . import get_coordinators
from .const import DOMAIN
from .coordinator import RoomCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators = get_coordinators(hass, entry.entry_id)

    hass.data[DOMAIN].setdefault(f"{entry.entry_id}_add_entities", {})
    hass.data[DOMAIN][f"{entry.entry_id}_add_entities"]["switch"] = async_add_entities

    async_add_entities(
        AutoModeSwitch(coord, entry.entry_id)
        for coord in coordinators.values()
    )


class AutoModeSwitch(SwitchEntity):
    """Switch to enable / disable auto-off mode for one room."""

    _attr_has_entity_name = False   # dùng tên đầy đủ để entity_id đoán được
    _attr_icon            = "mdi:robot"

    def __init__(self, coord: RoomCoordinator, entry_id: str) -> None:
        self._coord    = coord
        self._entry_id = entry_id
        # unique_id và name đều dùng room_id để entity_id = switch.{room_id}_auto_off
        self._attr_unique_id = f"{coord.room_id}_{DOMAIN}_auto"
        self._attr_name      = f"{coord.room_id}_auto_off"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coord.room_id)},
            name=coord.room_title,
            manufacturer="HA Smart Room",
        )
        self._unsub: callable | None = None

    @property
    def is_on(self) -> bool:
        return self._coord.auto_enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "room_id":    self._coord.room_id,
            "room_title": self._coord.room_title,
            "delay_min":  self._coord.delay_min,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._coord.async_set_auto(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._coord.async_set_auto(False)

    async def async_added_to_hass(self) -> None:
        self._unsub = self._coord.async_add_listener(self._on_coordinator_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()

    @callback
    def _on_coordinator_update(self) -> None:
        self.async_write_ha_state()
