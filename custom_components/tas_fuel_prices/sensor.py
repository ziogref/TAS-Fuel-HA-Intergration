"""Sensor platform for Tasmanian Fuel Prices."""
from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from math import radians, sin, cos, sqrt, atan2
import operator

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util

from .api import TasFuelAPI
from .const import (
    DOMAIN,
    CONF_DEVICE_NAME,
    CONF_FUEL_TYPES,
    CONF_STATIONS,
    ATTR_STATION_ID,
    ATTR_ADDRESS,
    ATTR_BRAND,
    ATTR_DISTRIBUTOR,
    ATTR_OPERATOR,
    ATTR_FUEL_TYPE,
    ATTR_LAST_UPDATED,
    ATTR_DISCOUNT_APPLIED,
    ATTR_DISCOUNT_PROVIDER,
    ATTR_USER_FAVOURITE,
    ATTR_TYRE_INFLATION,
    ATTR_IN_RANGE,
    ATTR_DISTANCE,
    ATTR_STATIONS,
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

    sensors: list[SensorEntity] = [
        TasFuelTokenExpirySensor(price_coordinator, api_client, hass.config.time_zone),
        TasFuelPricesLastUpdatedSensor(price_coordinator),
        TasFuelAdditionalDataLastUpdatedSensor(additional_data_coordinator),
    ]

    # Create summary sensors for each fuel type
    for fuel_type in fuel_types:
        sensors.append(
            TasFuelCheapestNearMeSummarySensor(
                price_coordinator, additional_data_coordinator, entry, fuel_type, hass
            )
        )

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
            distributor = "No data found"
            operator = "No data found"
            options = self.entry.options

            # Check for and apply discounts and amenities
            if self.additional_data_coordinator.data:
                additional_data = self.additional_data_coordinator.data

                # Distributor (Fuel Brand)
                distributors_map = additional_data.get("distributors", {})
                distributor = distributors_map.get(self._station_code, "No data found")

                # Site Operator
                operators_map = additional_data.get("operators", {})
                operator = operators_map.get(self._station_code, "No data found")

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
                ATTR_DISTRIBUTOR: distributor,
                ATTR_OPERATOR: operator,
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

class TasFuelCheapestNearMeSummarySensor(CoordinatorEntity, SensorEntity):
    """Representation of a summary sensor for the cheapest stations nearby."""
    _attr_has_entity_name = True

    def __init__(
        self,
        price_coordinator: DataUpdateCoordinator,
        additional_data_coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        fuel_type: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the summary sensor."""
        super().__init__(price_coordinator)
        self.additional_data_coordinator = additional_data_coordinator
        self.entry = entry
        self._fuel_type = fuel_type
        self.hass = hass

        self._attr_name = f"{fuel_type} Cheapest Near Me"
        self._attr_unique_id = f"{entry.entry_id}_{fuel_type}_cheapest_near_me"
        self._attr_icon = "mdi:map-marker-radius"
        self._attr_native_unit_of_measurement = "AUD/L"
        self._attr_extra_state_attributes = {ATTR_STATIONS: []}

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this sensor is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=CONF_DEVICE_NAME,
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.additional_data_coordinator.async_add_listener(self._handle_coordinator_update)
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self.entry.entry_id}_recalculate_distance",
                self._handle_coordinator_update,
            )
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from any coordinator."""
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self) -> None:
        """Update the state and attributes of the summary sensor."""
        if not self.coordinator.data or not self.additional_data_coordinator.data:
            self._attr_native_value = None
            return

        all_stations_info = self.coordinator.data.get('stations', [])
        all_prices = self.coordinator.data.get('prices', [])
        additional_data = self.additional_data_coordinator.data
        options = self.entry.options

        # --- Build a comprehensive list of all stations for this fuel type ---
        all_processed_stations = []
        for station_info in all_stations_info:
            station_code = str(station_info.get("code"))
            price_info = next((p for p in all_prices if str(p.get("stationcode")) == station_code and p.get("fueltype") == self._fuel_type), None)

            if not price_info or price_info.get('price') is None:
                continue

            # Calculate distance and check if in range
            dist_attrs = self._calculate_distance_attributes(station_info)
            if not dist_attrs[ATTR_IN_RANGE]:
                continue

            # Calculate discounts
            price = float(price_info.get('price'))
            discounted_price = price
            
            if options.get(CONF_ENABLE_WOOLWORTHS_DISCOUNT):
                woolworths_stations = set(additional_data.get("woolworths", []) + [s.strip() for s in options.get(CONF_WOOLWORTHS_ADDITIONAL_STATIONS, "").split(',') if s.strip()])
                if station_code in woolworths_stations:
                    discounted_price -= float(options.get(CONF_WOOLWORTHS_DISCOUNT_AMOUNT, 0))
            
            if discounted_price == price and options.get(CONF_ENABLE_COLES_DISCOUNT):
                coles_stations = set(additional_data.get("coles", []) + [s.strip() for s in options.get(CONF_COLES_ADDITIONAL_STATIONS, "").split(',') if s.strip()])
                if station_code in coles_stations:
                    discounted_price -= float(options.get(CONF_COLES_DISCOUNT_AMOUNT, 0))

            if discounted_price == price and options.get(CONF_ENABLE_RACT_DISCOUNT):
                ract_stations = set(additional_data.get("ract", []) + [s.strip() for s in options.get(CONF_RACT_ADDITIONAL_STATIONS, "").split(',') if s.strip()])
                if station_code in ract_stations:
                    discounted_price -= float(options.get(CONF_RACT_DISCOUNT_AMOUNT, 0))

            # Check tyre inflation
            tyre_inflation_list = set(additional_data.get("tyre_inflation", []))
            add_list = {s.strip() for s in options.get(CONF_ADD_TYRE_INFLATION_STATIONS, "").split(',') if s.strip()}
            remove_list = {s.strip() for s in options.get(CONF_REMOVE_TYRE_INFLATION_STATIONS, "").split(',') if s.strip()}
            has_tyres = station_code in add_list or (station_code in tyre_inflation_list and station_code not in remove_list)

            all_processed_stations.append({
                "name": station_info.get("name"),
                "address": station_info.get("address"),
                "code": station_code,
                "price": round(price / 100.0, 3),
                "discounted_price": round(discounted_price / 100.0, 3),
                "distributor": additional_data.get("distributors", {}).get(station_code, "No data found"),
                "operator": additional_data.get("operators", {}).get(station_code, "No data found"),
                ATTR_TYRE_INFLATION: has_tyres,
                **dist_attrs,
            })

        if not all_processed_stations:
            self._attr_native_value = None
            self._attr_extra_state_attributes[ATTR_STATIONS] = []
            return

        # --- Apply summary logic ---
        # Sort all in-range stations by discounted price
        sorted_stations = sorted(all_processed_stations, key=operator.itemgetter("discounted_price"))
        
        cheapest_overall = sorted_stations[0]
        cheapest_with_tyres = next((s for s in sorted_stations if s[ATTR_TYRE_INFLATION]), None)

        summary_list = []
        if cheapest_with_tyres and cheapest_with_tyres["code"] == cheapest_overall["code"]:
            summary_list.append(cheapest_overall)
        elif cheapest_with_tyres:
            summary_list.append(cheapest_overall)
            summary_list.append(cheapest_with_tyres)
        else: # No stations with tyres in range
            summary_list.append(cheapest_overall)

        self._attr_native_value = cheapest_overall["discounted_price"]
        self._attr_extra_state_attributes[ATTR_STATIONS] = summary_list

    def _calculate_distance_attributes(self, station_info: dict) -> dict:
        """Helper to calculate distance for a single station."""
        location_entity_id = self.entry.options.get(CONF_LOCATION_ENTITY)
        if not location_entity_id:
            return {ATTR_DISTANCE: "Not Configured", ATTR_IN_RANGE: True}

        range_km = self.entry.options.get(CONF_RANGE, 5)
        distance = None
        is_in_range = True

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

class TasFuelPricesLastUpdatedSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor that shows the last price update time."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self.entity_id = f"sensor.{DOMAIN}_prices_last_updated"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_prices_last_updated"
        self._attr_name = "Prices Last Updated"
        self._attr_native_value = dt_util.utcnow() if coordinator.last_update_success else None

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this sensor is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name=CONF_DEVICE_NAME,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = dt_util.utcnow()
        self.async_write_ha_state()

class TasFuelAdditionalDataLastUpdatedSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor that shows the last additional data update time."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self.entity_id = f"sensor.{DOMAIN}_additional_data_last_updated"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_additional_data_last_updated"
        self._attr_name = "Additional Data Last Updated"
        self._attr_native_value = dt_util.utcnow() if coordinator.last_update_success else None

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device this sensor is part of."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name=CONF_DEVICE_NAME,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = dt_util.utcnow()
        self.async_write_ha_state()
