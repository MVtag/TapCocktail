from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CARBONATION_OPTIONS, DOMAIN
from .coordinator import TapCocktailCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapCocktail select entities."""
    coordinator: TapCocktailCoordinator = hass.data[DOMAIN][entry.entry_id]

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

    @property
    def options(self) -> list[str]:
        """Return all available cocktails."""
        return self.coordinator.get_cocktail_options()

    @property
    def current_option(self) -> str | None:
        """Return the selected cocktail label."""
        tap = self.coordinator.get_tap(self._tap)
        cocktail_id = tap.get("cocktail")

        if not isinstance(cocktail_id, str) or not cocktail_id:
            return "Ingen"

        return self.coordinator.get_cocktail_option(cocktail_id) or "Ingen"

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
