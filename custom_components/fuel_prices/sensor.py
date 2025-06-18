"""Sensor platform for Tasmanian Fuel Prices."""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    SensorEntity,
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
    
    fuel_type = entry.options.get(CONF_FUEL_TYPE, "U91")
    favourite_stations = entry.options.get(CONF_STATIONS, [])

    sensors: list[SensorEntity] = []

    # Add the diagnostic sensor for token expiry, passing the HA timezone to it
    sensors.append(TasFuelTokenExpirySensor(coordinator, api_client, hass.config.time_zone))

    if coordinator.data:
        # The API returns a list directly under 'stations' and 'prices'
        all_stations = coordinator.data.get('stations', [])
        all_prices = coordinator.data.get('prices', [])
        
        # Use string for station codes to ensure consistent matching
        all_stations_map = {str(station['code']): station for station in all_stations}

        # Filter prices for the selected fuel type to find the cheapest
        relevant_prices = [p for p in all_prices if p.get('fueltype') == fuel_type]

        cheapest_prices = sorted(relevant_prices, key=lambda x: x.get('price', 999))[:5]
        for i, price_info in enumerate(cheapest_prices):
            station_code = str(price_info.get('stationcode'))
            if station_code in all_stations_map:
                sensors.append(
                    TasFuelPriceSensor(
                        coordinator=coordinator,
                        station_code=station_code,
                        fuel_type=fuel_type,
                        name=f"Cheapest {fuel_type} #{i+1}",
                        unique_id_suffix=f"cheapest_{fuel_type}_{i+1}"
                    )
                )

        # Create sensors for favourite stations
        for station_code in favourite_stations:
            station_code_str = str(station_code)
            if station_code_str in all_stations_map:
                station_name = all_stations_map[station_code_str].get('name', f"Station {station_code_str}")
                sensors.append(
                    TasFuelPriceSensor(
                        coordinator=coordinator,
                        station_code=station_code_str,
                        fuel_type=fuel_type,
                        name=f"Favourite: {station_name}",
                        unique_id_suffix=f"fav_{station_code_str}",
                        is_favourite=True # Flag this as a favourite sensor
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
        is_favourite: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._station_code = station_code
        self._fuel_type = fuel_type
        self._is_favourite = is_favourite
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
            
        all_stations_map = {str(station['code']): station for station in self.coordinator.data.get('stations', [])}
        all_prices = self.coordinator.data.get('prices', [])

        station_info = all_stations_map.get(self._station_code)
        
        # Find the price for the specific fuel type for this sensor's state
        price_info = next(
            (
                p
                for p in all_prices
                if str(p.get("stationcode")) == self._station_code and p.get("fueltype") == self._fuel_type
            ),
            None,
        )

        if station_info and price_info and price_info.get('price') is not None:
            # The state of the sensor is the price of the selected fuel type
            self._attr_native_value = round(price_info.get('price') / 100.0, 3)
            
            # For favourite stations, add all available details as attributes
            if self._is_favourite:
                # Get all prices for this specific station
                station_prices = [
                    p for p in all_prices if str(p.get("stationcode")) == self._station_code
                ]
                # Combine station info and all its prices into the attributes
                self._attr_extra_state_attributes = {
                    **station_info,
                    "all_prices_at_station": station_prices
                }
            else: # For cheapest stations, keep attributes minimal
                 self._attr_extra_state_attributes = {
                    ATTR_STATION_ID: self._station_code,
                    ATTR_BRAND: station_info.get("brand"),
                    "station_name": station_info.get("name"),
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

    def __init__(self, coordinator: DataUpdateCoordinator, api_client: TasFuelAPI, time_zone: ZoneInfo) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._time_zone = time_zone
        self._attr_name = "Access Token Expiry"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_token_expiry"
        # We are providing a formatted string, so we must not set a device_class.

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this sensor is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
        )

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor as a formatted string."""
        expiry_time = self._api_client.token_expiry
        if expiry_time is None:
            return None
        
        # Convert the UTC datetime object to the local timezone of the Home Assistant instance
        local_time = expiry_time.astimezone(self._time_zone)
        
        # Format the local time into the desired string format
        return local_time.strftime('%Y-%m-%d %H:%M:%S')

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
