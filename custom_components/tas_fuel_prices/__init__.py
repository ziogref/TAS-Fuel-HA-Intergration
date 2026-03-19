"""The Tasmanian Fuel Prices integration."""
from __future__ import annotations

import random
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change, async_call_later
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
        model="1.0.3",
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

    # Coordinator for fetching trading hours (Custom scheduled below)
    trading_hours_coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=f"{DOMAIN}_trading_hours",
        update_method=api.fetch_trading_hours,
    )

    # Fetch initial data
    await price_coordinator.async_config_entry_first_refresh()
    await additional_data_coordinator.async_config_entry_first_refresh()
    await trading_hours_coordinator.async_config_entry_first_refresh()

    data_bundle = {
        "price_coordinator": price_coordinator,
        "additional_data_coordinator": additional_data_coordinator,
        "trading_hours_coordinator": trading_hours_coordinator,
        "api": api,
        "location_listener_cancel": None, # To hold the listener cancel callback
        "trading_hours_schedule_cancel": None,
        "trading_hours_timer_cancel": None,
    }
    hass.data[DOMAIN][entry.entry_id] = data_bundle

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up the location update listener
    async_setup_location_listener(hass, entry)

    # Set up the randomized 4-5 AM daily Trading Hours Refresh
    async def schedule_daily_update(now) -> None:
        delay = random.randint(0, 3600)
        LOGGER.debug("Scheduling trading hours update in %s seconds", delay)
        
        async def trigger_update(now) -> None:
            await trading_hours_coordinator.async_request_refresh()
            data_bundle["trading_hours_timer_cancel"] = None
            
        data_bundle["trading_hours_timer_cancel"] = async_call_later(hass, delay, trigger_update)

    data_bundle["trading_hours_schedule_cancel"] = async_track_time_change(
        hass, schedule_daily_update, hour=4, minute=0, second=0
    )

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
    # Cancel any active listeners or schedules
    if data_bundle := hass.data[DOMAIN].get(entry.entry_id):
        if data_bundle.get("location_listener_cancel"):
            data_bundle["location_listener_cancel"]()
        if data_bundle.get("trading_hours_schedule_cancel"):
            data_bundle["trading_hours_schedule_cancel"]()
        if data_bundle.get("trading_hours_timer_cancel"):
            data_bundle["trading_hours_timer_cancel"]()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)