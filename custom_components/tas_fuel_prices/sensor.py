"""Sensor platform for Tasmanian Fuel Prices."""
from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from math import radians, sin, cos, sqrt, atan2

from homeassistant.components.sensor import SensorEntity # type: ignore
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.core import HomeAssistant, callback # type: ignore
from homeassistant.helpers.entity import EntityCategory # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback # type: ignore
from homeassistant.helpers.update_coordinator import ( # type: ignore
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.device_registry import DeviceInfo # type: ignore
from homeassistant.helpers.dispatcher import async_dispatcher_connect # type: ignore

from .api import TasFuelAPI
from .const import (
    DOMAIN,
    CONF_DEVICE_NAME,
    CONF_FUEL_TYPES,
    CONF_STATIONS,
    ATTR_STATION_ID,
    ATTR_ADDRESS,
    ATTR_BRAND,
    ATTR_FUEL_BRAND,
    ATTR_FUEL_TYPE,
    ATTR_LAST_UPDATED,
    ATTR_DISCOUNT_APPLIED,
    ATTR_DISCOUNT_PROVIDER,
    ATTR_USER_FAVOURITE,
    ATTR_TYRE_INFLATION,
    ATTR_IN_RANGE,
    ATTR_DISTANCE,
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
    CONF_ADD_TYRE_INFLATION_STATIONS,
    CONF_REMOVE_TYRE_INFLATION_STATIONS,
    CONF_LOCATION_ENTITY,
    CONF_RANGE,
)

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points in kilometers."""
    R = 6371  # Radius of Earth in kilometers
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat / 2) * sin(dLat / 2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon / 2) * sin(dLon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    data_bundle = hass.data[DOMAIN][entry.entry_id]
    price_coordinator: DataUpdateCoordinator = data_bundle["price_coordinator"]
    additional_data_coordinator: DataUpdateCoordinator = data_bundle["additional_data_coordinator"]
    api_client: TasFuelAPI = data_bundle["api"]
    
    fuel_types = entry.options.get(CONF_FUEL_TYPES, ["U91"])
    favourite_stations = entry.options.get(CONF_STATIONS, [])
    time_zone = ZoneInfo(hass.config.time_zone)

    sensors: list[SensorEntity] = []

    sensors.append(TasFuelTokenExpirySensor(price_coordinator, api_client, hass.config.time_zone))

    if price_coordinator.data:
        all_stations = price_coordinator.data.get('stations', [])
        
        for station_info in all_stations:
            station_code = str(station_info.get("code"))
            for fuel_type in fuel_types:
                sensors.append(
                    TasFuelPriceSensor(
                        price_coordinator=price_coordinator,
                        additional_data_coordinator=additional_data_coordinator,
                        entry=entry,
                        station_code=station_code,
                        station_name=station_info.get("name", f"Station {station_code}"),
                        fuel_type=fuel_type,
                        time_zone=time_zone,
                        favourite_stations=favourite_stations,
                        hass=hass,
                    )
                )
    
    async_add_entities(sensors)


class TasFuelPriceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tasmanian Fuel Price sensor."""
    _attr_has_entity_name = False

    def __init__(
        self,
        price_coordinator: DataUpdateCoordinator,
        additional_data_coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        station_code: str,
        station_name: str,
        fuel_type: str,
        time_zone: ZoneInfo,
        favourite_stations: list[str],
        hass: HomeAssistant,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(price_coordinator)
        self.additional_data_coordinator = additional_data_coordinator
        self.entry = entry
        self._station_code = station_code
        self._fuel_type = fuel_type
        self._time_zone = time_zone
        self._favourite_stations = favourite_stations
        self.hass = hass

        self._attr_name = f"{station_name} {fuel_type}"
        self._attr_unique_id = f"{self.coordinator.config_entry.entry_id}_{station_code}_{fuel_type}"
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

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Listen for updates from the additional_data_coordinator to refresh attributes
        self.async_on_remove(
            self.additional_data_coordinator.async_add_listener(
                self.async_schedule_update_ha_state, True
            )
        )

        # Listen for the signal to recalculate distance from location changes
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self.coordinator.config_entry.entry_id}_recalculate_distance",
                self.async_recalculate_distance,
            )
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    def _calculate_distance_attributes(self) -> dict:
        """Calculate distance and in_range attributes."""
        location_entity_id = self.entry.options.get(CONF_LOCATION_ENTITY)
        if not location_entity_id:
            return {ATTR_DISTANCE: "Not Configured", ATTR_IN_RANGE: True}

        range_km = self.entry.options.get(CONF_RANGE, 5)
        all_stations_map = {str(station['code']): station for station in self.coordinator.data.get('stations', [])}
        station_info = all_stations_map.get(self._station_code)
        
        distance = None
        is_in_range = True  # Default to True if we can't calculate

        if station_info and station_info.get("location"):
            location_state = self.hass.states.get(location_entity_id)
            if location_state and 'latitude' in location_state.attributes and 'longitude' in location_state.attributes:
                phone_lat = location_state.attributes['latitude']
                phone_lon = location_state.attributes['longitude']
                station_lat = station_info["location"]["latitude"]
                station_lon = station_info["location"]["longitude"]

                if phone_lat and phone_lon and station_lat and station_lon:
                    distance = haversine(phone_lat, phone_lon, station_lat, station_lon)
                    is_in_range = distance <= range_km
        
        return {
            ATTR_DISTANCE: f"{distance:.2f} km" if distance is not None else "Unknown",
            ATTR_IN_RANGE: is_in_range,
        }

    @callback
    def async_recalculate_distance(self) -> None:
        """Recalculate distance attributes when the location entity updates."""
        if not self.coordinator.data or not self._attr_extra_state_attributes:
            return

        LOGGER.debug("Recalculating distance for %s due to location update", self.entity_id)
        new_geo_attrs = self._calculate_distance_attributes()
        self._attr_extra_state_attributes.update(new_geo_attrs)
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
            tyre_inflation = False
            fuel_brand = "No data found"
            options = self.entry.options

            # Check for and apply discounts and amenities
            if self.additional_data_coordinator.data:
                additional_data = self.additional_data_coordinator.data

                # Fuel Brand / Distributor
                distributors_map = additional_data.get("distributors", {})
                fuel_brand = distributors_map.get(self._station_code, "No data found")

                # Discounts
                if options.get(CONF_ENABLE_WOOLWORTHS_DISCOUNT):
                    additional_ww = [s.strip() for s in options.get(CONF_WOOLWORTHS_ADDITIONAL_STATIONS, "").split(',') if s.strip()]
                    woolworths_stations = set(additional_data.get("woolworths", []) + additional_ww)
                    if self._station_code in woolworths_stations:
                        discount_applied_amount = float(options.get(CONF_WOOLWORTHS_DISCOUNT_AMOUNT, 0))
                        price -= discount_applied_amount
                        discount_provider = "Woolworths"

                if discount_provider == "None" and options.get(CONF_ENABLE_COLES_DISCOUNT):
                    additional_coles = [s.strip() for s in options.get(CONF_COLES_ADDITIONAL_STATIONS, "").split(',') if s.strip()]
                    coles_stations = set(additional_data.get("coles", []) + additional_coles)
                    if self._station_code in coles_stations:
                        discount_applied_amount = float(options.get(CONF_COLES_DISCOUNT_AMOUNT, 0))
                        price -= discount_applied_amount
                        discount_provider = "Coles"
                
                if discount_provider == "None" and options.get(CONF_ENABLE_RACT_DISCOUNT):
                    additional_ract = [s.strip() for s in options.get(CONF_RACT_ADDITIONAL_STATIONS, "").split(',') if s.strip()]
                    ract_stations = set(additional_data.get("ract", []) + additional_ract)
                    if self._station_code in ract_stations:
                        discount_applied_amount = float(options.get(CONF_RACT_DISCOUNT_AMOUNT, 0))
                        price -= discount_applied_amount
                        discount_provider = "RACT"
                
                # Tyre Inflation
                github_list = set(additional_data.get("tyre_inflation", []))
                add_list = {s.strip() for s in options.get(CONF_ADD_TYRE_INFLATION_STATIONS, "").split(',') if s.strip()}
                remove_list = {s.strip() for s in options.get(CONF_REMOVE_TYRE_INFLATION_STATIONS, "").split(',') if s.strip()}

                if self._station_code in add_list:
                    tyre_inflation = True
                elif self._station_code in github_list and self._station_code not in remove_list:
                    tyre_inflation = True


            self._attr_native_value = round(price / 100.0, 3)
            
            is_favourite = self._station_code in self._favourite_stations
            
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
                ATTR_DISCOUNT_APPLIED: round(discount_applied_amount / 100.0, 3),
                ATTR_DISCOUNT_PROVIDER: discount_provider,
                ATTR_USER_FAVOURITE: is_favourite,
                ATTR_TYRE_INFLATION: tyre_inflation,
                ATTR_FUEL_BRAND: fuel_brand,
            }
            # Add geolocation attributes
            attributes.update(self._calculate_distance_attributes())
            
            self._attr_extra_state_attributes = attributes
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
