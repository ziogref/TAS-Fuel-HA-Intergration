"""Button platform for Tasmanian Fuel Prices."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo

from .api import TasFuelAPI
from .const import DOMAIN, CONF_DEVICE_NAME

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    data_bundle = hass.data[DOMAIN][entry.entry_id]
    price_coordinator: DataUpdateCoordinator = data_bundle["price_coordinator"]
    api_client: TasFuelAPI = data_bundle["api"]

    buttons = [
        TasFuelRefreshTokenButton(price_coordinator, api_client),
        TasFuelRefreshPricesButton(price_coordinator),
    ]
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
        # After forcing a token refresh, we also trigger a price refresh
        # to immediately update all sensors, including the token expiry sensor.
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
