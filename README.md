# **Tasmanian Fuel Prices Integration for Home Assistant**

This is a custom integration for Home Assistant to monitor fuel prices in Tasmania, using the FuelCheck TAS API.

It provides sensors for the cheapest fuel stations based on your selected fuel type, as well as sensors for your favourite stations.

## **Features**

* Configurable through the Home Assistant UI.  
* Retrieves prices for various fuel types (U91, P95, P98, Diesel, etc.).  
* Creates sensors for the 5 cheapest stations for a selected fuel type.  
* Creates sensors for up to 5 of your favourite fuel stations.  
* Automatically manages API authentication (OAuth2) and refreshes data hourly.

## **Installation**

### **Prerequisites**

1. You must have [HACS (Home Assistant Community Store)](https://hacs.xyz/) installed.  
2. You must have a Client ID and Client Secret for the [NSW FuelCheck API](https://api.nsw.gov.au/Product/Index/22). (Note: This API also provides data for Tasmania).

### **Installation via HACS**

1. Open HACS in your Home Assistant instance.  
2. Go to **Integrations**.  
3. Click the three dots in the top right corner and select **Custom repositories**.  
4. In the "Repository" field, paste the URL to your GitHub repository.  
5. For "Category", select **Integration**.  
6. Click **Add**.  
7. The "Tasmanian Fuel Prices" integration will now appear in your HACS integrations list. Click on it and then click **Download**.  
8. Restart Home Assistant.

## **Configuration**

After installation, you need to configure the integration:

1. Navigate to **Settings** \> **Devices & Services**.  
2. Click the **\+ ADD INTEGRATION** button in the bottom right.  
3. Search for "Tasmanian Fuel Prices" and click on it.  
4. A configuration dialog will appear. Enter the following details:  
   * **Client ID**: Your API Key from the FuelCheck API developer portal.  
   * **Client Secret**: Your API Secret from the FuelCheck API developer portal.  
5. Click **Submit**. The integration will test the credentials.  
6. If successful, a new dialog will appear for options:  
   * **Fuel Type**: Select your desired fuel type (e.g., U91, E10, P95, P98, Diesel).  
   * **Favourite Stations**: Enter up to 5 station codes for your favourite locations. These are the unique identifiers for each station found in the API data.  
7. Click **Submit**.

The integration will now be set up and your sensors will be created. You can find them in your list of entities.

## **Sensors**

The integration will create two types of sensors:

1. **Cheapest Fuel**: Five sensors named sensor.tas\_fuel\_cheapest\_\<station\_name\>.  
   * The state of the sensor is the price of the fuel.  
   * Attributes include the station's address, fuel type, and the last time the price was updated.  
2. **Favourite Stations**: Up to five sensors named sensor.tas\_fuel\_favourite\_\<station\_name\>.  
   * The state of the sensor is the price of the fuel at that station.  
   * Attributes include the station's address, fuel type, and the last time the price was updated.

*This integration is not affiliated with or endorsed by the NSW Government or any fuel provider.*
