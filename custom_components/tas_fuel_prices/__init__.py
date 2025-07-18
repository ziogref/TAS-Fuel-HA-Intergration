"""The Tasmanian Fuel Prices integration."""
from __future__ import annotations
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, EVENT_HOMEASSISTANT_STOP, STATE_ON
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
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
        model="1.5.0", # Version bump
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
        "aa_interval_cancel": None, # For Android Auto rapid updates
    }
    hass.data[DOMAIN][entry.entry_id] = data_bundle

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up the Android Auto fast-update listener
    await async_setup_android_auto_listener(hass, entry)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_setup_android_auto_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a listener to enable rapid distance updates when Android Auto is active."""
    location_entity_id = entry.options.get(CONF_LOCATION_ENTITY)
    if not location_entity_id:
        return

    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get(location_entity_id)

    if not entity_entry or not entity_entry.device_id:
        return

    # Find the Android Auto sensor associated with the same device
    android_auto_sensor_id = None
    device_entities = er.async_entries_for_device(ent_reg, entity_entry.device_id)
    for device_entity in device_entities:
        if (
            device_entity.platform == "mobile_app"
            and device_entity.domain == "binary_sensor"
            and device_entity.entity_id.endswith("_android_auto")
        ):
            android_auto_sensor_id = device_entity.entity_id
            LOGGER.info("Found Android Auto sensor: %s", android_auto_sensor_id)
            break
    
    if not android_auto_sensor_id:
        LOGGER.info("No Android Auto sensor found for device of %s", location_entity_id)
        return
        
    data_bundle = hass.data[DOMAIN][entry.entry_id]

    def _start_aa_interval():
        """Start the 1-minute update interval."""
        if data_bundle["aa_interval_cancel"] is None:
            LOGGER.info("Android Auto active. Starting 1-minute distance updates.")
            recalculate_callback = lambda *_: dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_recalculate_distance")
            data_bundle["aa_interval_cancel"] = async_track_time_interval(
                hass, recalculate_callback, timedelta(minutes=1)
            )
            # Immediately trigger a recalculation
            recalculate_callback()

    def _stop_aa_interval():
        """Stop the 1-minute update interval."""
        if data_bundle["aa_interval_cancel"]:
            LOGGER.info("Android Auto inactive. Stopping 1-minute distance updates.")
            data_bundle["aa_interval_cancel"]()
            data_bundle["aa_interval_cancel"] = None

    async def android_auto_state_listener(event: Event) -> None:
        """Handle state changes for the Android Auto sensor."""
        new_state = event.data.get("new_state")
        if new_state and new_state.state == STATE_ON:
            _start_aa_interval()
        else:
            _stop_aa_interval()

    # Register the state change listener
    entry.async_on_unload(
        async_track_state_change_event(
            hass, [android_auto_sensor_id], android_auto_state_listener
        )
    )

    # Check the initial state of the sensor when setting up
    if (aa_state := hass.states.get(android_auto_sensor_id)) and aa_state.state == STATE_ON:
        _start_aa_interval()

    # Ensure the interval is cancelled on shutdown
    async def _stop_on_shutdown(event):
        _stop_aa_interval()
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop_on_shutdown)
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Cancel the Android Auto interval timer if it's running
    if (
        data_bundle := hass.data[DOMAIN].get(entry.entry_id)
    ) and data_bundle["aa_interval_cancel"]:
        data_bundle["aa_interval_cancel"]()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
