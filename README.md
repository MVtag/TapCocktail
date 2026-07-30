# 🍹 TapCocktail

**TapCocktail** is a custom Home Assistant integration for managing cocktails, mocktails, lemonades and other drinks served from draft taps and Cornelius kegs.

Create recipes in the Home Assistant UI, assign drinks to up to eight taps, control carbonation, track shelf life and show the current drink on dashboards and an optional round ESPHome display.

## ✨ Features

- Create, edit and delete drinks from **Settings → Devices & services → TapCocktail → Configure**
- Configure **1–8 taps**
- Organize drinks as cocktails, mocktails, lemonades and other categories
- Store **1–12 ingredients** per recipe
- Scale recipes for one glass, 2-litre and 9-litre kegs
- Calculate finished-drink ABV from ingredient amounts and alcohol percentages
- Built-in themes, icons and colours, with optional custom values
- Store CO₂ volume, serving temperature, glass type and serving tips
- Preset, recommended, custom or unlimited keg shelf life
- Restore tap selections and carbonation state after restarts
- Danish and English translations
- Sensors, selects and buttons for dashboards and automations
- Optional [TapCocktail Card](https://github.com/MVtag/tapcocktail-card)
- Optional LILYGO T-RGB 2.1-inch ESPHome tap display

## 🚰 Tap management

Each tap provides a drink selector, a 2/24/48-hour carbonation selector, start and stop buttons, status, progress, remaining time, expected finish time and time on tap. The selected-drink sensor exposes recipe data including ABV, CO₂, temperature, colour, icon, ingredients and shelf-life status.

## 📦 Installation

### HACS

1. Open HACS.
2. Search for **TapCocktail**.
3. Download the integration.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration** and select **TapCocktail**.

If TapCocktail is not listed in your HACS catalogue yet, add this repository as a custom **Integration** repository:

```text
https://github.com/MVtag/TapCocktail
```

### Manual installation

1. Download or clone this repository.
2. Copy `custom_components/tapcocktail` to `/config/custom_components/tapcocktail`.
3. Restart Home Assistant.
4. Add **TapCocktail** from **Settings → Devices & services**.

## ⚙️ First setup

1. Choose the number of taps.
2. Open **TapCocktail → Configure**.
3. Create or edit a recipe.
4. Select a drink and carbonation duration for a tap.
5. Press **Start carbonation**.

Recipes are stored as JSON under:

```text
/config/cocktails/<category>/
```

## 🧮 ABV and shelf life

Each ingredient can have an alcohol percentage. TapCocktail calculates the finished ABV from the ingredient amounts, or you can disable automatic calculation and enter ABV manually.

Shelf life supports:

- Recommended value based on category
- 3, 5, 7, 14 or 30 days
- A custom number of days
- No expiration date

When a tap becomes ready, TapCocktail calculates time on tap, days remaining and whether the drink is fresh, near its recommended limit or overdue.

## 📊 TapCocktail Card

Install [TapCocktail Card](https://github.com/MVtag/tapcocktail-card) for a visual Lovelace card with drink selection, carbonation controls, recipe view, animated bubbles, time on tap and green/orange/red shelf-life status.

```yaml
type: custom:tapcocktail-card
tap: 1
name: Hane 1
```

## 🖥️ LILYGO T-RGB ESPHome display

The package in [`esphome/packages/tapcocktail-display.yaml`](esphome/packages/tapcocktail-display.yaml) supports the **LILYGO T-RGB 2.1-inch ESP32-S3 display with FT3267 touch**.

It shows:

- Drink colour, icon, name, ABV, CO₂, temperature and glass
- Animated CO₂ bubbles
- Carbonation status and remaining time
- **KLAR TIL SERVERING** screen
- Shelf-life days remaining in green or orange
- Overdue shelf life in red
- Touch switching between the ready screen and drink information

Create a small device YAML in ESPHome:

```yaml
substitutions:
  tap: "1"

esphome:
  name: tapcocktail-display-hane-1
  friendly_name: TapCocktail Display Hane 1

packages:
  tapcocktail_display:
    url: https://github.com/MVtag/TapCocktail
    ref: main
    file: esphome/packages/tapcocktail-display.yaml
    refresh: 1d

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

api:
ota:
  - platform: esphome
logger:
```

For the next display, copy the device YAML and change both the names and `tap: "2"`. The same package supports taps 1–8.

## 🏠 Main entities

For every enabled tap, TapCocktail creates:

- `sensor.tapcocktail_hane_<number>`
- `sensor.hane_<number>_status`
- `sensor.hane_<number>_progress`
- `sensor.hane_<number>_remaining`
- `sensor.hane_<number>_faerdig`
- `sensor.hane_<number>_tid_pa_fad`
- Cocktail and carbonation selects
- Start and stop buttons

## 🗺️ Planned features

- Keg pressure and temperature sensors
- Remaining-volume estimation
- Drink and serving statistics
- Ingredient library, pricing and stock management

## ❤️ Contributing

Ideas, bug reports and pull requests are welcome.

## License

MIT License
