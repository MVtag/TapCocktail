# TapCocktail ESPHome display

This ESPHome package turns a LILYGO T-RGB 2.1-inch display with FT3267 touch
into a dedicated display for one TapCocktail tap.

## Features

- Cocktail name, icon, colour, ABV, CO₂, temperature and glass type
- Animated bubbles scaled from the drink's CO₂ value
- Dedicated carbonation screen with remaining time
- `KLAR TIL SERVERING` screen when carbonation is complete
- Touch switches between the ready screen and cocktail information
- One shared package for TapCocktail tap 1 through 8

## Requirements

- Home Assistant with the TapCocktail integration
- The selected tap enabled in TapCocktail
- ESPHome
- LILYGO T-RGB 2.1-inch hardware with FT3267 touch

The working touch configuration uses:

- Platform: `ft63x6`
- I²C address: `0x38`
- Interrupt: `GPIO1`
- Reset: XL9535 pin 1

## Install a display

1. Copy the matching file from `examples` to the ESPHome configuration folder.
2. Make sure `wifi_ssid` and `wifi_password` exist in `secrets.yaml`.
3. Change the `tap` substitution if necessary.
4. Save, validate and install the configuration from ESPHome.

For tap 1:

```yaml
substitutions:
  tap: "1"
  device_name: tapcocktail-display-hane-1
  friendly_name: TapCocktail Display Hane 1
```

For tap 2, change only:

```yaml
substitutions:
  tap: "2"
  device_name: tapcocktail-display-hane-2
  friendly_name: TapCocktail Display Hane 2
```

Tap 3 through 8 use the same pattern. TapCocktail already supports between one
and eight configured taps, so no display code changes are required.

## Home Assistant entities

For `${tap}: "3"`, the package automatically reads:

```text
sensor.tapcocktail_hane_3
sensor.hane_3_status
sensor.hane_3_remaining
```

The same naming pattern is used for every tap.

## Repository structure

```text
esphome/
├── packages/
│   └── tapcocktail-display.yaml
├── examples/
│   ├── hane-1.yaml
│   ├── hane-2.yaml
│   └── hane-3.yaml
├── images/
│   └── *.png
└── README.md
```

The images are downloaded from the TapCocktail GitHub repository at compile
time, so users do not have to copy the image folder into ESPHome.

## Touch variants

This package is specifically for the FT3267 version that has been tested with
TapCocktail. Other LILYGO T-RGB 2.1-inch variants may use another touch
controller and require a separate hardware package.
