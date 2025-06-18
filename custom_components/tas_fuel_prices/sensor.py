"""Sensor platform for Tasmanian Fuel Prices."""
from __future__ import annotations
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .api import TasFuelAPI
from .const import (
    DOMAIN,
    LOGGER,
    CONF_FUEL_TYPE,
    CONF_STATIONS,
    ATTR_STATION_ID,
    ATTR_ADDRESS,
    ATTR_BRAND,
    ATTR_FUEL_TYPE,
    ATTR_LAST_UPDATED,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    data_bundle = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data_bundle["coordinator"]
    api_client: TasFuelAPI = data_bundle["api"]
    
    await coordinator.async_refresh()
    
    fuel_type = entry.options.get(CONF_FUEL_TYPE, "U91")
    favourite_stations = entry.options.get(CONF_STATIONS, [])

    sensors: list[SensorEntity] = []

    # Add the diagnostic sensor for token expiry
    sensors.append(TasFuelTokenExpirySensor(coordinator, api_client))

    if coordinator.data:
        all_stations = coordinator.data.get('stations', [])
        all_prices = coordinator.data.get('prices', [])
        
        all_stations_map = {station['code']: station for station in all_stations}

        relevant_prices = [p for p in all_prices if p.get('fueltype') == fuel_type]

        cheapest_prices = sorted(relevant_prices, key=lambda x: x.get('price', 999))[:5]
        for i, price_info in enumerate(cheapest_prices):
            station_code = price_info.get('stationcode')
            if station_code in all_stations_map:
                station_name = all_stations_map[station_code].get('name', f"Station {station_code}")
                sensors.append(
                    TasFuelPriceSensor(
                        coordinator=coordinator,
                        station_code=station_code,
                        fuel_type=fuel_type,
                        name=f"Cheapest {fuel_type} #{i+1}: {station_name}",
                        unique_id_suffix=f"cheapest_{fuel_type}_{i+1}"
                    )
                )

        for station_code in favourite_stations:
            if station_code in all_stations_map:
                station_name = all_stations_map[station_code].get('name', f"Station {station_code}")
                sensors.append(
                    TasFuelPriceSensor(
                        coordinator=coordinator,
                        station_code=station_code,
                        fuel_type=fuel_type,
                        name=f"Favourite: {station_name}",
                        unique_id_suffix=f"fav_{station_code}"
                    )
                )

    async_add_entities(sensors)


class TasFuelPriceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tasmanian Fuel Price sensor."""
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        station_code: str,
        fuel_type: str,
        name: str,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._station_code = station_code
        self._fuel_type = fuel_type
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{unique_id_suffix}"
        self._attr_icon = "mdi:gas-station"
        self._attr_native_unit_of_measurement = "AUD/L"
        self._update_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this sensor is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self) -> None:
        """Update the state and attributes of the sensor."""
        if not self.coordinator.data:
            self._attr_native_value = None
            return
            
        all_stations_map = {station['code']: station for station in self.coordinator.data.get('stations', [])}
        all_prices = self.coordinator.data.get('prices', [])

        station_info = all_stations_map.get(self._station_code)
        price_info = next(
            (
                p
                for p in all_prices
                if p.get("stationcode") == self._station_code and p.get("fueltype") == self._fuel_type
            ),
            None,
        )

        if station_info and price_info and price_info.get('price') is not None:
            self._attr_native_value = round(price_info.get('price') / 100.0, 3)
            self._attr_extra_state_attributes = {
                ATTR_STATION_ID: self._station_code,
                ATTR_BRAND: station_info.get("brand"),
                ATTR_ADDRESS: station_info.get("address"),
                ATTR_FUEL_TYPE: self._fuel_type,
                ATTR_LAST_UPDATED: price_info.get("lastupdated"),
            }
        else:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {
                ATTR_STATION_ID: self._station_code,
                ATTR_FUEL_TYPE: self._fuel_type,
                "error": "Price not available for this station and fuel type",
            }

class TasFuelTokenExpirySensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor that shows token expiry."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: DataUpdateCoordinator, api_client: TasFuelAPI) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._attr_name = "Access Token Expiry"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_token_expiry"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this sensor is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        return self._api_client.token_expiry

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # This will be called after a successful data fetch, and we can tell Home Assistant
        # to re-read our sensor's state, which will now have the correct expiry time.
        self.async_write_ha_state()

