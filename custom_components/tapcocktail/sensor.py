"""Sensor platform for the TapCocktail integration."""

from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_TEMPERATURE_SENSOR_PREFIX,
    DOMAIN,
    TAP_STATUS_CARBONATING,
    TAP_STATUS_IDLE,
    TAP_STATUS_READY,
)
from .coordinator import TapCocktailCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TapCocktail sensors."""

    coordinator: TapCocktailCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        TapCocktailLibrarySensor(coordinator),
    ]

    for tap_number in range(1, coordinator.max_taps + 1):
        tap = str(tap_number)
        entities.extend(
            [
                TapCocktailHaneSensor(
                    coordinator,
                    hass,
                    tap,
                    entry.options.get(
                        f"{CONF_TEMPERATURE_SENSOR_PREFIX}_{tap}"
                    ),
                ),
                TapCocktailStatusSensor(coordinator, tap),
                TapCocktailProgressSensor(coordinator, tap),
                TapCocktailRemainingSensor(coordinator, tap),
                TapCocktailFinishedSensor(coordinator, tap),
                TapCocktailReadySinceSensor(coordinator, tap),
            ]
        )

    async_add_entities(entities)


class TapCocktailLibrarySensor(
    CoordinatorEntity[TapCocktailCoordinator],
    SensorEntity,
):
    """Expose the loaded TapCocktail library."""

    _attr_icon = "mdi:glass-cocktail"

    def __init__(self, coordinator: TapCocktailCoordinator) -> None:
        super().__init__(coordinator)

        self._attr_name = "TapCocktail Library"
        self._attr_unique_id = "tapcocktail_library"

    @property
    def native_value(self) -> int:
        """Return the number of loaded cocktails."""
        return len(self.coordinator.get_all_cocktails())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the cocktail database."""
        return {
            "cocktails": self.coordinator.get_all_cocktails(),
        }


class TapCocktailTapSensorBase(
    CoordinatorEntity[TapCocktailCoordinator],
    SensorEntity,
):
    """Shared base for sensors that describe a single tap.

    Centralises the two pieces of logic every tap sensor otherwise
    repeated: fetching this tap's data from the coordinator, and
    safely reading its (possibly missing) carbonation dict.
    """

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hane: str,
    ) -> None:
        super().__init__(coordinator)
        self.hane = hane

    def _tap(self) -> dict[str, Any]:
        """Return this sensor's tap data from the coordinator."""
        return self.coordinator.get_tap(self.hane)

    @staticmethod
    def _carbonation(tap: dict[str, Any]) -> dict[str, Any]:
        """Return a tap's carbonation dict, defaulting safely to {}."""
        carbonation = tap.get("carbonation") or {}
        return carbonation if isinstance(carbonation, dict) else {}


class TapCocktailHaneSensor(TapCocktailTapSensorBase):
    """Expose the cocktail selected for one tap."""

    _attr_icon = "mdi:glass-cocktail"

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hass: HomeAssistant,
        hane: str,
        temperature_sensor: str | None,
    ) -> None:
        super().__init__(coordinator, hane)

        self._temperature_sensor = temperature_sensor
        self._attr_name = f"TapCocktail Hane {hane}"
        self._attr_unique_id = f"tapcocktail_hane_{hane}"

    @property
    def native_value(self) -> str:
        """Return the selected cocktail label."""
        tap = self._tap()
        cocktail_id = tap.get("cocktail")

        if not isinstance(cocktail_id, str) or not cocktail_id:
            return "Ingen"

        return self.coordinator.get_cocktail_option(cocktail_id) or "Ingen"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details for the selected cocktail."""
        tap = self._tap()
        cocktail_id = tap.get("cocktail")

        if not isinstance(cocktail_id, str) or not cocktail_id:
            return {}

        cocktail = self.coordinator.get_cocktail(cocktail_id)

        if not cocktail:
            return {}

        attributes = cocktail.copy()

        try:
            co2 = float(attributes.get("co2", 2.5))
        except (TypeError, ValueError):
            co2 = 2.5

        if co2 <= 0:
            co2 = 2.5

        attributes["bubble_speed"] = round(6 / co2, 1)
        attributes["bubble_amount"] = round(co2 * 20)
        attributes["hane"] = self.hane

        if self._temperature_sensor:
            attributes["temperatursensor"] = self._temperature_sensor

        # Expose flat shelf-life attributes for dashboards, automations and
        # low-power displays that cannot parse the nested recipe object.
        attributes["holdbarhed_dage"] = None
        attributes["holdbarhed_resterende_dage"] = None
        attributes["holdbarhed_status"] = None

        shelf_life = attributes.get("holdbarhed")
        if isinstance(shelf_life, dict):
            try:
                shelf_life_days = int(shelf_life.get("days"))
            except (TypeError, ValueError):
                shelf_life_days = 0

            if shelf_life_days > 0:
                attributes["holdbarhed_dage"] = shelf_life_days
                ready_since = tap.get("ready_since")

                if (
                    tap.get("status") == TAP_STATUS_READY
                    and isinstance(ready_since, datetime)
                ):
                    elapsed_days = max(
                        0.0,
                        (dt_util.utcnow() - ready_since).total_seconds() / 86400,
                    )
                    remaining_days = ceil(shelf_life_days - elapsed_days)
                    used_ratio = elapsed_days / shelf_life_days

                    attributes["holdbarhed_resterende_dage"] = remaining_days
                    attributes["holdbarhed_status"] = (
                        "expired"
                        if remaining_days < 0
                        else "warning"
                        if used_ratio >= 0.8
                        else "fresh"
                    )

        return attributes


class TapCocktailStatusSensor(TapCocktailTapSensorBase):
    """Expose the current status for one tap."""

    _attr_icon = "mdi:gauge"

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hane: str,
    ) -> None:
        super().__init__(coordinator, hane)

        self._attr_name = f"Hane {hane} Status"
        self._attr_unique_id = f"tapcocktail_hane_{hane}_status"

    @property
    def native_value(self) -> str:
        """Return the current tap status."""
        tap = self._tap()
        status = tap.get("status", TAP_STATUS_IDLE)

        return str(status)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return supporting tap information."""
        tap = self._tap()

        return {
            "cocktail": tap.get("cocktail"),
            "ready_since": tap.get("ready_since"),
            "carbonation": tap.get("carbonation"),
        }


class TapCocktailProgressSensor(TapCocktailTapSensorBase):
    """Expose carbonation progress as a percentage."""

    _attr_icon = "mdi:chart-donut"
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hane: str,
    ) -> None:
        super().__init__(coordinator, hane)

        self._attr_name = f"Hane {hane} Progress"
        self._attr_unique_id = f"tapcocktail_hane_{hane}_progress"

    @property
    def native_value(self) -> float:
        """Return carbonation progress from 0 to 100 percent."""
        tap = self._tap()
        carbonation = self._carbonation(tap)

        started = carbonation.get("started")
        finished = carbonation.get("finished")

        if not isinstance(started, datetime) or not isinstance(
            finished,
            datetime,
        ):
            return 0.0

        total = (finished - started).total_seconds()

        if total <= 0:
            return 0.0

        elapsed = (min(finished, dt_util.utcnow()) - started).total_seconds()
        progress = max(0.0, min((elapsed / total) * 100, 100.0))

        return round(progress, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return timestamps used for the calculation."""
        tap = self._tap()
        carbonation = self._carbonation(tap)

        return {
            "started": carbonation.get("started"),
            "finished": carbonation.get("finished"),
            "status": tap.get("status"),
        }


class TapCocktailRemainingSensor(TapCocktailTapSensorBase):
    """Expose remaining carbonation time as formatted text."""

    _attr_icon = "mdi:timer-sand"

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hane: str,
    ) -> None:
        super().__init__(coordinator, hane)

        self._attr_name = f"Hane {hane} Remaining"
        self._attr_unique_id = f"tapcocktail_hane_{hane}_remaining"

    @property
    def native_value(self) -> str:
        """Return the remaining carbonation time."""
        tap = self._tap()
        status = tap.get("status", TAP_STATUS_IDLE)

        if status == TAP_STATUS_IDLE:
            return "Ikke startet"

        if status == TAP_STATUS_READY:
            return "Klar"

        if status != TAP_STATUS_CARBONATING:
            return "Ukendt"

        carbonation = self._carbonation(tap)
        finished = carbonation.get("finished")

        if not isinstance(finished, datetime):
            return "Ukendt"

        seconds = int((finished - dt_util.utcnow()).total_seconds())

        if seconds <= 0:
            return "Klar"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        if hours > 0:
            return f"{hours}t {minutes}m"

        return f"{minutes}m"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the finish timestamp and current status."""
        tap = self._tap()
        carbonation = self._carbonation(tap)

        return {
            "finished": carbonation.get("finished"),
            "status": tap.get("status"),
        }


class TapCocktailFinishedSensor(TapCocktailTapSensorBase):
    """Expose the timestamp at which carbonation finishes."""

    _attr_icon = "mdi:timer-sand"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hane: str,
    ) -> None:
        super().__init__(coordinator, hane)

        self._attr_name = f"Hane {hane} Færdig"
        self._attr_unique_id = f"tapcocktail_hane_{hane}_finished"

    @property
    def native_value(self) -> datetime | None:
        """Return the carbonation finish timestamp."""
        tap = self._tap()

        if tap.get("status") != TAP_STATUS_CARBONATING:
            return None

        carbonation = self._carbonation(tap)
        finished = carbonation.get("finished")

        return finished if isinstance(finished, datetime) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the current status."""
        tap = self._tap()

        return {
            "status": tap.get("status"),
        }


class TapCocktailReadySinceSensor(TapCocktailTapSensorBase):
    """Expose the timestamp at which the tap became ready."""

    _attr_icon = "mdi:beer"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hane: str,
    ) -> None:
        super().__init__(coordinator, hane)

        self._attr_name = f"Hane {hane} Tid på fad"
        self._attr_unique_id = f"tapcocktail_hane_{hane}_time_on_tap"

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp at which the tap became ready."""
        tap = self._tap()

        if tap.get("status") != TAP_STATUS_READY:
            return None

        ready_since = tap.get("ready_since")

        return ready_since if isinstance(ready_since, datetime) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the current status."""
        tap = self._tap()

        return {
            "status": tap.get("status"),
        }