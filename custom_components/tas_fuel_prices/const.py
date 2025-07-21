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
ATTR_DISTRIBUTOR = "distributor"
ATTR_OPERATOR = "operator"
ATTR_DISCOUNT_APPLIED = "discount_applied"
ATTR_DISCOUNT_PROVIDER = "discount_provider"
ATTR_USER_FAVOURITE = "user_favourite"
ATTR_TYRE_INFLATION = "tyre_inflation"
ATTR_IN_RANGE = "in_range"
ATTR_DISTANCE = "distance"
ATTR_STATIONS = "stations" # For summary sensors


# API Configuration
OAUTH_URL = "https://api.onegov.nsw.gov.au/oauth/client_credential/accesstoken"
API_BASE_URL = "https://api.onegov.nsw.gov.au/FuelPriceCheck/v2/fuel/prices"
API_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
}

# Additional Data URLs from external repo
BASE_DATA_URL = "https://raw.githubusercontent.com/ziogref/TAS-Fuel-HA-Additional-Data/main/"
DISTRIBUTOR_URL = "https://api.github.com/repos/ziogref/TAS-Fuel-HA-Additional-Data/contents/Distributors"
OPERATORS_URL = "https://api.github.com/repos/ziogref/TAS-Fuel-HA-Additional-Data/contents/Operators"
WOOLWORTHS_DISCOUNT_URL = f"{BASE_DATA_URL}Fuel-Discount/Woolworths.txt"
COLES_DISCOUNT_URL = f"{BASE_DATA_URL}Fuel-Discount/Coles.txt"
RACT_DISCOUNT_URL = f"{BASE_DATA_URL}Fuel-Discount/RACT.txt"
TYRE_INFLATION_URL = f"{BASE_DATA_URL}Tyre-Inflation/Sites.txt"


# Configuration from UI
CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_FUEL_TYPES = "fuel_types"
CONF_STATIONS = "stations"

# Discount Configuration
CONF_DISCOUNT_PROVIDERS = "discount_providers"
CONF_ENABLE_WOOLWORTHS_DISCOUNT = "enable_woolworths_discount"
CONF_ENABLE_COLES_DISCOUNT = "enable_coles_discount"
CONF_ENABLE_RACT_DISCOUNT = "enable_ract_discount"

CONF_WOOLWORTHS_DISCOUNT_AMOUNT = "woolworths_discount_amount"
CONF_WOOLWORTHS_ADDITIONAL_STATIONS = "woolworths_additional_stations"
CONF_COLES_DISCOUNT_AMOUNT = "coles_discount_amount"
CONF_COLES_ADDITIONAL_STATIONS = "coles_additional_stations"
CONF_RACT_DISCOUNT_AMOUNT = "ract_discount_amount"
CONF_RACT_ADDITIONAL_STATIONS = "ract_additional_stations"

# Tyre Inflation Configuration
CONF_ADD_TYRE_INFLATION_STATIONS = "add_tyre_inflation_stations"
CONF_REMOVE_TYRE_INFLATION_STATIONS = "remove_tyre_inflation_stations"

# Geolocation Configuration
CONF_LOCATION_ENTITY = "location_entity"
CONF_RANGE = "range"

# Select Entity
SELECT_FUEL_TYPE_ENTITY_NAME = "Fuel Type Selector"
FUEL_TYPE_ORDER = [
    "E10",
    "U91",
    "P95",
    "P98",
    "E85",
    "DL",
    "PDL",
    "B20",
    "LPG",
]


# Update intervals
SCAN_INTERVAL = timedelta(hours=1)
ADDITIONAL_DATA_UPDATE_INTERVAL = timedelta(days=1)
