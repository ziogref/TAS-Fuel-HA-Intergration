"""Button platform for Tasmanian Fuel Prices."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo

from .api import TasFuelAPI
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    data_bundle = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data_bundle["coordinator"]
    api_client: TasFuelAPI = data_bundle["api"]

    buttons = [
        TasFuelForcePriceFetchButton(coordinator),
        TasFuelForceTokenRefreshButton(coordinator, api_client),
    ]
    async_add_entities(buttons)


class TasFuelDiagnosticButton(ButtonEntity):
    """Base class for Tasmanian Fuel Prices diagnostic buttons."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the button."""
        self.coordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this button is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
        )

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this button."""
        return f"{self.coordinator.config_entry.entry_id}_{self.entity_description.key}"


class TasFuelForcePriceFetchButton(TasFuelDiagnosticButton):
    """Button to force a refresh of the fuel price data."""
    entity_description = ButtonEntity.entity_description.fget(ButtonEntity)
    entity_description.key = "force_price_refresh"
    entity_description.name = "Force Fuel Price Refresh"
    entity_description.icon = "mdi:update"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_request_refresh()


class TasFuelForceTokenRefreshButton(TasFuelDiagnosticButton):
    """Button to force a refresh of the API access token."""
    entity_description = ButtonEntity.entity_description.fget(ButtonEntity)
    entity_description.key = "force_token_refresh"
    entity_description.name = "Force Access Token Refresh"
    entity_description.icon = "mdi:key-variant"

    def __init__(self, coordinator: DataUpdateCoordinator, api_client: TasFuelAPI) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._api_client = api_client

    async def async_press(self) -> None:
        """Handle the button press."""
        self._api_client.force_token_refresh()
        # After forcing the token refresh, also trigger a data update to use the new token
        await self.coordinator.async_request_refresh()
