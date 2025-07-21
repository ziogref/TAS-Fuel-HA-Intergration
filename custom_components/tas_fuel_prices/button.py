"""Button platform for Tasmanian Fuel Prices."""
from __future__ import annotations
import urllib.parse

from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant, ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er, device_registry as dr

from .api import TasFuelAPI
from .const import (
    DOMAIN,
    CONF_DEVICE_NAME,
    CONF_FUEL_TYPES,
    CONF_LOCATION_ENTITY,
    ATTR_STATIONS,
    ATTR_TYRE_INFLATION,
    ATTR_ADDRESS,
    LOGGER,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    data_bundle = hass.data[DOMAIN][entry.entry_id]
    price_coordinator: DataUpdateCoordinator = data_bundle["price_coordinator"]
    additional_data_coordinator: DataUpdateCoordinator = data_bundle["additional_data_coordinator"]
    api_client: TasFuelAPI = data_bundle["api"]

    buttons = [
        TasFuelRefreshTokenButton(price_coordinator, api_client),
        TasFuelRefreshPricesButton(price_coordinator),
        TasFuelRefreshAdditionalDataButton(price_coordinator, additional_data_coordinator),
    ]

    # Create navigation buttons if a location entity is configured
    if entry.options.get(CONF_LOCATION_ENTITY):
        fuel_types = entry.options.get(CONF_FUEL_TYPES, [])
        for fuel_type in fuel_types:
            buttons.append(
                NavigateToCheapestButton(hass, entry, fuel_type)
            )
            buttons.append(
                NavigateToCheapestTyreButton(hass, entry, fuel_type)
            )

    async_add_entities(buttons)


class TasFuelRefreshTokenButton(ButtonEntity):
    """Representation of a button to force a token refresh."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DataUpdateCoordinator, api_client: TasFuelAPI) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self._api_client = api_client
        self._attr_name = "Refresh Access Token"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_refresh_token"
        self._attr_icon = "mdi:key-refresh"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this button is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name=CONF_DEVICE_NAME,
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api_client.force_refresh_token()
        await self.coordinator.async_request_refresh()


class TasFuelRefreshPricesButton(ButtonEntity):
    """Representation of a button to manually refresh prices."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self._attr_name = "Refresh Fuel Prices"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_refresh_prices"
        self._attr_icon = "mdi:update"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this button is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name=CONF_DEVICE_NAME,
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_request_refresh()


class TasFuelRefreshAdditionalDataButton(ButtonEntity):
    """Representation of a button to manually refresh additional data from GitHub."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, price_coordinator: DataUpdateCoordinator, additional_data_coordinator: DataUpdateCoordinator) -> None:
        """Initialize the button."""
        self.price_coordinator = price_coordinator
        self.additional_data_coordinator = additional_data_coordinator
        self._attr_name = "Refresh Discount & Amenity Data"
        self._attr_unique_id = f"{price_coordinator.config_entry.entry_id}_refresh_additional_data"
        self._attr_icon = "mdi:download"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this button is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.price_coordinator.config_entry.entry_id)},
            name=CONF_DEVICE_NAME,
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.additional_data_coordinator.async_request_refresh()
        await self.price_coordinator.async_request_refresh()


class BaseNavigateButton(ButtonEntity):
    """Base class for navigation buttons."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        fuel_type: str,
    ) -> None:
        """Initialize the navigation button."""
        self.hass = hass
        self.entry = entry
        self._fuel_type = fuel_type
        self._attr_icon = "mdi:google-maps"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this button is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_{self._fuel_type}")},
            name=f"{CONF_DEVICE_NAME} - {self._fuel_type}",
            manufacturer="Custom Integration",
            via_device=(DOMAIN, self.entry.entry_id),
        )
    
    async def _get_notification_service(self) -> str | None:
        """Dynamically find the notification service for the tracked device."""
        location_entity_id = self.entry.options.get(CONF_LOCATION_ENTITY)
        if not location_entity_id:
            LOGGER.error("Navigation button pressed, but no location entity is configured.")
            return None

        ent_reg = er.async_get(self.hass)
        entity_entry = ent_reg.async_get(location_entity_id)
        if not entity_entry or not entity_entry.device_id:
            LOGGER.error(
                "Could not find a device linked to the location entity: %s",
                location_entity_id,
            )
            return None

        dev_reg = dr.async_get(self.hass)
        device = dev_reg.async_get(entity_entry.device_id)
        if not device:
            LOGGER.error("Could not find device with ID: %s", entity_entry.device_id)
            return None

        # Construct the expected service name from the device name
        service_name = f"mobile_app_{device.name.lower().replace(' ', '_')}"
        if self.hass.services.has_service("notify", service_name):
            return f"notify.{service_name}"
        
        LOGGER.error(
            "Found device '%s', but could not find the corresponding notification service 'notify.%s'",
            device.name,
            service_name,
        )
        return None


    async def _get_station_address(self, tyre_inflation_required: bool) -> str | None:
        """Get the address of the desired station from the summary sensor."""
        registry = er.async_get(self.hass)
        summary_sensor_unique_id = f"{self.entry.entry_id}_{self._fuel_type}_cheapest_filtered"
        summary_sensor_entity_id = registry.async_get_entity_id(
            SENSOR_DOMAIN, DOMAIN, summary_sensor_unique_id
        )

        if not summary_sensor_entity_id:
            LOGGER.warning(
                "Could not find summary sensor with unique_id: %s",
                summary_sensor_unique_id,
            )
            return None

        sensor_state = self.hass.states.get(summary_sensor_entity_id)
        if not sensor_state or not sensor_state.attributes.get(ATTR_STATIONS):
            LOGGER.warning(
                "Summary sensor %s has no state or station data.",
                summary_sensor_entity_id,
            )
            return None

        stations = sensor_state.attributes[ATTR_STATIONS]
        target_station = None

        if not tyre_inflation_required:
            target_station = stations[0] if stations else None
        else:
            target_station = next(
                (s for s in stations if s.get(ATTR_TYRE_INFLATION)), None
            )

        if not target_station:
            LOGGER.warning(
                "No suitable station found for navigation (Tyre Inflation Required: %s)",
                tyre_inflation_required,
            )
            return None

        return target_station.get(ATTR_ADDRESS)

    async def async_press(self) -> None:
        """This method should be implemented by subclasses."""
        raise NotImplementedError


class NavigateToCheapestButton(BaseNavigateButton):
    """Button to navigate to the cheapest station."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attr_name = f"Navigate to Cheapest {self._fuel_type}"
        self._attr_unique_id = f"{self.entry.entry_id}_navigate_cheapest_{self._fuel_type}"

    async def async_press(self) -> None:
        """Handle the button press and send notification."""
        address = await self._get_station_address(tyre_inflation_required=False)
        notification_service = await self._get_notification_service()

        if address and notification_service:
            uri = f"google.navigation:q={urllib.parse.quote(address)}"
            service_domain, service_name = notification_service.split(".")
            
            await self.hass.services.async_call(
                service_domain,
                service_name,
                {"message": "command_launch_uri", "data": {"uri": uri}},
                blocking=True,
            )


class NavigateToCheapestTyreButton(BaseNavigateButton):
    """Button to navigate to the cheapest station with tyre inflation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attr_name = f"Navigate to Cheapest {self._fuel_type} (Tyres)"
        self._attr_unique_id = f"{self.entry.entry_id}_navigate_cheapest_tyre_{self._fuel_type}"

    async def async_press(self) -> None:
        """Handle the button press and send notification."""
        address = await self._get_station_address(tyre_inflation_required=True)
        notification_service = await self._get_notification_service()

        if address and notification_service:
            uri = f"google.navigation:q={urllib.parse.quote(address)}"
            service_domain, service_name = notification_service.split(".")
            
            await self.hass.services.async_call(
                service_domain,
                service_name,
                {"message": "command_launch_uri", "data": {"uri": uri}},
                blocking=True,
            )
