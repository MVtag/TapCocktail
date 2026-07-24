import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def input_select_entity_ids(max_taps: int) -> list[str]:
    """Return input_select entity IDs for all active taps."""
    return [
        f"input_select.tapcocktail_hane_{tap}"
        for tap in range(1, max_taps + 1)
    ]


def option_to_cocktail_id(option: str | None) -> str | None:
    """Convert a dropdown label such as '🍊 Filur' to 'filur'."""
    if not option or option == "Ingen":
        return None

    return (
        option.split(" ", 1)[-1]
        .strip()
        .lower()
        .replace(" ", "_")
    )


def tap_number_from_entity_id(entity_id: str) -> str | None:
    """Extract a tap number from an input_select entity ID."""
    suffix = entity_id.rsplit("_", 1)[-1]
    return suffix if suffix.isdigit() else None


async def update_cocktail_dropdown(
    hass: HomeAssistant,
    cocktails: dict,
    stored_selections: dict,
    max_taps: int,
) -> None:
    """Update dropdown options and restore selections for active taps."""
    options: list[str] = []

    for cocktail in cocktails.values():
        icon = cocktail.get("ikon", "🍹")
        name = cocktail.get("navn")

        if name:
            options.append(f"{icon} {name}")

    options.sort()
    options.insert(0, "Ingen")

    for entity_id in input_select_entity_ids(max_taps):
        entity = hass.states.get(entity_id)

        if entity is None:
            _LOGGER.warning("TapCocktail: %s not found", entity_id)
            continue

        old_options = entity.attributes.get("options", [])
        current = entity.state
        remembered = stored_selections.get(entity_id)
        target = remembered if remembered else current

        if old_options == options and current == target:
            continue

        _LOGGER.info(
            "TapCocktail: updating options for %s (target=%s)",
            entity_id,
            target,
        )

        await hass.services.async_call(
            "input_select",
            "set_options",
            {
                "entity_id": entity_id,
                "options": options,
            },
            blocking=True,
        )

        if target and target in options:
            await hass.services.async_call(
                "input_select",
                "select_option",
                {
                    "entity_id": entity_id,
                    "option": target,
                },
                blocking=True,
            )
        elif target and target not in ("", "unknown", "unavailable"):
            _LOGGER.warning(
                "TapCocktail: '%s' no longer exists for %s",
                target,
                entity_id,
            )
