from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_config_flow() -> None:
    path = ROOT / "custom_components/tapcocktail/config_flow.py"

    replace_once(
        path,
        "from .const import (\n    CONF_MAX_TAPS,",
        "from .const import (\n    CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR,\n    CONF_MAX_TAPS,",
    )

    replace_once(
        path,
        '    """Return settings for active taps and their optional temperature sensors."""\n    fields: dict[Any, Any] = {',
        '    """Return tap settings including the shared carbonation-room sensor."""\n'
        '    current_room_sensor = options.get(\n'
        '        CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR\n'
        '    )\n'
        '    room_sensor_marker = (\n'
        '        vol.Optional(\n'
        '            CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR,\n'
        '            default=current_room_sensor,\n'
        '        )\n'
        '        if current_room_sensor\n'
        '        else vol.Optional(CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR)\n'
        '    )\n\n'
        '    fields: dict[Any, Any] = {\n'
        '        room_sensor_marker: selector(\n'
        '            {\n'
        '                "entity": {\n'
        '                    "domain": "sensor",\n'
        '                    "device_class": "temperature",\n'
        '                }\n'
        '            }\n'
        '        ),',
    )

    replace_once(
        path,
        "            for tap_number in range(1, current + 1):",
        "            selected_room_sensor = user_input.get(\n"
        "                CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR\n"
        "            )\n"
        "            if selected_room_sensor:\n"
        "                new_options[\n"
        "                    CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR\n"
        "                ] = str(selected_room_sensor)\n"
        "            else:\n"
        "                new_options.pop(\n"
        "                    CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR,\n"
        "                    None,\n"
        "                )\n\n"
        "            for tap_number in range(1, current + 1):",
    )


def patch_select_platform() -> None:
    path = ROOT / "custom_components/tapcocktail/select.py"
    text = path.read_text(encoding="utf-8")

    text = text.replace(
        "from homeassistant.helpers.entity_platform import AddEntitiesCallback\n",
        "from homeassistant.helpers import entity_registry as er\n"
        "from homeassistant.helpers.entity_platform import AddEntitiesCallback\n",
        1,
    )
    text = text.replace(
        "    CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR,\n",
        "",
        1,
    )
    text = text.replace(
        "    entities: list[SelectEntity] = [\n"
        "        TapCocktailCarbonationRoomTemperatureSelect(hass, entry),\n"
        "    ]\n",
        "    entity_registry = er.async_get(hass)\n"
        "    legacy_entity_id = entity_registry.async_get_entity_id(\n"
        "        \"select\",\n"
        "        DOMAIN,\n"
        "        \"tapcocktail_carbonation_room_temperature_sensor\",\n"
        "    )\n"
        "    if legacy_entity_id:\n"
        "        entity_registry.async_remove(legacy_entity_id)\n\n"
        "    entities: list[SelectEntity] = []\n",
        1,
    )

    pattern = re.compile(
        r"\nclass TapCocktailCarbonationRoomTemperatureSelect\(SelectEntity\):.*?(?=\nclass TapCocktailCocktailSelect)",
        re.S,
    )
    text, count = pattern.subn("\n", text, count=1)
    if count != 1:
        raise RuntimeError("Could not remove legacy carbonation-room select class")

    path.write_text(text, encoding="utf-8")


def patch_ui_text(path: Path, *, language: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    settings = data["options"]["step"]["settings"]

    if language == "en":
        settings["description"] = (
            "Select the shared temperature sensor for the carbonation room, "
            "the number of active taps, and an optional temperature sensor for each tap."
        )
        label = "Shared temperature sensor – carbonation room"
    else:
        settings["description"] = (
            "Vælg den fælles temperatursensor til karboneringsrummet, antal aktive haner "
            "og en valgfri temperatursensor til hver hane."
        )
        label = "Fælles temperatursensor – karboneringsrum"

    original = settings.get("data", {})
    reordered: dict[str, object] = {
        "carbonation_room_temperature_sensor": label,
    }
    reordered.update(original)
    settings["data"] = reordered

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def bump_version() -> None:
    path = ROOT / "custom_components/tapcocktail/manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = "2.6.0"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    patch_config_flow()
    patch_select_platform()
    patch_ui_text(ROOT / "custom_components/tapcocktail/strings.json", language="da")
    patch_ui_text(ROOT / "custom_components/tapcocktail/translations/da.json", language="da")
    patch_ui_text(ROOT / "custom_components/tapcocktail/translations/en.json", language="en")
    bump_version()


if __name__ == "__main__":
    main()
