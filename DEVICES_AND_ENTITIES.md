# Guide: Devices and Entities

This guide provides a detailed breakdown of all the devices and entities created by the Tasmanian Fuel Prices integration. Understanding these components will help you make the most of the integration and build powerful automations.

## Device Structure

The integration organizes its entities into several devices to make them easier to manage.

* **Main Device (`Tasmanian Fuel Prices`)**: This is the primary device that holds all the central control, summary, and diagnostic entities.
* **Fuel Type Devices (`Tasmanian Fuel Prices - [Fuel Type]`)**: A separate device is created for each fuel type you monitor (e.g., `Tasmanian Fuel Prices - U91`). These devices contain the individual price sensors for every station selling that fuel, helping to group the large number of entities logically.

---

## Main Device Entities

You can find the following entities within the main "Tasmanian Fuel Prices" device.

### Select Entity

* **`select.tasmanian_fuel_prices_fuel_type_selector`**
    * **Description**: A dropdown menu that allows you to select which fuel type is displayed on the interactive Lovelace card. The options in the dropdown are determined by the fuel types you selected during the integration's configuration.
    * **State**: The currently selected fuel type (e.g., `P98`).

### Summary Sensors

Two summary sensors are created for each monitored fuel type. Their state always reflects the cheapest *discounted* price. These are powerful tools for automations.

* **`sensor.[fuel_type]_cheapest_near_me`**
    * **Description**: Shows the cheapest fuel price from stations that are within the range you configured.
    * **State**: The lowest price (in dollars or cents, based on your config).

* **`sensor.[fuel_type]_cheapest_filtered`**
    * **Description**: Shows the cheapest fuel price after excluding any distributors or operators you chose to ignore during setup.
    * **State**: The lowest price from the filtered list.

* **Key Attribute: `stations`**
    * Both summary sensors have a `stations` attribute which is a list containing detailed information about the cheapest station(s). It includes the cheapest overall station and, if different, the cheapest station that also has tyre inflation.
    * Each entry in the list contains the station's `name`, `address`, `discounted_price`, `distributor`, `operator`, and `distance`. This attribute is perfect for creating detailed notifications.

### Diagnostic Sensors & Buttons

These entities help you monitor the integration's health and manually trigger updates. They all have the `DIAGNOSTIC` entity category.

* **`sensor.access_token_expiry`**: Shows the exact date and time when the API access token will expire.
* **`sensor.prices_last_updated`**: A timestamp of the last successful fuel price update from the API.
* **`sensor.additional_data_last_updated`**: A timestamp of the last successful update of discount/amenity data from GitHub.
* **`button.refresh_access_token`**: Manually forces a refresh of the API access token.
* **`button.refresh_fuel_prices`**: Manually triggers a poll of the FuelCheck API for new prices.
* **`button.refresh_discount_amenity_data`**: Manually triggers a refresh of the community-sourced data.

---

## Fuel Price Sensor Entities

These are the individual sensors for each station and fuel type, located within their respective fuel type devices (e.g., inside "Tasmanian Fuel Prices - P98").

* **Entity ID Format**: `sensor.tas_fuel_prices_[station_code]_[fuel_type]`
    * **Example**: `sensor.tas_fuel_prices_211_p98`
* **Description**: Represents the price of a specific fuel at a single station.
* **State**: The price of the fuel, formatted in dollars or cents based on your configuration. The state reflects the price *after* any applicable discounts have been subtracted. If the price is unavailable, the state will be `unknown`.

### Key Attributes for Price Sensors

These attributes provide rich data for use in Lovelace cards and automations.

* **`address`**: The street address of the station.
* **`brand`**: The primary brand of the station (from the API).
* **`distributor`**: The fuel distributor, based on community data.
* **`operator`**: The site operator, based on community data.
* **`discount_applied`**: The value of the discount that was subtracted from the price (e.g., `0.04`).
* **`discount_provider`**: The name of the discount provider (e.g., `Coles`).
* **`user_favourite`**: `true` if the station is in your list of favourites, otherwise `false`.
* **`tyre_inflation`**: `true` if the station is known to have tyre inflation facilities.
* **`distance`**: The calculated distance from your location entity to the station (e.g., `2.75 km`).
* **`in_range`**: `true` if the station's distance is within the range you configured.
* **`all_prices_at_station`**: A list of all fuel types and their current prices available at that specific station.