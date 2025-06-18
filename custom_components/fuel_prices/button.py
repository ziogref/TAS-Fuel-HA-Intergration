"""Button platform for Fuel Prices."""
from __future__ import annotations
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo

from .api import TasFuelAPI
from .const import DOMAIN

@dataclass(frozen=True, kw_only=True)
class TasFuelButtonEntityDescription(ButtonEntityDescription):
    """Describes a Fuel Prices button entity."""

BUTTONS: tuple[TasFuelButtonEntityDescription, ...] = (
    TasFuelButtonEntityDescription(
        key="force_price_refresh",
        name="Force Fuel Price Refresh",
        icon="mdi:update",
    ),
    TasFuelButtonEntityDescription(
        key="force_token_refresh",
        name="Force Access Token Refresh",
        icon="mdi:key-variant",
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    data_bundle = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data_bundle["coordinator"]
    api_client: TasFuelAPI = data_bundle["api"]

    async_add_entities(
        TasFuelDiagnosticButton(
            coordinator=coordinator,
            api_client=api_client,
            description=description,
        )
        for description in BUTTONS
    )


class TasFuelDiagnosticButton(ButtonEntity):
    """Base class for Fuel Prices diagnostic buttons."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api_client: TasFuelAPI,
        description: TasFuelButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self._api_client = api_client
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this button is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.entity_description.key == "force_price_refresh":
            await self.coordinator.async_request_refresh()
        elif self.entity_description.key == "force_token_refresh":
            self._api_client.force_token_refresh()
            await self.coordinator.async_request_refresh()
