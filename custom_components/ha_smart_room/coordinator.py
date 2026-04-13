"""
HA Smart Room — Room Coordinator
Runs server-side auto-off logic for a single room.
One coordinator instance per room.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_DELAY_MIN,
    STATUS_COUNTDOWN,
    STATUS_IDLE,
    STATUS_OCCUPIED,
    STATUS_TRIGGERED,
)

_LOGGER = logging.getLogger(__name__)


class RoomCoordinator:
    """
    Brain for one room.

    Responsibilities:
    - Track motion sensor state changes
    - Run countdown timer when room becomes empty
    - Call turn_off on all configured device entities when countdown expires
    - Expose state properties consumed by switch / number / sensor entities
    """

    def __init__(
        self,
        hass: HomeAssistant,
        room_id: str,
        room_title: str,
        delay_min: int,
        motion_entity: str,
        device_entities: list[str],
    ) -> None:
        self.hass            = hass
        self.room_id         = room_id
        self.room_title      = room_title
        self.delay_min       = delay_min
        self.motion_entity   = motion_entity
        self.device_entities = list(device_entities)

        # Runtime state
        self._auto_enabled:   bool                = False
        self._status:         str                 = STATUS_IDLE
        self._last_motion_at: datetime | None     = None
        self._countdown_end:  datetime | None     = None
        self._countdown_task: asyncio.Task | None = None
        self._unsub_motion:   Callable | None     = None

        # Listeners — entities register here to get notified on state changes
        self._listeners: list[Callable] = []

    # ── Public properties ──────────────────────────────────────────────────────

    @property
    def auto_enabled(self) -> bool:
        return self._auto_enabled

    @property
    def status(self) -> str:
        return self._status

    @property
    def last_motion_at(self) -> datetime | None:
        return self._last_motion_at

    @property
    def countdown_remaining_seconds(self) -> int | None:
        if self._countdown_end is None:
            return None
        remaining = (self._countdown_end - dt_util.utcnow()).total_seconds()
        return max(0, int(remaining))

    # ── Listener pattern ───────────────────────────────────────────────────────

    def async_add_listener(self, cb: Callable) -> Callable:
        """Register a listener; returns an unsubscribe callable."""
        self._listeners.append(cb)

        def _remove() -> None:
            try:
                self._listeners.remove(cb)
            except ValueError:
                pass

        return _remove

    @callback
    def _notify_listeners(self) -> None:
        for cb in list(self._listeners):
            cb()

    # ── Setup / Teardown ───────────────────────────────────────────────────────

    async def async_setup(self) -> None:
        """Start tracking the configured motion sensor."""
        self._subscribe_motion()
        _LOGGER.debug("Coordinator setup for room '%s'", self.room_title)

    async def async_unload(self) -> None:
        """Stop tracking and cancel any running countdown."""
        self._unsubscribe_motion()
        self._cancel_countdown()
        _LOGGER.debug("Coordinator unloaded for room '%s'", self.room_title)

    # ── Auto mode (called by switch entity) ────────────────────────────────────

    async def async_set_auto(self, enabled: bool) -> None:
        """Enable or disable auto-off mode."""
        if self._auto_enabled == enabled:
            return
        self._auto_enabled = enabled
        _LOGGER.info(
            "Room '%s' auto-off → %s", self.room_title, "ON" if enabled else "OFF"
        )

        if not enabled:
            self._cancel_countdown()
            self._set_status(STATUS_IDLE)
        else:
            state = (
                self.hass.states.get(self.motion_entity)
                if self.motion_entity
                else None
            )
            if state and state.state == "on":
                self._set_status(STATUS_OCCUPIED)
            else:
                await self._start_countdown()

        self._notify_listeners()

    # ── Delay (called by number entity) ────────────────────────────────────────

    async def async_set_delay(self, minutes: int) -> None:
        """Update the auto-off delay; restarts countdown if it is running."""
        self.delay_min = max(1, int(minutes))
        _LOGGER.debug("Room '%s' delay → %d min", self.room_title, self.delay_min)
        if self._status == STATUS_COUNTDOWN:
            self._cancel_countdown()
            await self._start_countdown()
        self._notify_listeners()

    # ── Manual trigger ─────────────────────────────────────────────────────────

    async def async_trigger_autooff(self) -> None:
        """Immediately turn off all devices (called by card or automation)."""
        await self._execute_autooff()

    # ── Public motion update (called by service handler) ──────────────────────

    async def async_update_motion(self, detected: bool) -> None:
        """Handle a software motion event from the card service."""
        await self._handle_motion(detected)

    # ── Motion handler ─────────────────────────────────────────────────────────

    @callback
    def _on_motion_change(self, event: Any) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        self.hass.async_create_task(self._handle_motion(new_state.state == "on"))

    async def _handle_motion(self, detected: bool) -> None:
        if detected:
            self._last_motion_at = dt_util.utcnow()
            self._cancel_countdown()
            self._set_status(STATUS_OCCUPIED)
            _LOGGER.debug("Room '%s': motion detected", self.room_title)
        else:
            _LOGGER.debug("Room '%s': motion cleared", self.room_title)
            if self._auto_enabled:
                await self._start_countdown()
            else:
                self._set_status(STATUS_IDLE)
        self._notify_listeners()

    # ── Countdown ──────────────────────────────────────────────────────────────

    async def _start_countdown(self) -> None:
        self._cancel_countdown()
        delay_secs = self.delay_min * 60
        self._countdown_end = dt_util.utcnow() + timedelta(seconds=delay_secs)
        self._set_status(STATUS_COUNTDOWN)
        self._notify_listeners()
        _LOGGER.info(
            "Room '%s': countdown started — %d min until auto-off",
            self.room_title,
            self.delay_min,
        )
        self._countdown_task = self.hass.async_create_task(
            self._countdown_worker(delay_secs)
        )

    async def _countdown_worker(self, delay_secs: float) -> None:
        """Sleep in 30-second ticks, notifying listeners for UI updates."""
        elapsed = 0.0
        tick    = 30.0
        while elapsed < delay_secs:
            sleep_for = min(tick, delay_secs - elapsed)
            await asyncio.sleep(sleep_for)
            elapsed += sleep_for          # ← use actual sleep duration, not tick
            self._notify_listeners()      # update remaining-seconds sensor
        await self._execute_autooff()

    def _cancel_countdown(self) -> None:
        if self._countdown_task and not self._countdown_task.done():
            self._countdown_task.cancel()
        self._countdown_task = None
        self._countdown_end  = None

    # ── Execute auto-off ────────────────────────────────────────────────────────

    async def _execute_autooff(self) -> None:
        """Turn off all configured device entities."""
        self._cancel_countdown()
        self._set_status(STATUS_TRIGGERED)
        self._notify_listeners()

        for entity_id in self.device_entities:
            domain = entity_id.split(".")[0]
            try:
                await self.hass.services.async_call(
                    domain,
                    "turn_off",
                    {"entity_id": entity_id},
                    blocking=False,
                )
                _LOGGER.debug("Auto-off: turned off %s", entity_id)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "Auto-off: failed to turn off %s — %s", entity_id, exc
                )

        _LOGGER.info(
            "Room '%s': auto-off executed (%d device(s))",
            self.room_title,
            len(self.device_entities),
        )

        # Brief pause so the "triggered" state is visible before resetting
        await asyncio.sleep(2)
        self._set_status(STATUS_IDLE)
        self._notify_listeners()

    # ── Motion subscription helpers ────────────────────────────────────────────

    def _subscribe_motion(self) -> None:
        """Subscribe to the current motion_entity, reading its initial state."""
        self._unsubscribe_motion()
        if not self.motion_entity:
            return
        self._unsub_motion = async_track_state_change_event(
            self.hass, [self.motion_entity], self._on_motion_change
        )
        state = self.hass.states.get(self.motion_entity)
        if state and state.state == "on":
            self._set_status(STATUS_OCCUPIED)
            self._last_motion_at = dt_util.utcnow()

    def _unsubscribe_motion(self) -> None:
        if self._unsub_motion:
            self._unsub_motion()
            self._unsub_motion = None

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _set_status(self, status: str) -> None:
        self._status = status

    async def update_config(
        self,
        room_title: str,
        delay_min: int,
        motion_entity: str,
        device_entities: list[str],
    ) -> None:
        """
        Hot-update config without a full integration reload.

        Re-subscribes the motion listener when motion_entity changes so the
        coordinator always tracks the correct sensor.
        """
        motion_changed = self.motion_entity != motion_entity

        self.room_title      = room_title
        self.delay_min       = max(1, int(delay_min))
        self.motion_entity   = motion_entity
        self.device_entities = list(device_entities)

        if motion_changed:
            # Unsubscribe old sensor, subscribe new one
            self._subscribe_motion()
            _LOGGER.debug(
                "Room '%s': motion entity updated to '%s'", room_title, motion_entity
            )

        self._notify_listeners()
