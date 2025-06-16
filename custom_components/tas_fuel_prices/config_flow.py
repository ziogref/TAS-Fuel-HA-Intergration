"""Config flow for Tasmanian Fuel Prices."""
from __future__ import annotations

import voluptuous as vol
from typing import Any

from aiohttp import ClientError, ClientSession, ClientResponseError

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_CLIENT_SECRET
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    LOGGER,
    CONF_CLIENT_ID,
    CONF_FUEL_TYPE,
    CONF_STATIONS,
)
from .api import TasFuelAPI

# Available fuel types from the API documentation
# You can expand this list if needed
FUEL_TYPES = ["U91", "E10", "P95", "P98", "DL", "PDL", "B20", "E85", "LPG"]


class TasFuelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tasmanian Fuel Prices."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the initial step."""
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
                # We store the credentials and create the entry
                return self.async_create_entry(
                    title="Tasmanian Fuel Prices", data=user_input
                )

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
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    """Handle an options flow for Tasmanian Fuel Prices."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Manage the options."""
        if user_input is not None:
            # The station codes should be a comma-separated string
            # We split them into a list of integers
            stations_str = user_input.get(CONF_STATIONS, "")
            stations_list = [
                s.strip() for s in stations_str.split(",") if s.strip().isdigit()
            ]
            
            # Limit to 5 favorite stations
            user_input[CONF_STATIONS] = stations_list[:5]

            return self.async_create_entry(title="", data=user_input)

        # Get current options
        current_fuel_type = self.config_entry.options.get(CONF_FUEL_TYPE, "U91")
        current_stations = self.config_entry.options.get(CONF_STATIONS, [])

        schema = vol.Schema(
            {
                vol.Required(CONF_FUEL_TYPE, default=current_fuel_type): vol.In(FUEL_TYPES),
                vol.Optional(
                    CONF_STATIONS,
                    description={"suggested_value": ",".join(current_stations)},
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

