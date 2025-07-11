"""The Tasmanian Fuel Prices integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import TasFuelAPI
from .const import (
    DOMAIN,
    LOGGER,
    SCAN_INTERVAL,
    ADDITIONAL_DATA_UPDATE_INTERVAL,
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_DEVICE_NAME,
)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tasmanian Fuel Prices from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    device_registry = dr.async_get(hass)
    # Get the main device entry
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=CONF_DEVICE_NAME,
        manufacturer="Custom Integration",
        model="1.4.0", # Version bump
    )

    session = async_get_clientsession(hass)
    api = TasFuelAPI(
        entry.data[CONF_API_KEY],
        entry.data[CONF_API_SECRET],
        session,
    )

    # Coordinator for fetching fuel prices from the API
    price_coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=f"{DOMAIN}_prices",
        update_method=api.fetch_prices,
        update_interval=SCAN_INTERVAL,
    )

    # Coordinator for fetching discount/amenity station lists from GitHub
    additional_data_coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=f"{DOMAIN}_additional_data",
        update_method=api.fetch_additional_data_lists,
        update_interval=ADDITIONAL_DATA_UPDATE_INTERVAL,
    )

    # Fetch initial data
    await price_coordinator.async_config_entry_first_refresh()
    await additional_data_coordinator.async_config_entry_first_refresh()


    hass.data[DOMAIN][entry.entry_id] = {
        "price_coordinator": price_coordinator,
        "additional_data_coordinator": additional_data_coordinator,
        "api": api,
    }

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
