from datetime import timedelta
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, TAP_STATUS_CARBONATING
from .coordinator import TapCocktailCoordinator


def option_to_duration(option: str) -> timedelta:
    """Convert a carbonation option to a timedelta."""

    mapping = {
        "2 timer": timedelta(hours=2),
        "24 timer": timedelta(hours=24),
        "48 timer": timedelta(hours=48),
    }

    return mapping.get(
        option,
        timedelta(hours=24),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up TapCocktail buttons."""
    coordinator: TapCocktailCoordinator = (
        hass.data[DOMAIN][entry.entry_id]
    )
    entities = []
    for tap in range(1, coordinator.max_taps + 1):
        entities.append(
            TapCocktailStartButton(
                coordinator,
                hass,
                str(tap),
            )
        )
        entities.append(
            TapCocktailStopButton(
                coordinator,
                hass,
                str(tap),
            )
        )
    async_add_entities(entities)


class TapCocktailStartButton(
    CoordinatorEntity,
    ButtonEntity,
):
    """Start carbonation."""

    _attr_icon = "mdi:play-circle"

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hass,
        tap,
    ):
        super().__init__(coordinator)
        self.hass = hass
        self._tap = tap
        self._attr_name = (
            f"Hane {tap} Start Karbonering"
        )
        self._attr_unique_id = (
            f"tapcocktail_hane_{tap}_start"
        )

    @property
    def available(self) -> bool:
        """Kun mulig når hanen ikke karbonerer."""
        tap = self.coordinator.get_tap(self._tap)
        return tap.get("status") != TAP_STATUS_CARBONATING

    async def async_press(self):
        """Start carbonation."""

        select = self.hass.states.get(
            f"select.hane_{self._tap}_karbonering"
        )

        if select:
            duration = option_to_duration(
                select.state
            )
        else:
            duration = timedelta(hours=24)

        await self.coordinator.start_carbonation(
            self._tap,
            duration,
        )


class TapCocktailStopButton(
    CoordinatorEntity,
    ButtonEntity,
):
    """Stop carbonation."""

    _attr_icon = "mdi:stop-circle"

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hass,
        tap,
    ):
        super().__init__(coordinator)
        self.hass = hass
        self._tap = tap
        self._attr_name = (
            f"Hane {tap} Stop Karbonering"
        )
        self._attr_unique_id = (
            f"tapcocktail_hane_{tap}_stop"
        )

    @property
    def available(self) -> bool:
        """Kun mulig mens karbonering er i gang."""
        tap = self.coordinator.get_tap(self._tap)
        return tap.get("status") == TAP_STATUS_CARBONATING

    async def async_press(self):
        """Stop carbonation."""
        await self.coordinator.stop_carbonation(
            self._tap,
        )