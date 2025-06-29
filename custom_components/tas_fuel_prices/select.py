"""Select platform for Tasmanian Fuel Prices."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_DEVICE_NAME, CONF_FUEL_TYPES, SELECT_FUEL_TYPE_ENTITY_NAME


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    fuel_types = entry.options.get(CONF_FUEL_TYPES, [])
    if fuel_types:
        async_add_entities([FuelTypeSelect(entry, fuel_types)])


class FuelTypeSelect(SelectEntity, RestoreEntity):
    """Representation of a Select entity for fuel types."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, fuel_types: list[str]) -> None:
        """Initialize the select entity."""
        self._entry = entry
        self._attr_name = SELECT_FUEL_TYPE_ENTITY_NAME
        self._attr_unique_id = f"{entry.entry_id}_fuel_type_selector"
        self._attr_options = fuel_types
        self._attr_icon = "mdi:gas-station"
        # Set the default selected option to the first in the list if available
        self._attr_current_option = fuel_types[0] if fuel_types else None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state in self._attr_options:
            self._attr_current_option = last_state.state

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this entity is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=CONF_DEVICE_NAME,
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self.async_write_ha_state()

