# 🍹 TapCocktail

**TapCocktail** is a custom Home Assistant integration for managing cocktails, mocktails, lemonades and other drinks served from draft taps and Cornelius kegs.

Create and maintain recipes directly from the Home Assistant UI, assign a drink to each tap, track carbonation and expose recipe data to dashboards and automations.

## ✨ Features

- 🍸 Manage recipes from **Settings → Devices & services → TapCocktail → Configure**
- ➕ Create, edit and delete drinks without editing JSON manually
- 🚰 Configure between **1 and 8 taps**
- 🗂️ Organize recipes in categories such as cocktails, mocktails and lemonades
- 🧾 Store between **1 and 12 ingredients** per recipe
- ⚖️ Calculate ingredient quantities for a glass, 2-litre keg and 9-litre keg
- 🎨 Built-in drink themes with matching icons and colours
- 🌈 Optional custom icon and colour for each recipe
- 🫧 Store recommended carbonation in Vol. CO₂
- 🌡️ Store serving temperature, ABV, glass type and serving tips
- 🔄 Automatically reload recipes when files are updated
- 💾 Restore tap selections and carbonation state after Home Assistant restarts
- 🇩🇰 Danish and 🇬🇧 English translations
- 📊 Home Assistant sensors, selects and buttons for dashboards and automations

## 🚰 Tap management

Each configured tap provides:

- A drink selector
- A carbonation duration selector: **2, 24 or 48 hours**
- Start and stop carbonation buttons
- Current tap status: `idle`, `carbonating` or `ready`
- Carbonation progress in percent
- Remaining carbonation time
- Expected finish time
- The time the drink became ready
- Recipe attributes including ingredients, ABV, CO₂, temperature, colour, icon and serving tips

The number of taps can be changed later from the TapCocktail integration options.

## 📦 Installation

### Manual installation

1. Download or clone this repository.
2. Copy `custom_components/tapcocktail` to:
   ```text
   /config/custom_components/tapcocktail
   ```
3. Restart Home Assistant.
4. Open **Settings → Devices & services**.
5. Select **Add integration** and search for **TapCocktail**.

### HACS

The repository contains the required HACS structure. A public HACS release and installation guide are planned.

## ⚙️ Configuration

After adding the integration:

1. Choose how many taps you want to manage.
2. Open **TapCocktail → Configure**.
3. Create your first recipe or manage existing recipes.
4. Select a recipe and carbonation duration for each tap.
5. Press the start button when carbonation begins.

## 🍸 Cocktail library

Recipes are stored as JSON files under:

```text
/config/cocktails/<category>/
```

Files created through the Home Assistant UI are saved automatically. They can also be edited manually.

Example:

```json
{
  "id": "gin_hass",
  "navn": "Gin Hass",
  "kategori": "cocktails",
  "tema": "tropisk",
  "ikon": "🥭",
  "farve": "#FFB000",
  "abv": 8.0,
  "co2": 2.3,
  "temperatur": 3.0,
  "glas": "Highball",
  "ingredienser": [
    {
      "navn": "Gin",
      "glas": "4 cl",
      "2_liter": "40 cl",
      "9_liter": "180 cl"
    }
  ],
  "serveringstips": "Serve ice cold over plenty of ice."
}
```

## 🏠 Home Assistant entities

TapCocktail creates a library sensor and the following entities for every enabled tap:

- Drink selection
- Carbonation duration
- Start and stop buttons
- Selected drink sensor
- Status sensor
- Progress sensor
- Remaining-time sensor
- Finish-time sensor
- Ready-since sensor

These entities can be used with standard Home Assistant cards, custom cards, scripts and automations.

## 🗺️ Planned features

- HACS release and update support
- Keg pressure monitoring
- Temperature sensor support
- Remaining keg-volume estimation
- Drink and serving statistics
- Ready-to-use dashboard cards

## ❤️ Contributing

Ideas, bug reports and pull requests are welcome.

## 🍻 About

TapCocktail was created for Home Assistant users who enjoy serving professional-quality drinks from Cornelius kegs and draft systems.

Cheers! 🍹
