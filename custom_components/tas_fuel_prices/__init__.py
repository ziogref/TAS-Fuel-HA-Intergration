"""The Tasmanian Fuel Prices integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.dispatcher import dispatcher_send


from .api import TasFuelAPI
from .const import (
    DOMAIN,
    LOGGER,
    SCAN_INTERVAL,
    ADDITIONAL_DATA_UPDATE_INTERVAL,
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_DEVICE_NAME,
    CONF_LOCATION_ENTITY,
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
        model="1.7.0", # Version bump
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

    data_bundle = {
        "price_coordinator": price_coordinator,
        "additional_data_coordinator": additional_data_coordinator,
        "api": api,
        "location_listener_cancel": None, # To hold the listener cancel callback
    }
    hass.data[DOMAIN][entry.entry_id] = data_bundle

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up the location update listener
    async_setup_location_listener(hass, entry)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

def async_setup_location_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a listener to recalculate distance when the location entity changes."""
    location_entity_id = entry.options.get(CONF_LOCATION_ENTITY)
    if not location_entity_id:
        LOGGER.info("No location entity configured. Skipping location listener setup.")
        return

    data_bundle = hass.data[DOMAIN][entry.entry_id]

    async def location_state_listener(event: Event) -> None:
        """Handle state changes for the location entity."""
        LOGGER.debug("Location entity %s changed, dispatching distance recalculation.", location_entity_id)
        dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_recalculate_distance")

    # Register the state change listener
    cancel_listener = async_track_state_change_event(
        hass, [location_entity_id], location_state_listener
    )
    data_bundle["location_listener_cancel"] = cancel_listener
    
    # Trigger an initial calculation right after setup
    dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_recalculate_distance")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Cancel the location listener if it's running
    if (
        data_bundle := hass.data[DOMAIN].get(entry.entry_id)
    ) and data_bundle.get("location_listener_cancel"):
        data_bundle["location_listener_cancel"]()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
