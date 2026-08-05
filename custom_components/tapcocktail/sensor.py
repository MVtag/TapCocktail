"""Sensor platform for the TapCocktail integration."""

from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPressure
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR,
    CONF_TEMPERATURE_SENSOR_PREFIX,
    DOMAIN,
    TAP_STATUS_CARBONATING,
    TAP_STATUS_IDLE,
    TAP_STATUS_READY,
)
from .coordinator import TapCocktailCoordinator
from .pressure import CarbonationPressure, calculate_carbonation_pressure


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
        tap_temperature_sensor = entry.options.get(
            f"{CONF_TEMPERATURE_SENSOR_PREFIX}_{tap}"
        )
        entities.extend(
            [
                TapCocktailHaneSensor(
                    coordinator,
                    hass,
                    entry,
                    tap,
                    tap_temperature_sensor,
                ),
                TapCocktailPressureSensor(
                    coordinator,
                    hass,
                    entry,
                    tap,
                    tap_temperature_sensor,
                    pressure_mode="carbonation",
                ),
                TapCocktailPressureSensor(
                    coordinator,
                    hass,
                    entry,
                    tap,
                    tap_temperature_sensor,
                    pressure_mode="cooling",
                ),
                TapCocktailPressureSensor(
                    coordinator,
                    hass,
                    entry,
                    tap,
                    tap_temperature_sensor,
                    pressure_mode="serving",
                ),
                TapCocktailStatusSensor(coordinator, tap),
                TapCocktailProgressSensor(coordinator, tap),
                TapCocktailRemainingSensor(coordinator, tap),
                TapCocktailFinishedSensor(coordinator, tap),
                TapCocktailReadySinceSensor(coordinator, tap),
            ]
        )

    async_add_entities(entities)


def _read_temperature_c(
    hass: HomeAssistant,
    entity_id: str | None,
) -> float | None:
    """Read one Home Assistant temperature sensor and convert it to °C."""
    if not entity_id:
        return None

    temperature_state = hass.states.get(entity_id)
    if (
        temperature_state is None
        or temperature_state.state in ("unknown", "unavailable")
    ):
        return None

    try:
        temperature = float(temperature_state.state)
    except (TypeError, ValueError):
        return None

    unit = temperature_state.attributes.get("unit_of_measurement", "°C")
    if unit == "°F":
        temperature = (temperature - 32) * 5 / 9
    elif unit == "K":
        temperature -= 273.15

    return round(temperature, 1)


def _positive_float(value: Any, fallback: float) -> float:
    """Return a positive float or a safe fallback."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    return result if result > 0 else fallback


def _cocktail_for_tap(
    coordinator: TapCocktailCoordinator,
    tap: str,
) -> dict[str, Any] | None:
    """Return the selected cocktail for one tap."""
    cocktail_id = coordinator.get_tap(tap).get("cocktail")
    if not isinstance(cocktail_id, str) or not cocktail_id:
        return None
    return coordinator.get_cocktail(cocktail_id)


def _pressure_for_mode(
    coordinator: TapCocktailCoordinator,
    hass: HomeAssistant,
    entry: ConfigEntry,
    tap: str,
    tap_temperature_sensor: str | None,
    pressure_mode: str,
) -> tuple[CarbonationPressure, str, str | None] | None:
    """Calculate the requested pressure and return its temperature source."""
    cocktail = _cocktail_for_tap(coordinator, tap)
    if not cocktail:
        return None

    volumes_co2 = _positive_float(cocktail.get("co2"), 2.5)
    target_temperature = _positive_float(cocktail.get("temperatur"), 4.0)

    if pressure_mode == "carbonation":
        source_entity = entry.options.get(
            CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR
        )
        source_entity = (
            str(source_entity) if source_entity else None
        )
        temperature = _read_temperature_c(hass, source_entity)
        source_label = "karboneringsrum"
    elif pressure_mode == "serving":
        source_entity = tap_temperature_sensor
        temperature = _read_temperature_c(hass, source_entity)
        if temperature is None:
            temperature = target_temperature
            source_entity = None
            source_label = "opskriftens måltemperatur"
        else:
            source_label = "hanens temperatursensor"
    else:
        source_entity = None
        temperature = target_temperature
        source_label = "opskriftens måltemperatur"

    if temperature is None:
        return None

    return (
        calculate_carbonation_pressure(volumes_co2, temperature),
        source_label,
        source_entity,
    )


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
        entry: ConfigEntry,
        hane: str,
        temperature_sensor: str | None,
    ) -> None:
        super().__init__(coordinator, hane)

        self._hass = hass
        self._entry = entry
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

        co2 = _positive_float(attributes.get("co2"), 2.5)
        attributes["bubble_speed"] = round(6 / co2, 1)
        attributes["bubble_amount"] = round(co2 * 20)
        attributes["hane"] = self.hane

        if self._temperature_sensor:
            attributes["temperatursensor"] = self._temperature_sensor
            current_temperature = _read_temperature_c(
                self._hass,
                self._temperature_sensor,
            )
            if current_temperature is not None:
                attributes["aktuel_temperatur"] = current_temperature
                attributes["aktuel_temperatur_enhed"] = "°C"

        room_sensor = self._entry.options.get(
            CONF_CARBONATION_ROOM_TEMPERATURE_SENSOR
        )
        if room_sensor:
            attributes["karboneringsrum_temperatursensor"] = str(
                room_sensor
            )

        pressure_attribute_names = {
            "carbonation": "karboneringstryk",
            "cooling": "nedkoelingstryk",
            "serving": "serveringstryk",
        }
        for pressure_mode, attribute_prefix in pressure_attribute_names.items():
            pressure_result = _pressure_for_mode(
                self.coordinator,
                self._hass,
                self._entry,
                self.hane,
                self._temperature_sensor,
                pressure_mode,
            )
            if pressure_result is None:
                attributes[f"{attribute_prefix}_bar"] = None
                attributes[f"{attribute_prefix}_psi"] = None
                attributes[f"{attribute_prefix}_temperatur"] = None
                continue

            pressure, source_label, source_entity = pressure_result
            attributes[f"{attribute_prefix}_bar"] = pressure.bar
            attributes[f"{attribute_prefix}_psi"] = pressure.psi
            attributes[f"{attribute_prefix}_temperatur"] = (
                pressure.temperature_c
            )
            attributes[f"{attribute_prefix}_temperatur_kilde"] = (
                source_label
            )
            if source_entity:
                attributes[f"{attribute_prefix}_temperatursensor"] = (
                    source_entity
                )

        attributes["trykplan_status"] = (
            "klar"
            if attributes.get("karboneringstryk_bar") is not None
            else "mangler_karboneringsrum_temperatur"
        )

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


class TapCocktailPressureSensor(TapCocktailTapSensorBase):
    """Expose one calculated regulator pressure for a tap."""

    _attr_device_class = SensorDeviceClass.PRESSURE
    _attr_native_unit_of_measurement = UnitOfPressure.BAR
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: TapCocktailCoordinator,
        hass: HomeAssistant,
        entry: ConfigEntry,
        hane: str,
        temperature_sensor: str | None,
        pressure_mode: str,
    ) -> None:
        super().__init__(coordinator, hane)
        self._hass = hass
        self._entry = entry
        self._temperature_sensor = temperature_sensor
        self._pressure_mode = pressure_mode

        labels = {
            "carbonation": (
                "Karboneringstryk",
                "carbonation_pressure",
                "mdi:gauge",
            ),
            "cooling": (
                "Køletryk",
                "cooling_pressure",
                "mdi:snowflake-thermometer",
            ),
            "serving": (
                "Serveringstryk",
                "serving_pressure",
                "mdi:glass-cocktail",
            ),
        }
        name, unique_suffix, icon = labels[pressure_mode]
        self._attr_name = f"Hane {hane} {name}"
        self._attr_unique_id = f"tapcocktail_hane_{hane}_{unique_suffix}"
        self._attr_icon = icon

    def _pressure_result(
        self,
    ) -> tuple[CarbonationPressure, str, str | None] | None:
        return _pressure_for_mode(
            self.coordinator,
            self._hass,
            self._entry,
            self.hane,
            self._temperature_sensor,
            self._pressure_mode,
        )

    @property
    def native_value(self) -> float | None:
        """Return the recommended regulator pressure in bar."""
        result = self._pressure_result()
        return result[0].bar if result else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return PSI, CO₂ target and the temperature used."""
        result = self._pressure_result()
        cocktail = _cocktail_for_tap(self.coordinator, self.hane)
        attributes: dict[str, Any] = {
            "type": self._pressure_mode,
            "cocktail": self._tap().get("cocktail"),
            "vol_co2": (
                _positive_float(cocktail.get("co2"), 2.5)
                if cocktail
                else None
            ),
        }

        if result is None:
            attributes["status"] = (
                "mangler_karboneringsrum_temperatur"
                if self._pressure_mode == "carbonation"
                else "mangler_cocktail"
            )
            return attributes

        pressure, source_label, source_entity = result
        attributes.update(
            {
                "psi": pressure.psi,
                "temperatur": pressure.temperature_c,
                "temperatur_enhed": "°C",
                "temperatur_kilde": source_label,
                "temperatursensor": source_entity,
                "status": "klar",
            }
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
