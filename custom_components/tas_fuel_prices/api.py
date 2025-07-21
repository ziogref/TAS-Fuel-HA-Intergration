"""API client for the Tasmanian Fuel Prices integration."""

from datetime import datetime, timedelta, UTC
import backoff # type: ignore
import aiohttp # type: ignore
import json
import uuid

from aiohttp import ClientError, ClientSession, ClientResponseError # type: ignore

from .const import (
    API_BASE_URL,
    OAUTH_URL,
    LOGGER,
    COLES_DISCOUNT_URL,
    WOOLWORTHS_DISCOUNT_URL,
    RACT_DISCOUNT_URL,
    TYRE_INFLATION_URL,
    DISTRIBUTORS_URL,
)


class TasFuelAPI:
    """A class for handling the data retrieval from the FuelCheck API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        session: ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._api_secret = api_secret
        self._session = session
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

    @property
    def token_expiry(self) -> datetime | None:
        """Return the token expiry datetime object."""
        return self._token_expiry

    @backoff.on_exception(backoff.expo, ClientResponseError, max_tries=3, logger=LOGGER)
    async def _get_access_token(self) -> str:
        """
        Retrieve a new OAuth2 access token from the API.
        The token is valid for 12 hours.
        """
        if self._access_token and self._token_expiry and self._token_expiry > datetime.now(UTC):
            LOGGER.debug("Using existing, valid access token.")
            return self._access_token

        LOGGER.info("Requesting new access token.")
        
        params = {"grant_type": "client_credentials"}
        auth = aiohttp.BasicAuth(self._api_key, self._api_secret)

        try:
            response = await self._session.get(
                OAUTH_URL,
                params=params,
                auth=auth
            )
            response.raise_for_status()
            
            token_data = await response.json(content_type=None)

            if "access_token" not in token_data:
                LOGGER.error(
                    "API returned a successful response, but no 'access_token' was found. Response: %s",
                    token_data,
                )
                raise KeyError("'access_token' not found in API response.")

            self._access_token = token_data["access_token"]
            expiry_seconds = int(token_data.get("expires_in", 43199))
            self._token_expiry = datetime.now(UTC) + timedelta(seconds=expiry_seconds - 60)
            
            LOGGER.info("Successfully obtained new access token.")
            return self._access_token

        except ClientResponseError as err:
            response_text = await response.text()
            LOGGER.error(
                "API Error getting token. Status: %s, Response: %s",
                err.status,
                response_text,
            )
            raise
        except Exception as err:
            LOGGER.error("Unexpected error getting token: %s", err)
            raise

    @backoff.on_exception(backoff.expo, ClientError, max_tries=3, logger=LOGGER)
    async def fetch_prices(self) -> dict:
        """
        Fetch fuel prices from the API.
        This function handles token retrieval and renewal automatically.
        """
        token = await self._get_access_token()
        
        transaction_id = str(uuid.uuid4())
        request_timestamp = datetime.now(UTC).strftime('%d/%m/%Y %I:%M:%S %p')

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "apikey": self._api_key,
            "transactionid": transaction_id,
            "requesttimestamp": request_timestamp,
        }

        params = {"states": "TAS"}
        
        try:
            LOGGER.debug("Fetching all fuel prices for TAS from API.")
            response = await self._session.get(
                API_BASE_URL,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = await response.json(content_type=None)
            LOGGER.debug("Successfully fetched all fuel prices.")
            return data

        except ClientResponseError as err:
            if err.status == 401:
                LOGGER.warning("Access token rejected by prices endpoint, forcing refresh.")
                self._access_token = None
            raise
        except Exception as err:
            LOGGER.error("Unexpected error fetching prices: %s", err)
            raise

    async def force_refresh_token(self) -> None:
        """
        Force a refresh of the access token by clearing the existing one.
        The next call to `fetch_prices` will then request a new token.
        """
        LOGGER.info("Forcing a refresh of the access token.")
        self._access_token = None
        self._token_expiry = None

    @backoff.on_exception(backoff.expo, ClientError, max_tries=3, logger=LOGGER)
    async def fetch_additional_data_lists(self) -> dict:
        """Fetch the lists of station codes for discounts, amenities, and distributors from GitHub."""
        LOGGER.info("Fetching additional data lists from GitHub.")
        additional_data = {}
        urls = {
            "coles": COLES_DISCOUNT_URL,
            "woolworths": WOOLWORTHS_DISCOUNT_URL,
            "ract": RACT_DISCOUNT_URL,
            "tyre_inflation": TYRE_INFLATION_URL,
        }

        for provider, url in urls.items():
            try:
                response = await self._session.get(url)
                response.raise_for_status()
                text = await response.text()
                
                # Process each line to extract the station code, ignoring comments.
                station_codes = set()
                for line in text.splitlines():
                    # Take the part before the first '#', which acts as a comment character.
                    code_part = line.split('#', 1)[0]
                    # Strip leading/trailing whitespace to handle various formatting.
                    station_code = code_part.strip()
                    # Add to the set if the resulting string is not empty.
                    if station_code:
                        station_codes.add(station_code)
                
                additional_data[provider] = list(station_codes)
                LOGGER.debug("Successfully fetched and parsed %s station codes for %s", len(station_codes), provider)
            except ClientError as e:
                LOGGER.error("Error fetching additional data list for %s: %s", provider, e)
                # If a list fails to download, provide an empty list to prevent errors
                additional_data[provider] = []
        
        # Fetch and process distributor data
        distributors = {}
        try:
            LOGGER.info("Fetching distributor file list from GitHub.")
            response = await self._session.get(DISTRIBUTORS_URL)
            response.raise_for_status()
            files = await response.json()

            for file_info in files:
                if file_info.get("type") == "file" and file_info.get("name").endswith(".txt"):
                    distributor_name = file_info["name"].replace(".txt", "")
                    download_url = file_info["download_url"]
                    LOGGER.debug("Fetching distributor file: %s", download_url)
                    
                    dist_response = await self._session.get(download_url)
                    dist_response.raise_for_status()
                    text = await dist_response.text()

                    for line in text.splitlines():
                        code_part = line.split('#', 1)[0]
                        station_code = code_part.strip()
                        if station_code:
                            distributors[station_code] = distributor_name
            LOGGER.info("Successfully processed %s distributor mappings.", len(distributors))
        except (ClientError, KeyError) as e:
            LOGGER.error("Error fetching or processing distributor data: %s", e)

        additional_data["distributors"] = distributors
        
        return additional_data
