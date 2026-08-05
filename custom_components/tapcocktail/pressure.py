"""CO₂ equilibrium-pressure calculations for TapCocktail."""

from __future__ import annotations

from dataclasses import dataclass

PSI_PER_BAR = 14.5037738


@dataclass(frozen=True, slots=True)
class CarbonationPressure:
    """Calculated regulator pressure at one temperature."""

    bar: float
    psi: float
    temperature_c: float
    volumes_co2: float


def calculate_carbonation_pressure(
    volumes_co2: float,
    temperature_c: float,
) -> CarbonationPressure:
    """Return equilibrium gauge pressure for CO₂ volumes and temperature.

    The polynomial is the commonly used keg-carbonation relation with
    temperature expressed in degrees Fahrenheit and pressure returned as
    gauge PSI. Negative regulator pressures are clamped to zero because a
    standard CO₂ regulator cannot provide vacuum.
    """
    volumes = max(0.0, float(volumes_co2))
    temperature = float(temperature_c)
    temperature_f = temperature * 9 / 5 + 32

    pressure_psi = (
        -16.6999
        - 0.0101059 * temperature_f
        + 0.00116512 * temperature_f**2
        + 0.173354 * temperature_f * volumes
        + 4.24267 * volumes
        - 0.0684226 * volumes**2
    )
    pressure_psi = max(0.0, pressure_psi)

    return CarbonationPressure(
        bar=round(pressure_psi / PSI_PER_BAR, 2),
        psi=round(pressure_psi, 1),
        temperature_c=round(temperature, 1),
        volumes_co2=round(volumes, 2),
    )
