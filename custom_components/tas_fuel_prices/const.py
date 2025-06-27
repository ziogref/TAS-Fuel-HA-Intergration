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
ATTR_DISCOUNT_APPLIED = "discount_applied"
ATTR_DISCOUNT_PROVIDER = "discount_provider"


# API Configuration
OAUTH_URL = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken"
API_BASE_URL = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v2/fuel/prices"
API_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
}

# Discount Data URLs from external repo
BASE_DISCOUNT_URL = "https://raw.githubusercontent.com/ziogref/TAS-Fuel-HA-Additional-Data/main/Fuel-Discount/"
COLES_DISCOUNT_URL = f"{BASE_DISCOUNT_URL}Coles.txt"
WOOLWORTHS_DISCOUNT_URL = f"{BASE_DISCOUNT_URL}Woolworths.txt"
RACT_DISCOUNT_URL = f"{BASE_DISCOUNT_URL}RACT.txt"

# Configuration from UI
CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_FUEL_TYPES = "fuel_types"
CONF_STATIONS = "stations"

# Discount Configuration
CONF_DISCOUNT_PROVIDERS = "discount_providers"
CONF_ENABLE_COLES_DISCOUNT = "enable_coles_discount"
CONF_ENABLE_WOOLWORTHS_DISCOUNT = "enable_woolworths_discount"
CONF_ENABLE_RACT_DISCOUNT = "enable_ract_discount"

CONF_COLES_DISCOUNT_AMOUNT = "coles_discount_amount"
CONF_COLES_ADDITIONAL_STATIONS = "coles_additional_stations"
CONF_WOOLWORTHS_DISCOUNT_AMOUNT = "woolworths_discount_amount"
CONF_WOOLWORTHS_ADDITIONAL_STATIONS = "woolworths_additional_stations"
CONF_RACT_DISCOUNT_AMOUNT = "ract_discount_amount"
CONF_RACT_ADDITIONAL_STATIONS = "ract_additional_stations"


# Update intervals
SCAN_INTERVAL = timedelta(hours=1)
DISCOUNT_DATA_UPDATE_INTERVAL = timedelta(days=1)
