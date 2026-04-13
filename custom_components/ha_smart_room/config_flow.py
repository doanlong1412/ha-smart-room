"""Config flow for HA Smart Room — single-step, no user input required."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class HASmartRoomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Config flow: user clicks Submit — no fields needed.
    The integration auto-discovers rooms as cards register themselves.
    """

    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Only one instance of this integration is allowed
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="HA Smart Room", data={})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "Click Submit — rooms are registered automatically by the card."
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HASmartRoomOptionsFlow(config_entry)


class HASmartRoomOptionsFlow(config_entries.OptionsFlow):
    """Options flow — nothing to configure here; rooms are managed by the card."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
