# 🍹 TapCocktail

**TapCocktail** is a custom Home Assistant integration for managing cocktails served from draft taps and Cornelius kegs.

Assign cocktails to individual taps, load recipes from JSON files, and display beautiful dashboards with serving information such as carbonation, temperature, alcohol content, glass recommendations and more.

---

## ✨ Features

- 🍸 Assign cocktails to each tap
- 📂 Load cocktails from JSON files
- 🫧 Display carbonation (Vol. CO₂)
- 🌡️ Recommended serving temperature
- 🥃 Alcohol percentage (ABV)
- 🍹 Glass recommendations
- 💡 Serving tips
- 🎨 Cocktail colors and icons
- 🔄 Automatic reload when cocktail files are updated
- 🏠 Native Home Assistant entities
- 📊 Dashboard friendly sensors

---

## 📸 Preview

*Screenshots coming soon.*

---

## 📦 Installation

### Manual

1. Copy the `custom_components/tapcocktail` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services**.
4. Add the **TapCocktail** integration.

---

## 🍸 Cocktail Library

Cocktails are stored as simple JSON files, making it easy to add or edit recipes.

Example:

```json
{
  "id": "gin_hass",
  "navn": "Gin Hass",
  "kategori": "Cocktail",
  "ikon": "🍹",
  "abv": 8,
  "co2": 2.3,
  "temperatur": 3,
  "glas": "Highball"
}
```

---

## 🚀 Planned Features

- HACS support
- Keg pressure monitoring
- Temperature sensors
- Remaining volume estimation
- Cocktail statistics
- Multiple taps
- Dashboard cards

---

## ❤️ Contributing

Ideas, bug reports and pull requests are always welcome.

---

## 🍻 About

TapCocktail was created for Home Assistant users who enjoy serving professional-quality cocktails from Cornelius kegs and draft systems.

Cheers! 🍹