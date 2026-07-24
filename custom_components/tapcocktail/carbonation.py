from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from .const import (
    TAP_STATUS_CARBONATING,
    TAP_STATUS_IDLE,
    TAP_STATUS_READY,
)

if TYPE_CHECKING:
    from .coordinator import TapCocktailCoordinator


class CarbonationEngine:
    """Ejer al logik om karbonering af en hane.

    Coordinatoren ejer selve dataen (taps), men al logik om hvordan
    en hane bevæger sig gennem idle -> carbonating -> ready ligger her.
    """

    def __init__(self, coordinator: "TapCocktailCoordinator") -> None:
        self.coordinator = coordinator

    def start(self, tap: str, duration: timedelta) -> None:
        """Start karbonering af en hane."""
        now = dt_util.utcnow()
        self.coordinator.update_tap(
            tap,
            status=TAP_STATUS_CARBONATING,
            carbonation={
                "duration": duration.total_seconds(),
                "started": now,
                "finished": now + duration,
            },
            ready_since=None,
        )

    def stop(self, tap: str) -> None:
        """Stop/nulstil karbonering af en hane."""
        self.coordinator.update_tap(
            tap,
            status=TAP_STATUS_IDLE,
            carbonation={
                "duration": None,
                "started": None,
                "finished": None,
            },
            ready_since=None,
        )

    def tick(self) -> bool:
        """Tjek alle haner for om karboneringen er færdig.

        Kaldes ved hver coordinator-opdatering (hvert 10. sekund).
        Returnerer True hvis mindst én hane skiftede status, så
        coordinatoren ved om der er noget nyt at gemme.
        """
        changed = False
        now = dt_util.utcnow()
        for tap_id, tap in self.coordinator.get_all_taps().items():
            if tap.get("status") != TAP_STATUS_CARBONATING:
                continue

            finished = tap.get("carbonation", {}).get("finished")
            if finished and now >= finished:
                self.coordinator.update_tap(
                    tap_id,
                    status=TAP_STATUS_READY,
                    ready_since=now,
                )
                changed = True
        return changed