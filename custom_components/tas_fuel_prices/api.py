"""API client for the Tasmanian Fuel Prices integration."""

import asyncio
from datetime import datetime, timedelta
import backoff
import aiohttp

from aiohttp import ClientError, ClientSession, ClientResponseError

from .const import API_BASE_URL, API_HEADERS, OAUTH_URL, LOGGER


class TasFuelAPI:
    """A class for handling the data retrieval from the FuelCheck API."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._client_id = client_id
        self._client_secret = client_secret
        self._session = session
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

    @backoff.on_exception(backoff.expo, ClientResponseError, max_tries=3, logger=LOGGER)
    async def _get_access_token(self) -> str:
        """
        Retrieve a new OAuth2 access token from the API.
        The token is valid for 12 hours.
        """
        if self._access_token and self._token_expiry and self._token_expiry > datetime.now():
            LOGGER.debug("Using existing, valid access token.")
            return self._access_token

        LOGGER.info("Requesting new access token.")
        # Data should be sent in the body, not as URL params
        data = {"grant_type": "client_credentials"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = await self._session.post(
                OAUTH_URL,
                data=data, # Use 'data' to send form data in the body
                auth=aiohttp.BasicAuth(self._client_id, self._client_secret),
                headers=headers,
            )
            response.raise_for_status()
            # The server sends the wrong content-type, so we ignore it during parsing
            token_data = await response.json(content_type=None)
            
            self._access_token = token_data["access_token"]
            # The token expires in 43199 seconds (12 hours). We'll be safe and refresh a bit earlier.
            expiry_seconds = int(token_data.get("expires_in", 43199))
            self._token_expiry = datetime.now() + timedelta(seconds=expiry_seconds - 60)
            
            LOGGER.info("Successfully obtained new access token.")
            return self._access_token

        except ClientResponseError as err:
            LOGGER.error("API Error getting token: %s", err)
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
        headers = {**API_HEADERS, "Authorization": f"Bearer {token}"}
        
        # The API requires a unique transactionId for each request.
        # We also add ReferenceData=True to get the full station list.
        request_body = {
            "fueltype": "All", # Fetch all types, we will filter later
            "brand": "All",
            "namedlocation": "All",
            "sortby": "price",
            "sortascending": "true",
            "transactionId": f"HA-{int(datetime.now().timestamp())}",
            "ReferenceData": "True"
        }

        try:
            LOGGER.debug("Fetching fuel prices from API.")
            response = await self._session.post(
                API_BASE_URL,
                json=request_body,
                headers=headers,
            )
            response.raise_for_status()
            data = await response.json()
            LOGGER.debug("Successfully fetched fuel prices.")
            return data

        except ClientResponseError as err:
            # If the token is invalid, the API returns a 401
            if err.status == 401:
                LOGGER.warning("Access token rejected, requesting a new one.")
                self._access_token = None # Force a new token on next call
            raise
        except Exception as err:
            LOGGER.error("Unexpected error fetching prices: %s", err)
            raise
