"""
HA Smart Room Integration
=========================
Server-side brain for the HA Smart Room Card.

Architecture:
  Card  ──websocket──▶  register_room service
                              │
                              ▼
                     RoomCoordinator (per room)
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
                 switch    number    sensor
              (auto on/off) (delay)  (status/motion)
"""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
import homeassistant.helpers.entity_registry as er

from .const import (
    CONF_DELAY_MIN,
    CONF_ROOM_ID,
    CONF_ROOM_TITLE,
    DEFAULT_DELAY_MIN,
    DOMAIN,
    PLATFORMS,
    SERVICE_REGISTER_ROOM,
    SERVICE_TRIGGER_AUTOOFF,
    SERVICE_UNREGISTER_ROOM,
    SERVICE_UPDATE_MOTION,
)
from .coordinator import RoomCoordinator
from .storage import RoomRegistry

_LOGGER = logging.getLogger(__name__)

# ── Service schemas ───────────────────────────────────────────────────────────

REGISTER_ROOM_SCHEMA = vol.Schema({
    vol.Required("room_id"):          cv.string,
    vol.Required("room_title"):       cv.string,
    vol.Optional("delay_min", default=DEFAULT_DELAY_MIN): vol.All(vol.Coerce(int), vol.Range(min=1, max=120)),
    vol.Optional("motion_entity", default=""): cv.string,
    vol.Optional("device_entities", default=[]): vol.All(cv.ensure_list, [cv.string]),
})

UNREGISTER_ROOM_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
})

UPDATE_MOTION_SCHEMA = vol.Schema({
    vol.Required("room_id"):  cv.string,
    vol.Required("detected"): cv.boolean,
})

TRIGGER_AUTOOFF_SCHEMA = vol.Schema({
    vol.Required("room_id"): cv.string,
})


# ── Setup ─────────────────────────────────────────────────────────────────────

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration from configuration.yaml (not used — config flow only)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Smart Room from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Load persistent room registry
    registry = RoomRegistry(hass)
    await registry.async_load()

    # Coordinators map: room_id → RoomCoordinator
    coordinators: dict[str, RoomCoordinator] = {}

    hass.data[DOMAIN][entry.entry_id] = {
        "registry":     registry,
        "coordinators": coordinators,
    }

    # Spin up coordinators for rooms already in storage
    for room_id, room_data in registry.rooms.items():
        coord = _make_coordinator(hass, room_data)
        coordinators[room_id] = coord
        await coord.async_setup()

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    _register_services(hass, entry)

    _LOGGER.info("HA Smart Room integration loaded (%d room(s))", len(coordinators))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinators: dict[str, RoomCoordinator] = data.get("coordinators", {})

    for coord in coordinators.values():
        await coord.async_unload()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


# ── Services ──────────────────────────────────────────────────────────────────

def _register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register all services exposed to the card and automations (only once)."""
    # Services chỉ cần đăng ký 1 lần — nếu đã có thì bỏ qua
    if hass.services.has_service(DOMAIN, SERVICE_REGISTER_ROOM):
        return

    def _get_data():
        return hass.data[DOMAIN][entry.entry_id]

    async def handle_register_room(call: ServiceCall) -> None:
        """
        Called by the card on load / config change.
        Creates or updates a room coordinator + entities.
        """
        from homeassistant.helpers.entity_platform import async_get_platforms

        data        = _get_data()
        registry    = data["registry"]
        coordinators = data["coordinators"]

        room_id         = call.data["room_id"]
        room_title      = call.data["room_title"]
        delay_min       = call.data["delay_min"]
        motion_entity   = call.data["motion_entity"]
        device_entities = call.data["device_entities"]

        await registry.async_register(
            room_id, room_title, delay_min, motion_entity, device_entities
        )

        if room_id in coordinators:
            # Cập nhật coordinator đang chạy — không cần tạo lại entities
            coord = coordinators[room_id]
            coord.update_config(room_title, delay_min, motion_entity, device_entities)
            _LOGGER.debug("Updated coordinator for room '%s'", room_title)
        else:
            # Phòng mới — tạo coordinator rồi thêm entities vào từng platform đang chạy
            room_data = registry.get(room_id)
            coord = _make_coordinator(hass, room_data)
            coordinators[room_id] = coord
            await coord.async_setup()

            # Thêm entities vào các platform đang chạy (không reload toàn bộ integration)
            platforms = async_get_platforms(hass, DOMAIN)
            for platform in platforms:
                if platform.config_entry.entry_id != entry.entry_id:
                    continue
                if platform.domain == "switch":
                    from .switch import AutoModeSwitch
                    await platform.async_add_entities([AutoModeSwitch(coord, entry.entry_id)])
                elif platform.domain == "number":
                    from .number import AutoDelayNumber
                    await platform.async_add_entities([AutoDelayNumber(coord, entry.entry_id)])
                elif platform.domain == "sensor":
                    from .sensor import RoomStatusSensor, RoomLastMotionSensor, RoomCountdownSensor
                    await platform.async_add_entities([
                        RoomStatusSensor(coord, entry.entry_id),
                        RoomLastMotionSensor(coord, entry.entry_id),
                        RoomCountdownSensor(coord, entry.entry_id),
                    ])
            _LOGGER.info("Created new room '%s' with entities", room_title)

    async def handle_unregister_room(call: ServiceCall) -> None:
        """Remove a room, its entities and device from Integration entries."""
        data         = _get_data()
        registry     = data["registry"]
        coordinators = data["coordinators"]

        room_id = call.data["room_id"]
        removed = await registry.async_unregister(room_id)
        if removed and room_id in coordinators:
            await coordinators[room_id].async_unload()
            del coordinators[room_id]

            # 1. Xoá entities khỏi entity registry, thu thập device_id liên quan
            import homeassistant.helpers.device_registry as dr
            ent_registry = er.async_get(hass)
            dev_registry = dr.async_get(hass)
            entries = er.async_entries_for_config_entry(ent_registry, entry.entry_id)
            device_ids_to_check: set = set()
            for e in entries:
                if e.unique_id.startswith(f"{room_id}_"):
                    if e.device_id:
                        device_ids_to_check.add(e.device_id)
                    ent_registry.async_remove(e.entity_id)

            # 2. Xoá device khỏi device registry nếu không còn entity nào
            for device_id in device_ids_to_check:
                remaining = [
                    e for e in er.async_entries_for_device(ent_registry, device_id)
                    if e.config_entry_id == entry.entry_id
                ]
                if not remaining:
                    dev_registry.async_remove_device(device_id)
                    _LOGGER.debug("Removed device %s for room %s", device_id, room_id)

            _LOGGER.info("Removed room id=%s (entities + device cleaned up)", room_id)

    async def handle_update_motion(call: ServiceCall) -> None:
        """
        Card calls this when it detects motion locally
        (fallback if user has no motion entity configured).
        """
        coordinators = _get_data()["coordinators"]
        room_id  = call.data["room_id"]
        detected = call.data["detected"]
        coord = coordinators.get(room_id)
        if coord:
            await coord._handle_motion(detected)

    async def handle_trigger_autooff(call: ServiceCall) -> None:
        """Immediately trigger auto-off for a room (card button or automation)."""
        coordinators = _get_data()["coordinators"]
        room_id = call.data["room_id"]
        coord = coordinators.get(room_id)
        if coord:
            await coord.async_trigger_autooff()

    hass.services.async_register(
        DOMAIN, SERVICE_REGISTER_ROOM,
        handle_register_room, schema=REGISTER_ROOM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UNREGISTER_ROOM,
        handle_unregister_room, schema=UNREGISTER_ROOM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_MOTION,
        handle_update_motion, schema=UPDATE_MOTION_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_TRIGGER_AUTOOFF,
        handle_trigger_autooff, schema=TRIGGER_AUTOOFF_SCHEMA
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_coordinator(hass: HomeAssistant, room_data: dict) -> RoomCoordinator:
    return RoomCoordinator(
        hass            = hass,
        room_id         = room_data["room_id"],
        room_title      = room_data["room_title"],
        delay_min       = room_data.get("delay_min", DEFAULT_DELAY_MIN),
        motion_entity   = room_data.get("motion_entity", ""),
        device_entities = room_data.get("device_entities", []),
    )


def get_coordinators(hass: HomeAssistant, entry_id: str) -> dict[str, RoomCoordinator]:
    """Helper used by platform modules to access coordinators."""
    return hass.data[DOMAIN][entry_id]["coordinators"]
