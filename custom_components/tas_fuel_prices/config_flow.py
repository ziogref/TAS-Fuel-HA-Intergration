"""Config flow for Tasmanian Fuel Prices."""
from __future__ import annotations

import voluptuous as vol
from typing import Any

from aiohttp import ClientError, ClientResponseError

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    LOGGER,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_FUEL_TYPE,
    CONF_STATIONS,
)
from .api import TasFuelAPI

# Available fuel types from the API documentation
FUEL_TYPES = ["U91", "E10", "P95", "P98", "DL", "PDL", "B20", "E85", "LPG"]


class TasFuelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tasmanian Fuel Prices."""

    VERSION = 1
    data: dict[str, Any]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the initial authentication step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = TasFuelAPI(
                user_input[CONF_CLIENT_ID], user_input[CONF_CLIENT_SECRET], session
            )
            try:
                # Test credentials by fetching a token
                await api._get_access_token()
            except (ClientError, ClientResponseError):
                errors["base"] = "auth_error"
            except Exception:
                LOGGER.exception("Unexpected exception during auth test")
                errors["base"] = "unknown_error"
            else:
                # Auth is valid, store the data and proceed to the options step
                self.data = user_input
                return await self.async_step_options()

        # Show the form to the user
        schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the options step during initial setup."""
        if user_input is not None:
            # Combine the auth data with the options and create the entry
            stations_str = user_input.get(CONF_STATIONS, "")
            stations_list = [
                s.strip() for s in stations_str.split(",") if s.strip().isdigit()
            ]
            options_data = {
                CONF_FUEL_TYPE: user_input[CONF_FUEL_TYPE],
                CONF_STATIONS: stations_list[:5],
            }
            return self.async_create_entry(
                title="Tasmanian Fuel Prices", data=self.data, options=options_data
            )

        # Show the options form
        schema = vol.Schema(
            {
                vol.Required(CONF_FUEL_TYPE, default="U91"): vol.In(FUEL_TYPES),
                vol.Optional(CONF_STATIONS, default=""): str,
            }
        )
        return self.async_show_form(step_id="options", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler (for re-configuration)."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    """Handle a options flow for re-configuring."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Manage the options."""
        if user_input is not None:
            stations_str = user_input.get(CONF_STATIONS, "")
            stations_list = [
                s.strip() for s in stations_str.split(",") if s.strip().isdigit()
            ]
            user_input[CONF_STATIONS] = stations_list[:5]
            return self.async_create_entry(title="", data=user_input)

        current_fuel_type = self.config_entry.options.get(CONF_FUEL_TYPE, "U91")
        current_stations = self.config_entry.options.get(CONF_STATIONS, [])

        schema = vol.Schema(
            {
                vol.Required(CONF_FUEL_TYPE, default=current_fuel_type): vol.In(FUEL_TYPES),
                vol.Optional(
                    CONF_STATIONS,
                    description={"suggested_value": ",".join(map(str, current_stations))},
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
