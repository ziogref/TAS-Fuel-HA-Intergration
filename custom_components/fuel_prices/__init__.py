"""The Tasmanian Fuel Prices integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import TasFuelAPI
from .const import DOMAIN, LOGGER, SCAN_INTERVAL, CONF_API_KEY, CONF_API_SECRET, CONF_DEVICE_NAME

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tasmanian Fuel Prices from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create a device for all entities to be grouped under
    device_registry = hass.helpers.device_registry.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        device_info=DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=CONF_DEVICE_NAME,
            manufacturer="Custom Integration",
            model="v1.0.3",
        ),
    )

    session = async_get_clientsession(hass)
    api = TasFuelAPI(
        entry.data[CONF_API_KEY],
        entry.data[CONF_API_SECRET],
        session,
    )

    coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=DOMAIN,
        update_method=api.fetch_prices,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
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
