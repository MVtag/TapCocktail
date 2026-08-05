from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CARBONATION_OPTIONS,
    CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR,
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

    entities: list[SelectEntity] = [
        TapCocktailCarbonationRoomTemperatureSelect(hass, entry),
    ]

    for tap_number in range(1, coordinator.max_taps + 1):
        tap = str(tap_number)
        entities.extend(
            [
                TapCocktailCocktailSelect(coordinator, tap),
                TapCocktailCarbonationSelect(coordinator, tap),
            ]
        )

    async_add_entities(entities)


class TapCocktailCarbonationRoomTemperatureSelect(SelectEntity):
    """Select the shared temperature sensor for the carbonation room."""

    _attr_icon = "mdi:thermometer-lines"
    _attr_name = "Karboneringsrum Temperatursensor"
    _attr_unique_id = "tapcocktail_carbonation_room_temperature_sensor"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self._hass = hass
        self._entry = entry

    @property
    def options(self) -> list[str]:
        """Return all available Home Assistant temperature sensors."""
        sensor_options = sorted(
            state.entity_id
            for state in self._hass.states.async_all("sensor")
            if state.attributes.get("device_class") == "temperature"
        )

        current = self._entry.options.get(
            CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR
        )
        if (
            isinstance(current, str)
            and current
            and current not in sensor_options
        ):
            sensor_options.append(current)

        return ["Ingen"] + sensor_options

    @property
    def current_option(self) -> str:
        """Return the selected shared carbonation-room sensor."""
        current = self._entry.options.get(
            CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR
        )
        return str(current) if current else "Ingen"

    async def async_select_option(self, option: str) -> None:
        """Save the shared carbonation-room temperature sensor."""
        if option not in self.options:
            return

        new_options = dict(self._entry.options)
        if option == "Ingen":
            new_options.pop(
                CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR,
                None,
            )
        else:
            new_options[
                CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR
            ] = option

        self._hass.config_entries.async_update_entry(
            self._entry,
            options=new_options,
        )
        self.async_write_ha_state()


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
