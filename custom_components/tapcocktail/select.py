from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CARBONATION_OPTIONS,
    DOMAIN,
)
from .coordinator import TapCocktailCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapCocktail select entities."""
    coordinator: TapCocktailCoordinator = hass.data[DOMAIN][entry.entry_id]

    entity_registry = er.async_get(hass)
    legacy_entity_id = entity_registry.async_get_entity_id(
        "select",
        DOMAIN,
        "tapcocktail_carbonation_room_temperature_sensor",
    )
    if legacy_entity_id:
        entity_registry.async_remove(legacy_entity_id)

    entities: list[SelectEntity] = []

    for tap_number in range(1, coordinator.max_taps + 1):
        tap = str(tap_number)
        entities.extend(
            [
                TapCocktailCocktailSelect(coordinator, tap),
                TapCocktailCarbonationSelect(coordinator, tap),
            ]
        )

    async_add_entities(entities)



class TapCocktailCocktailSelect(
    CoordinatorEntity[TapCocktailCoordinator],
    SelectEntity,
):
    """Select the cocktail connected to one tap."""

    _attr_icon = "mdi:glass-cocktail"

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        tap: str,
    ) -> None:
        super().__init__(coordinator)

        self._tap = tap
        self._attr_name = f"Hane {tap} Cocktail"
        self._attr_unique_id = f"tapcocktail_hane_{tap}_cocktail"

    def _stored_option(self) -> str | None:
        """Return the last explicitly saved option for this tap."""
        option = self.coordinator.stored_selections.get(
            f"select.hane_{self._tap}_cocktail"
        )
        if not isinstance(option, str) or option == "Ingen":
            return None
        return option

    @property
    def options(self) -> list[str]:
        """Return all available cocktails without invalidating a saved choice."""
        options = self.coordinator.get_cocktail_options()
        tap = self.coordinator.get_tap(self._tap)
        cocktail_id = tap.get("cocktail")

        if isinstance(cocktail_id, str) and cocktail_id:
            current_option = self.coordinator.get_cocktail_option(cocktail_id)
            saved_option = self._stored_option()

            # Only keep the stored label as a fallback while the cocktail is
            # genuinely unavailable. If its icon or name changed, the current
            # library label replaces the stale stored label instead of showing
            # both options for the same cocktail.
            if (
                current_option is None
                and saved_option
                and saved_option not in options
            ):
                options.append(saved_option)

        return options

    @property
    def current_option(self) -> str | None:
        """Return the selected cocktail label."""
        tap = self.coordinator.get_tap(self._tap)
        cocktail_id = tap.get("cocktail")

        if not isinstance(cocktail_id, str) or not cocktail_id:
            return "Ingen"

        return (
            self.coordinator.get_cocktail_option(cocktail_id)
            or self._stored_option()
        )

    async def async_select_option(self, option: str) -> None:
        """Select a cocktail and reset the tap state."""
        if option not in self.options:
            return

        await self.coordinator.async_select_cocktail(self._tap, option)


class TapCocktailCarbonationSelect(
    CoordinatorEntity[TapCocktailCoordinator],
    RestoreEntity,
    SelectEntity,
):
    """Select the carbonation duration for one tap."""

    _attr_icon = "mdi:timer-cog"

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        tap: str,
    ) -> None:
        super().__init__(coordinator)

        self._tap = tap
        self._attr_name = f"Hane {tap} Karbonering"
        self._attr_unique_id = f"tapcocktail_hane_{tap}_karbonering"
        self._attr_options = CARBONATION_OPTIONS
        self._attr_current_option = "24 timer"

    async def async_added_to_hass(self) -> None:
        """Restore the most recently selected duration."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()

        if (
            last_state is not None
            and last_state.state in CARBONATION_OPTIONS
        ):
            self._attr_current_option = last_state.state

    @property
    def current_option(self) -> str:
        """Return the current duration."""
        return self._attr_current_option

    async def async_select_option(self, option: str) -> None:
        """Select a carbonation duration."""
        if option not in CARBONATION_OPTIONS:
            return

        self._attr_current_option = option
        self.async_write_ha_state()
