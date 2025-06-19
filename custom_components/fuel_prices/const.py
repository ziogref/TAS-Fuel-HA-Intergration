"""Constants for the Tasmanian Fuel Prices integration."""

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# The domain of the integration. This must be unique.
DOMAIN = "tas_fuel_prices"
CONF_DEVICE_NAME = "Tasmanian Fuel Prices"

# Attributes
ATTR_STATION_ID = "station_id"
ATTR_FUEL_TYPE = "fuel_type"
ATTR_LAST_UPDATED = "last_updated"
ATTR_ADDRESS = "address"
ATTR_BRAND = "brand"

# API Configuration
OAUTH_URL = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken"
API_BASE_URL = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v2/fuel/prices"
API_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
}

# Configuration from UI
CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_FUEL_TYPE = "fuel_type"
CONF_STATIONS = "stations"

# Update interval for the coordinator
SCAN_INTERVAL = timedelta(hours=1)
