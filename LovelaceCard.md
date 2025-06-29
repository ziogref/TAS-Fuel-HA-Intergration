# Guide: Dynamic Fuel Price Lovelace Card

### Objective

This guide will show you how to create a single Lovelace card that displays:

1.  An automatically populated list of your "Favourite" fuel stations at the top, sorted by price.
2.  A dynamic list of all other fuel stations, also automatically sorted from cheapest to most expensive.
3.  The ability to exclude specific brands (e.g., United) from the dynamic list.

---

### Part 1: Prerequisites

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

We will use the `vertical-stack-in-card` to combine two different cards into a single, seamless element on your dashboard.

1.  Navigate to the dashboard where you want to add the card and click the three dots in the top right, then select "**Edit Dashboard**".
2.  Click the "**+ ADD CARD**" button.
3.  Scroll to the bottom of the list and select the "**Manual**" card.
4.  Delete the placeholder content (`type: entities`) and paste the YAML code from the section below.

---

### Part 3: The YAML Code

Copy the entire code block below and paste it into the Manual card editor. Explanations for each section are provided below the code.

```yaml
type: custom:vertical-stack-in-card
title: Unleaded 91 Prices
cards:
  - type: custom:auto-entities
    card:
      type: entities
      title: '⭐ My Favourites'
      show_header_toggle: false
    filter:
      include:
        - entity_id: '*_u91'
          attributes:
            user_favourite: true
    sort:
      method: state
      numeric: true
  - type: custom:auto-entities
    card:
      type: entities
      show_header_toggle: false
    filter:
      include:
        - entity_id: '*_u91'
      exclude:
        - attributes:
            user_favourite: true
        - attributes:
            brand: United
    sort:
      method: state
      numeric: true
```

---

### How This Code Works

* **`type: custom:vertical-stack-in-card`**: This is the container that holds our two cards and makes them look like a single element.
* **`title: Unleaded 91 Prices`**: The main title for the entire card. You can change this to whatever you like.

#### Card 1: Your Favourites (Dynamic)

* **`filter:`**: 
    * **`include:`**: This uses the standard filter syntax. Placing `entity_id` and `attributes` in the same list item creates an **AND** condition. It will only include sensors that match the `entity_id` glob **AND** have the attribute `user_favourite: true`.
* **`sort: { method: state, numeric: true }`**: Sorts your favourites by price (cheapest first).

#### Card 2: The Main List (Dynamic)

* **`filter:`**:
    * **`include:`**: This first grabs all sensors matching the `entity_id` glob (e.g., `*_u91`). **You must change this** to match the fuel type you want to display.
    * **`exclude:`**: This then removes entities from the list. We have two separate rules: one removes any sensor with `user_favourite: true`, and the other removes any sensor where the `brand` is "United".
* **`sort:`**: This sorts the remaining list by price.

After pasting the YAML, click "**SAVE**". This non-template version is cleaner and should now work as intended.
