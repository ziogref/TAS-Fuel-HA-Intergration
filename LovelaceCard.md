# Guide: Interactive Fuel Price Card with Dropdown

### Objective

This guide will show you how to create a single, powerful Lovelace card that:

1.  Displays a dropdown menu to select the fuel type you want to view.
2.  Based on your selection, automatically populates a list of your "Favourite" fuel stations, sorted by price.
3.  Displays a dynamic list of all other stations for the selected fuel type, also sorted by price.
4.  **Automatically** hides stations based on the excluded distributors and operators you set in the integration's configuration.
5.  Automatically hides any station whose price is currently "Unknown".

---

### Part 1: Prerequisites (Custom Cards)

This card requires two custom frontend components from the Home Assistant Community Store (HACS).

1.  **Install HACS:** If you haven't already, install [HACS](https://hacs.xyz/) in your Home Assistant instance.
2.  **Install Required Cards via HACS:**
    * Open HACS in your Home Assistant sidebar.
    * Go to the "Frontend" section.
    * Click the blue "+ EXPLORE & DOWNLOAD REPOSITORIES" button.
    * Search for and download each of the following cards:
        * **`auto-entities`**
        * **`vertical-stack-in-card`**
    * Follow the on-screen instructions for both. A Home Assistant restart may be required after installation.

---

### Part 2: Creating the Lovelace Card

1.  Navigate to the dashboard where you want to add the card and click the three dots in the top right, then select "**Edit Dashboard**".
2.  Click the "**+ ADD CARD**" button.
3.  Scroll to the bottom of the list and select the "**Manual**" card.
4.  Delete the placeholder content (`type: entities`) and paste the YAML code from the section below.

---

### Part 3: The YAML Code

Copy the entire code block below and paste it into the Manual card editor. This new version is fully automatic and requires no manual editing of exclusion lists.

```yaml
type: custom:vertical-stack-in-card
cards:
  - type: entities
    entities:
      - entity: select.tasmanian_fuel_prices_fuel_type_selector
        name: Select Fuel Type
  - type: custom:auto-entities
    card:
      type: entities
      title: '⭐ My Favourites'
      show_header_toggle: false
    filter:
      template: |
        {% set selected_fuel = states('select.tasmanian_fuel_prices_fuel_type_selector') %}
        {% for state in states.sensor %}
          {% if 
            state.entity_id.startswith('sensor.tas_fuel_prices_') and
            state.entity_id.endswith('_' + selected_fuel.lower()) and 
            state.attributes.get('user_favourite') == true and 
            state.state != 'unknown' 
          %}
            {{ state.entity_id }},
          {% endif %}
        {% endfor %}
    sort:
      method: state
      numeric: true
  - type: custom:auto-entities
    card:
      type: entities
      title: '⛽ All Other Stations'
      show_header_toggle: false
    filter:
      template: |
        {% set selected_fuel = states('select.tasmanian_fuel_prices_fuel_type_selector') %}
        {% for state in states.sensor %}
          {% if
            state.entity_id.startswith('sensor.tas_fuel_prices_') and
            state.entity_id.endswith('_' + selected_fuel.lower()) and
            state.attributes.get('user_favourite') == false and
            state.attributes.get('distributor_excluded') == false and
            state.attributes.get('operator_excluded') == false and
            state.state != 'unknown'
          %}
            {{ state.entity_id }},
          {% endif %}
        {% endfor %}
    sort:
      method: state
      numeric: true
```

### Part 4: How This Code Works

* **Top Card (Input Select):** The first card in the stack displays the `select.tasmanian_fuel_prices_fuel_type_selector` entity, which is automatically created by the integration.
* **Template Filtering:**
    * `{% set selected_fuel = states('select.tasmanian_fuel_prices_fuel_type_selector') %}`: This line gets the currently selected value from the auto-created dropdown.
    * `state.entity_id.endswith('_' + selected_fuel.lower())`: The template uses this `selected_fuel` variable to dynamically filter the sensors. We use `.lower()` to ensure the match works correctly even if the case is different. When you change the dropdown, the `auto-entities` card automatically re-runs the filter and updates the list.

After pasting the YAML, click "**SAVE**". You will have a fully interactive card that allows you to switch between different fuel types without any manual setup.
