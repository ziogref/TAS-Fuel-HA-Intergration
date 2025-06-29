"""Config flow for Tasmanian Fuel Prices."""
from __future__ import annotations

import voluptuous as vol
from typing import Any

from aiohttp import ClientError, ClientResponseError

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    LOGGER,
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_FUEL_TYPES,
    CONF_STATIONS,
    CONF_ENABLE_WOOLWORTHS_DISCOUNT,
    CONF_ENABLE_COLES_DISCOUNT,
    CONF_ENABLE_RACT_DISCOUNT,
    CONF_WOOLWORTHS_DISCOUNT_AMOUNT,
    CONF_WOOLWORTHS_ADDITIONAL_STATIONS,
    CONF_COLES_DISCOUNT_AMOUNT,
    CONF_COLES_ADDITIONAL_STATIONS,
    CONF_RACT_DISCOUNT_AMOUNT,
    CONF_RACT_ADDITIONAL_STATIONS,
    CONF_ADD_TYRE_INFLATION_STATIONS,
    CONF_REMOVE_TYRE_INFLATION_STATIONS,
)
from .api import TasFuelAPI

FUEL_TYPES_OPTIONS = ["U91", "E10", "P95", "P98", "DL", "PDL", "B20", "E85", "LPG"]


class TasFuelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tasmanian Fuel Prices."""

    VERSION = 6
    data: dict[str, Any] = {}
    options: dict[str, Any] = {}


    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the initial authentication step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = TasFuelAPI(
                user_input[CONF_API_KEY], user_input[CONF_API_SECRET], session
            )
            try:
                await api._get_access_token()
            except (ClientError, ClientResponseError):
                errors["base"] = "auth_error"
            except Exception:
                LOGGER.exception("Unexpected exception during auth test")
                errors["base"] = "unknown_error"
            else:
                self.data.update(user_input)
                return await self.async_step_init_options()

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_API_SECRET): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_init_options(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the main options step."""
        if user_input is not None:
            stations_str = user_input.get(CONF_STATIONS, "")
            stations_list = [
                s.strip() for s in stations_str.split(",") if s.strip().isdigit()
            ]
            self.options.update(user_input)
            self.options[CONF_STATIONS] = stations_list

            if self.options.get(CONF_ENABLE_WOOLWORTHS_DISCOUNT):
                return await self.async_step_woolworths_discount()
            if self.options.get(CONF_ENABLE_COLES_DISCOUNT):
                return await self.async_step_coles_discount()
            if self.options.get(CONF_ENABLE_RACT_DISCOUNT):
                return await self.async_step_ract_discount()

            return await self.async_step_tyre_inflation()

        schema = vol.Schema(
            {
                vol.Required(CONF_FUEL_TYPES, default=["U91"]): cv.multi_select(
                    FUEL_TYPES_OPTIONS
                ),
                vol.Optional(CONF_STATIONS, default=""): str,
                vol.Optional(CONF_ENABLE_WOOLWORTHS_DISCOUNT, default=False): bool,
                vol.Optional(CONF_ENABLE_COLES_DISCOUNT, default=False): bool,
                vol.Optional(CONF_ENABLE_RACT_DISCOUNT, default=False): bool,
            }
        )
        return self.async_show_form(step_id="init_options", data_schema=schema)

    async def async_step_woolworths_discount(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle Woolworths discount options."""
        if user_input is not None:
            self.options.update(user_input)
            if self.options.get(CONF_ENABLE_COLES_DISCOUNT):
                return await self.async_step_coles_discount()
            if self.options.get(CONF_ENABLE_RACT_DISCOUNT):
                return await self.async_step_ract_discount()
            return await self.async_step_tyre_inflation()

        schema = vol.Schema({
            vol.Required(CONF_WOOLWORTHS_DISCOUNT_AMOUNT, default=6): int,
            vol.Optional(CONF_WOOLWORTHS_ADDITIONAL_STATIONS, default=""): str,
        })
        return self.async_show_form(step_id="woolworths_discount", data_schema=schema)

    async def async_step_coles_discount(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle Coles discount options."""
        if user_input is not None:
            self.options.update(user_input)
            if self.options.get(CONF_ENABLE_RACT_DISCOUNT):
                return await self.async_step_ract_discount()
            return await self.async_step_tyre_inflation()

        schema = vol.Schema({
            vol.Required(CONF_COLES_DISCOUNT_AMOUNT, default=4): int,
            vol.Optional(CONF_COLES_ADDITIONAL_STATIONS, default=""): str,
        })
        return self.async_show_form(step_id="coles_discount", data_schema=schema)

    async def async_step_ract_discount(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle RACT discount options."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_tyre_inflation()

        schema = vol.Schema({
            vol.Required(CONF_RACT_DISCOUNT_AMOUNT, default=6): int,
            vol.Optional(CONF_RACT_ADDITIONAL_STATIONS, default=""): str,
        })
        return self.async_show_form(step_id="ract_discount", data_schema=schema)

    async def async_step_tyre_inflation(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle Tyre Inflation override options."""
        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(title="Tasmanian Fuel Prices", data=self.data, options=self.options)

        schema = vol.Schema({
            vol.Optional(CONF_ADD_TYRE_INFLATION_STATIONS, default=""): str,
            vol.Optional(CONF_REMOVE_TYRE_INFLATION_STATIONS, default=""): str,
        })
        return self.async_show_form(step_id="tyre_inflation", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler (for re-configuration)."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    """Handle an options flow for re-configuring."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Manage the options."""
        if user_input is not None:
            stations_str = user_input.get(CONF_STATIONS, "")
            stations_list = [
                s.strip() for s in stations_str.split(",") if s.strip().isdigit()
            ]
            self.options.update(user_input)
            self.options[CONF_STATIONS] = stations_list

            if self.options.get(CONF_ENABLE_WOOLWORTHS_DISCOUNT):
                return await self.async_step_woolworths_discount()
            if self.options.get(CONF_ENABLE_COLES_DISCOUNT):
                return await self.async_step_coles_discount()
            if self.options.get(CONF_ENABLE_RACT_DISCOUNT):
                return await self.async_step_ract_discount()
            
            return await self.async_step_tyre_inflation()

        schema = vol.Schema({
                vol.Required(CONF_FUEL_TYPES, default=self.options.get(CONF_FUEL_TYPES, ["U91"])): cv.multi_select(
                    FUEL_TYPES_OPTIONS
                ),
                vol.Optional(CONF_STATIONS, description={"suggested_value": ",".join(map(str, self.options.get(CONF_STATIONS, [])))}): str,
                vol.Optional(CONF_ENABLE_WOOLWORTHS_DISCOUNT, default=self.options.get(CONF_ENABLE_WOOLWORTHS_DISCOUNT, False)): bool,
                vol.Optional(CONF_ENABLE_COLES_DISCOUNT, default=self.options.get(CONF_ENABLE_COLES_DISCOUNT, False)): bool,
                vol.Optional(CONF_ENABLE_RACT_DISCOUNT, default=self.options.get(CONF_ENABLE_RACT_DISCOUNT, False)): bool,
        })
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_woolworths_discount(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle Woolworths discount options for re-configuration."""
        if user_input is not None:
            self.options.update(user_input)
            if self.options.get(CONF_ENABLE_COLES_DISCOUNT):
                return await self.async_step_coles_discount()
            if self.options.get(CONF_ENABLE_RACT_DISCOUNT):
                return await self.async_step_ract_discount()
            return await self.async_step_tyre_inflation()

        schema = vol.Schema({
            vol.Required(CONF_WOOLWORTHS_DISCOUNT_AMOUNT, default=self.options.get(CONF_WOOLWORTHS_DISCOUNT_AMOUNT, 6)): int,
            vol.Optional(CONF_WOOLWORTHS_ADDITIONAL_STATIONS, description={"suggested_value": self.options.get(CONF_WOOLWORTHS_ADDITIONAL_STATIONS, "")}): str,
        })
        return self.async_show_form(step_id="woolworths_discount", data_schema=schema)

    async def async_step_coles_discount(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle Coles discount options for re-configuration."""
        if user_input is not None:
            self.options.update(user_input)
            if self.options.get(CONF_ENABLE_RACT_DISCOUNT):
                return await self.async_step_ract_discount()
            return await self.async_step_tyre_inflation()

        schema = vol.Schema({
            vol.Required(CONF_COLES_DISCOUNT_AMOUNT, default=self.options.get(CONF_COLES_DISCOUNT_AMOUNT, 4)): int,
            vol.Optional(CONF_COLES_ADDITIONAL_STATIONS, description={"suggested_value": self.options.get(CONF_COLES_ADDITIONAL_STATIONS, "")}): str,
        })
        return self.async_show_form(step_id="coles_discount", data_schema=schema)

    async def async_step_ract_discount(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle RACT discount options for re-configuration."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_tyre_inflation()

        schema = vol.Schema({
            vol.Required(CONF_RACT_DISCOUNT_AMOUNT, default=self.options.get(CONF_RACT_DISCOUNT_AMOUNT, 6)): int,
            vol.Optional(CONF_RACT_ADDITIONAL_STATIONS, description={"suggested_value": self.options.get(CONF_RACT_ADDITIONAL_STATIONS, "")}): str,
        })
        return self.async_show_form(step_id="ract_discount", data_schema=schema)

    async def async_step_tyre_inflation(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle Tyre Inflation override options for re-configuration."""
        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(title="", data=self.options)

        schema = vol.Schema({
            vol.Optional(CONF_ADD_TYRE_INFLATION_STATIONS, description={"suggested_value": self.options.get(CONF_ADD_TYRE_INFLATION_STATIONS, "")}): str,
            vol.Optional(CONF_REMOVE_TYRE_INFLATION_STATIONS, description={"suggested_value": self.options.get(CONF_REMOVE_TYRE_INFLATION_STATIONS, "")}): str,
        })
        return self.async_show_form(step_id="tyre_inflation", data_schema=schema)
