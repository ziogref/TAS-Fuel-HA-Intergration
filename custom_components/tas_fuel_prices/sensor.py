"""Sensor platform for Tasmanian Fuel Prices."""
from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorEntity
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
    CONF_DEVICE_NAME,
    CONF_FUEL_TYPES,
    CONF_STATIONS,
    ATTR_STATION_ID,
    ATTR_ADDRESS,
    ATTR_BRAND,
    ATTR_FUEL_TYPE,
    ATTR_LAST_UPDATED,
    ATTR_DISCOUNT_APPLIED,
    ATTR_DISCOUNT_PROVIDER,
    LOGGER,
    CONF_ENABLE_COLES_DISCOUNT,
    CONF_COLES_DISCOUNT_AMOUNT,
    CONF_COLES_ADDITIONAL_STATIONS,
    CONF_ENABLE_WOOLWORTHS_DISCOUNT,
    CONF_WOOLWORTHS_DISCOUNT_AMOUNT,
    CONF_WOOLWORTHS_ADDITIONAL_STATIONS,
    CONF_ENABLE_RACT_DISCOUNT,
    CONF_RACT_DISCOUNT_AMOUNT,
    CONF_RACT_ADDITIONAL_STATIONS,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    data_bundle = hass.data[DOMAIN][entry.entry_id]
    price_coordinator: DataUpdateCoordinator = data_bundle["price_coordinator"]
    discount_coordinator: DataUpdateCoordinator = data_bundle["discount_coordinator"]
    api_client: TasFuelAPI = data_bundle["api"]
    
    fuel_types = entry.options.get(CONF_FUEL_TYPES, ["U91"])
    favourite_stations = entry.options.get(CONF_STATIONS, [])
    time_zone = ZoneInfo(hass.config.time_zone)

    sensors: list[SensorEntity] = []

    # The token expiry sensor is not tied to a specific fuel type, so it uses the main device.
    sensors.append(TasFuelTokenExpirySensor(price_coordinator, api_client, hass.config.time_zone))

    if price_coordinator.data:
        all_stations = price_coordinator.data.get('stations', [])
        all_prices = price_coordinator.data.get('prices', [])
        
        all_stations_map = {str(station['code']): station for station in all_stations}

        for fuel_type in fuel_types:
            relevant_prices = [p for p in all_prices if p.get('fueltype') == fuel_type]

            cheapest_prices = sorted(relevant_prices, key=lambda x: float(x.get('price', 999)))[:5]
            for i, price_info in enumerate(cheapest_prices):
                station_code = str(price_info.get('stationcode'))
                if station_code in all_stations_map:
                    sensors.append(
                        TasFuelPriceSensor(
                            price_coordinator=price_coordinator,
                            discount_coordinator=discount_coordinator,
                            entry=entry,
                            station_code=station_code,
                            fuel_type=fuel_type,
                            name=f"Cheapest {fuel_type} #{i+1}",
                            unique_id_suffix=f"cheapest_{fuel_type}_{i+1}",
                            time_zone=time_zone
                        )
                    )

            for station_code in favourite_stations:
                station_code_str = str(station_code)
                if station_code_str in all_stations_map:
                    station_name = all_stations_map[station_code_str].get('name', f"Station {station_code_str}")
                    sensors.append(
                        TasFuelPriceSensor(
                            price_coordinator=price_coordinator,
                            discount_coordinator=discount_coordinator,
                            entry=entry,
                            station_code=station_code_str,
                            fuel_type=fuel_type,
                            name=f"Favourite: {station_name} ({fuel_type})",
                            unique_id_suffix=f"fav_{station_code_str}_{fuel_type}",
                            is_favourite=True,
                            time_zone=time_zone
                        )
                    )

    async_add_entities(sensors)


class TasFuelPriceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tasmanian Fuel Price sensor."""
    _attr_has_entity_name = True

    def __init__(
        self,
        price_coordinator: DataUpdateCoordinator,
        discount_coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        station_code: str,
        fuel_type: str,
        name: str,
        unique_id_suffix: str,
        time_zone: ZoneInfo,
        is_favourite: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(price_coordinator)
        self.discount_coordinator = discount_coordinator
        self.entry = entry
        self._station_code = station_code
        self._fuel_type = fuel_type
        self._is_favourite = is_favourite
        self._time_zone = time_zone
        self._attr_name = name
        self._attr_unique_id = f"{self.coordinator.config_entry.entry_id}_{unique_id_suffix}"
        self._attr_icon = "mdi:gas-station"
        self._attr_native_unit_of_measurement = "AUD/L"
        self._update_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this sensor is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.config_entry.entry_id}_{self._fuel_type}")},
            name=f"{CONF_DEVICE_NAME} - {self._fuel_type}",
            manufacturer="Custom Integration",
            via_device=(DOMAIN, self.coordinator.config_entry.entry_id)
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
        
        price_info = next(
            (
                p
                for p in all_prices
                if str(p.get("stationcode")) == self._station_code and p.get("fueltype") == self._fuel_type
            ),
            None,
        )

        if station_info and price_info and price_info.get('price') is not None:
            price = float(price_info.get('price'))
            discount_applied_amount = 0.0
            discount_provider = "None"

            # Check for and apply discounts
            if self.discount_coordinator.data:
                options = self.entry.options
                discount_lists = self.discount_coordinator.data

                # Check Coles
                if options.get(CONF_ENABLE_COLES_DISCOUNT):
                    additional_coles = [s.strip() for s in options.get(CONF_COLES_ADDITIONAL_STATIONS, "").split(',') if s.strip()]
                    coles_stations = set(discount_lists.get("coles", []) + additional_coles)
                    if self._station_code in coles_stations:
                        discount_applied_amount = float(options.get(CONF_COLES_DISCOUNT_AMOUNT, 0))
                        price -= discount_applied_amount
                        discount_provider = "Coles"
                
                # Check Woolworths (only if Coles discount was not already applied)
                if discount_provider == "None" and options.get(CONF_ENABLE_WOOLWORTHS_DISCOUNT):
                    additional_ww = [s.strip() for s in options.get(CONF_WOOLWORTHS_ADDITIONAL_STATIONS, "").split(',') if s.strip()]
                    woolworths_stations = set(discount_lists.get("woolworths", []) + additional_ww)
                    if self._station_code in woolworths_stations:
                        discount_applied_amount = float(options.get(CONF_WOOLWORTHS_DISCOUNT_AMOUNT, 0))
                        price -= discount_applied_amount
                        discount_provider = "Woolworths"

                # Check RACT (only if no other discount applied)
                if discount_provider == "None" and options.get(CONF_ENABLE_RACT_DISCOUNT):
                    additional_ract = [s.strip() for s in options.get(CONF_RACT_ADDITIONAL_STATIONS, "").split(',') if s.strip()]
                    ract_stations = set(discount_lists.get("ract", []) + additional_ract)
                    if self._station_code in ract_stations:
                        discount_applied_amount = float(options.get(CONF_RACT_DISCOUNT_AMOUNT, 0))
                        price -= discount_applied_amount
                        discount_provider = "RACT"

            self._attr_native_value = round(price / 100.0, 3)
            
            common_attributes = {
                ATTR_DISCOUNT_APPLIED: round(discount_applied_amount / 100.0, 3),
                ATTR_DISCOUNT_PROVIDER: discount_provider
            }

            if self._is_favourite:
                station_prices = [
                    p for p in all_prices if str(p.get("stationcode")) == self._station_code
                ]
                
                cleaned_prices = [
                    {"fueltype": p.get("fueltype"), "price": p.get("price")} 
                    for p in station_prices
                ]

                latest_update_str = None
                if station_prices:
                   latest_update_str = max(p.get("lastupdated") for p in station_prices if p.get("lastupdated"))
                
                last_updated_local_str = "Unknown"
                if latest_update_str:
                    try:
                        update_time_utc = datetime.strptime(latest_update_str, '%d/%m/%Y %H:%M:%S').replace(tzinfo=timezone.utc)
                        update_time_local = update_time_utc.astimezone(self._time_zone)
                        last_updated_local_str = update_time_local.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError) as e:
                        LOGGER.warning("Could not parse timestamp '%s': %s", latest_update_str, e)
                        last_updated_local_str = "Invalid Date Format"

                filtered_station_info = station_info.copy()
                filtered_station_info.pop("brandid", None)
                filtered_station_info.pop("stationid", None)
                
                attributes = {
                    **filtered_station_info,
                    "all_prices_at_station": cleaned_prices,
                    ATTR_LAST_UPDATED: last_updated_local_str,
                    **common_attributes,
                }
                self._attr_extra_state_attributes = attributes
                 
            else:
                 self._attr_extra_state_attributes = {
                    ATTR_STATION_ID: self._station_code,
                    ATTR_BRAND: station_info.get("brand"),
                    "station_name": station_info.get("name"),
                    ATTR_ADDRESS: station_info.get("address"),
                    ATTR_FUEL_TYPE: self._fuel_type,
                    ATTR_LAST_UPDATED: price_info.get("lastupdated"),
                    **common_attributes,
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

    def __init__(self, coordinator: DataUpdateCoordinator, api_client: TasFuelAPI, tz_str: str) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._api_client = api_client
        self._time_zone = ZoneInfo(tz_str)
        self._attr_name = "Access Token Expiry"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_token_expiry"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this sensor is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name=CONF_DEVICE_NAME,
            manufacturer="Custom Integration",
        )

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor as a formatted string."""
        expiry_time = self._api_client.token_expiry
        if expiry_time is None:
            return None
        
        local_time = expiry_time.astimezone(self._time_zone)
        
        return local_time.strftime('%Y-%m-%d %H:%M:%S')

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
