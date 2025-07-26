# Guide: Automation Examples

The Tasmanian Fuel Prices integration provides a wealth of data that is perfect for creating powerful automations. This guide offers some practical examples to get you started. You can add these directly to your `automations.yaml` file or create them using the Home Assistant UI.

---

### Example 1: Price Drop Alert for a Favourite Station

**Goal:** Receive a notification on your phone when the price of P98 at the "U-Go Lindisfarne" station (station code 211) drops below $1.90.

**What this does:** This automation uses a `numeric_state` trigger to watch a specific fuel price sensor. When the price (which is the sensor's state) falls below the target value, it sends a detailed notification to your phone.

**What you need to change:**
* `entity_id`: Change `sensor.tas_fuel_prices_211_p98` to the entity ID of the station and fuel type you want to monitor. Remember the format is `sensor.tas_fuel_prices_[station_code]_[fuel_type]`.
* `below: '1.90'`: Adjust this to your desired price threshold.
* `notify.mobile_app_your_phone`: Replace this with the name of your own notification service.

#### Automation YAML:

```yaml
alias: "Fuel Price Alert: P98 at Lindisfarne"
description: "Notifies when P98 at U-Go Lindisfarne is below $1.90"
trigger:
  - platform: numeric_state
    entity_id: sensor.tas_fuel_prices_211_p98
    below: '1.90'
condition:
  # This condition prevents the automation from triggering if the price is unknown
  - condition: template
    value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] }}"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "⛽ Cheap Fuel Alert!"
      message: >-
        The price for {{ state_attr(trigger.entity_id, 'fuel_type') }} at {{ state_attr(trigger.entity_id, 'name') }} has dropped to ${{ trigger.to_state.state }}!
mode: single

### Example 2: Daily Cheapest Fuel Report

**Goal:** Every morning at 8 AM, get a notification showing the cheapest "filtered" station for U91 fuel, including its name, address, and price.

**What this does:** This automation uses a `time` trigger to run daily. It then uses the `stations` attribute of the "Cheapest Filtered" summary sensor to gather details about the cheapest station and formats them into a clean notification.

**What you need to change:**

* `sensor.u91_cheapest_filtered`: If you want to track a different fuel type, change this to the corresponding summary sensor (e.g., `sensor.p98_cheapest_filtered`).
* `notify.mobile_app_your_phone`: Replace this with your notification service.

#### Automation YAML:

```yaml
alias: "Daily Cheapest U91 Report"
description: "Sends the cheapest filtered U91 station every morning at 8 AM"
trigger:
  - platform: time
    at: "08:00:00"
condition:
  # This condition ensures the automation only runs if the summary sensor has data
  - condition: template
    value_template: "{{ state_attr('sensor.u91_cheapest_filtered', 'stations') | length > 0 }}"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "⛽ Daily U91 Fuel Report"
      message: >-
        The cheapest U91 today is at {{ state_attr('sensor.u91_cheapest_filtered', 'stations')[0].name }}. 
        Price: ${{ state_attr('sensor.u91_cheapest_filtered', 'stations')[0].discounted_price }}
        Address: {{ state_attr('sensor.u91_cheapest_filtered', 'stations')[0].address }}
mode: single

These examples should provide a solid foundation for building your own custom fuel price automations.