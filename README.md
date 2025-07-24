# Tasmanian Fuel Prices Integration for Home Assistant

Welcome to the Tasmanian Fuel Prices integration for Home Assistant! This component allows you to monitor fuel prices across Tasmania, leveraging the official FuelCheck TAS API. Unlike the official apps, this integration can automatically apply your selected discount programs to show you the *actual* price you'll pay at the pump. It's designed to be powerful yet easy to use, helping you find the cheapest fuel, track prices at your favourite stations, and make informed decisions.

## Screenshots

<table align="center">
  <tr>
    <td valign="top"><img src="https://github.com/ziogref/TAS-Fuel-HA-Intergration/blob/main/assets/lovelace_card.png" width="270" alt="Lovelace Card View"></td>
    <td valign="top"><img src="https://github.com/ziogref/TAS-Fuel-HA-Intergration/blob/main/assets/device_overview.png" width="270" alt="Devices View"></td>
    <td valign="top"><img src="https://github.com/ziogref/TAS-Fuel-HA-Intergration/blob/main/assets/main_device.png" width="270" alt="Main Devices View"></td>
  </tr>
</table>

## Key Features

* **See the *Real* Price**: Unlike the official apps, this integration automatically applies your selected discount programs (Woolworths, Coles, RACT, United) to show the final price you'll pay at the pump.
* **Simple UI Configuration**: Set up and configure the integration entirely through the Home Assistant user interface.
* **Multiple Fuel Types**: Monitor prices for all major fuel types, including U91, P95, P98, Diesel, LPG, and more.
* **Favourite Station Tracking**: Create dedicated sensors for your most visited stations for at-a-glance price checks.
* **Geolocation Aware (Optional)**: By linking the integration to your phone's location via the Home Assistant Companion App, you can calculate the real-time distance to stations and filter to see only those within a set range.
* **Amenity Tracking**: Keep track of which stations have tyre inflation facilities, based on community-sourced data.
* **Smart Summary Sensors**: Two types of summary sensors are created for each fuel type, which are ideal for use in automations:
    * **Cheapest Near Me**: Shows the cheapest station(s) within your defined range.
    * **Cheapest Filtered**: Excludes brands or operators you don't use to find the cheapest fuel that's right for you.
* **Diagnostic Tools**: Includes sensors to monitor API status and buttons to manually refresh data whenever you need to.

## Data Refresh Cycles

The integration automatically keeps your data up-to-date through several refresh cycles:
* **Fuel Prices**: Fetched from the API every hour.
* **Community Data**: Discount and amenity information is updated from GitHub once every 24 hours.
* **Distance Calculations**: The distance to stations is recalculated instantly whenever your location entity updates (e.g., as you are driving). This does not trigger a full API poll but ensures the "in range" status is always current.

## Prerequisites

1.  **HACS**: You must have the [Home Assistant Community Store (HACS)](https://hacs.xyz/) installed.
2.  **API Credentials**: You will need a free **API Key** and **API Secret**. The Tasmanian fuel price data is hosted on the NSW Government's API platform, so you must sign up at the [NSW API portal](https://api.nsw.gov.au/Product/Index/22) to get your credentials.

### Installation & Configuration

#### Installation

Once this integration is available in the default HACS repository, users can install it with the following steps:

1.  Open HACS in your Home Assistant instance.
2.  Go to **Integrations**.
3.  Click the blue **+ EXPLORE & DOWNLOAD REPOSITORIES** button in the bottom right.
4.  Search for "Tasmanian Fuel Prices" and click on the result.
5.  Click the **DOWNLOAD** button and follow the on-screen instructions.
6.  Restart Home Assistant as prompted.

#### Configuration

1.  Navigate to **Settings** > **Devices & Services**.
2.  Click **+ ADD INTEGRATION** and search for "Tasmanian Fuel Prices".
3.  Enter your **API Key** and **API Secret** from the developer portal.
4.  If the credentials are valid, you will be guided through a series of configuration steps to select fuel types, favourite stations, discount programs, and more. Follow the on-screen instructions.

### What This Integration Creates

Once configured, the integration creates the devices and entities needed to monitor fuel prices. It's important to note that a unique sensor entity is created for **every station for each fuel type you choose to monitor**. For example, if you monitor 3 fuel types, and there are 250 stations, over 750 sensor entities will be created.

These entities are organized into devices to keep things manageable:

* **A main device**: Named "Tasmanian Fuel Prices," this device holds the primary control entities (like the Fuel Type Selector), all diagnostic buttons and sensors, and the summary sensors for each fuel type.
* **A separate device for each fuel type**: To make Browse easier, a dedicated device is created for each fuel type you monitor (e.g., "Tasmanian Fuel Prices - U91"). These devices contain all the individual price sensor entities for every station that sells that specific fuel.

For a detailed breakdown of every entity and its attributes, please see our **[Devices and Entities Guide](DEVICES_AND_ENTITIES.md)**.

## Usage Guides

Take your fuel price monitoring to the next level with our advanced usage guides:

* **[Interactive Lovelace Card Guide](LovelaceCard.md)**: A step-by-step guide to creating a dynamic dashboard card that lets you switch fuel types and see sorted price lists.
* **[Automation & Scripting Guide](AUTOMATIONS.md)**: Examples of how to create notifications for price drops, daily fuel reports, and more.

## Community-Sourced Data

The official API provides prices but lacks information on which stations participate in specific discount programs (like Woolworths, Coles, RACT, and United) or offer amenities like tyre inflation. To solve this, this integration pulls supplementary data from a community-maintained repository.

[**TAS-Fuel-HA-Additional-Data Repository**](https://github.com/ziogref/TAS-Fuel-HA-Additional-Data)

We encourage all users to contribute! If you find a station that's missing a discount or has a new tyre inflator, please help us keep the data accurate for everyone. The repository's README explains how.

## Disclaimer

*The codebase for this project was written by Google Gemini, based on instructions, direction, and code review from Ziogref.*

*This integration is not affiliated with, endorsed by, or connected to the NSW Government, the Tasmanian Government, the official FuelCheck NSW app (fuelcheck.nsw.gov.au), or the official FuelCheck TAS app (fuelcheck.tas.gov.au).*
