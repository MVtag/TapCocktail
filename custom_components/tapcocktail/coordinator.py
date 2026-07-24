from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from .carbonation import CarbonationEngine
from .cocktail_manager import CocktailManager
from .const import (
    COCKTAIL_PATH,
    DOMAIN,
    TAP_STATUS_IDLE,
)

_LOGGER = logging.getLogger(__name__)


def _load_cocktails_sync(folder_path: str) -> dict:
    """Blocking file I/O - køres i en executor thread."""
    cocktails = {}
    folder = Path(folder_path)
    if not folder.exists():
        _LOGGER.warning(
            "Cocktail folder not found: %s",
            folder_path,
        )
        return cocktails
    for file in folder.rglob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                cocktail = json.load(f)
            cocktail_id = cocktail.get("id", file.stem)
            cocktail["kategori"] = file.parent.name
            cocktails[cocktail_id] = cocktail
            _LOGGER.debug(
                "Loaded cocktail: %s",
                cocktail_id,
            )
        except Exception as err:
            _LOGGER.error(
                "Could not load %s: %s",
                file,
                err,
            )
    return cocktails


def _new_tap_state() -> dict[str, object]:
    """Return a fresh, empty tap state."""
    return {
        "cocktail": None,
        "status": TAP_STATUS_IDLE,
        "carbonation": {
            "duration": None,
            "started": None,
            "finished": None,
        },
        "ready_since": None,
    }


def _option_to_cocktail_id(option: str | None) -> str | None:
    """Konverter en dropdown-tekst ('🍊 Filur') til et cocktail-id ('filur')."""
    if not option or option == "Ingen":
        return None
    return (
        option
        .split(" ", 1)[-1]
        .strip()
        .lower()
        .replace(" ", "_")
    )


def _serialize_taps(taps: dict[str, dict]) -> dict:
    """Konverter datetime-felter til ISO-strenge, så de kan gemmes som JSON."""
    serialized = {}
    for tap_id, tap in taps.items():
        tap_copy = dict(tap)
        carbonation = dict(tap_copy.get("carbonation") or {})
        for key in ("started", "finished"):
            value = carbonation.get(key)
            if isinstance(value, datetime):
                carbonation[key] = value.isoformat()
        tap_copy["carbonation"] = carbonation

        ready_since = tap_copy.get("ready_since")
        if isinstance(ready_since, datetime):
            tap_copy["ready_since"] = ready_since.isoformat()

        serialized[tap_id] = tap_copy
    return serialized


def _deserialize_taps(data: dict) -> dict[str, dict]:
    """Konverter ISO-strenge tilbage til datetime, når data hentes fra storage."""
    taps: dict[str, dict] = {}
    for tap_id, tap in data.items():
        tap_copy = dict(tap)
        carbonation = dict(tap_copy.get("carbonation") or {})
        for key in ("started", "finished"):
            value = carbonation.get(key)
            if isinstance(value, str):
                carbonation[key] = dt_util.parse_datetime(value)
        tap_copy["carbonation"] = carbonation

        ready_since = tap_copy.get("ready_since")
        if isinstance(ready_since, str):
            tap_copy["ready_since"] = dt_util.parse_datetime(ready_since)

        taps[tap_id] = tap_copy
    return taps


class TapCocktailCoordinator(DataUpdateCoordinator):
    """Coordinator for TapCocktail."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: Store,
        stored_selections: dict,
        taps_store: Store,
        stored_taps: dict,
        max_taps: int,
    ):
        self.hass = hass
        self.store = store
        self.stored_selections = stored_selections
        self.taps_store = taps_store
        self.max_taps = max_taps
        self.cocktail_manager = CocktailManager(COCKTAIL_PATH)

        # Genskab gemte haner (status, karbonering, tider) - fald tilbage
        # til en tom hane for dem der ikke findes i det gemte data endnu
        restored = _deserialize_taps(stored_taps) if stored_taps else {}

        # Keep every stored tap, including currently inactive taps. This means
        # reducing the configured tap count does not delete their saved data.
        self.taps: dict[str, dict[str, object]] = dict(restored)

        # Ensure every currently active tap exists.
        for tap_number in range(1, self.max_taps + 1):
            self.taps.setdefault(str(tap_number), _new_tap_state())

        # Karboneringsmotoren ejer al logik om idle -> carbonating -> ready
        self.carbonation = CarbonationEngine(self)

        # True når tap-data er ændret og skal gemmes
        self._taps_dirty = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )

    async def _async_update_data(self):
        """Load cocktail JSON files."""
        cocktails = await self.hass.async_add_executor_job(
            _load_cocktails_sync,
            COCKTAIL_PATH,
        )
        self._sync_selected_cocktails()

        self.carbonation.tick()

        if self._taps_dirty:
            await self._save_taps()
            self._taps_dirty = False

        return cocktails

    def _sync_selected_cocktails(self) -> None:
        """Synchronise active taps with the integration-owned selects.

        Stored tap data is authoritative during startup. Legacy input_select
        helpers must never overwrite the selected cocktail after a restart.
        """
        for tap in self.active_tap_ids:
            entity_id = f"select.hane_{tap}_cocktail"
            state = self.hass.states.get(entity_id)

            # During startup the select platform may not be loaded yet.
            # Keep the restored tap state unchanged until the entity exists.
            if state is None or state.state in ("unknown", "unavailable"):
                continue

            cocktail_id = self.cocktail_option_to_id(state.state)
            current = self.get_tap(tap)

            if current.get("cocktail") == cocktail_id:
                continue

            new_state = _new_tap_state()
            new_state["cocktail"] = cocktail_id
            self.taps[tap] = new_state
            self._taps_dirty = True

    async def _save_taps(self) -> None:
        """Gem tap-data (status, karbonering, tider) til disk."""
        await self.taps_store.async_save(
            _serialize_taps(self.taps)
        )

    #
    # Cocktail helpers
    #
    def get_cocktail(self, cocktail_id: str) -> dict:
        """Return one cocktail."""
        if not self.data:
            return {}
        return self.data.get(cocktail_id, {})

    def get_all_cocktails(self) -> dict:
        """Return all cocktails."""
        return self.data or {}

    def get_cocktail_options(self) -> list[str]:
        """Return cocktail labels for the integration-owned select."""
        options = ["Ingen"]

        for cocktail in self.get_all_cocktails().values():
            name = cocktail.get("navn")
            icon = cocktail.get("ikon", "🍹")

            if name:
                options.append(f"{icon} {name}")

        return [options[0], *sorted(options[1:])]

    def get_cocktail_option(self, cocktail_id: str) -> str | None:
        """Return the displayed option for a cocktail ID."""
        cocktail = self.get_cocktail(cocktail_id)

        if not cocktail:
            return None

        name = cocktail.get("navn")
        icon = cocktail.get("ikon", "🍹")

        if not name:
            return None

        return f"{icon} {name}"

    def cocktail_option_to_id(self, option: str | None) -> str | None:
        """Resolve a displayed option to its cocktail ID."""
        if not option or option == "Ingen":
            return None

        for cocktail_id in self.get_all_cocktails():
            if self.get_cocktail_option(cocktail_id) == option:
                return cocktail_id

        return _option_to_cocktail_id(option)

    async def async_select_cocktail(
        self,
        tap: str,
        option: str,
    ) -> None:
        """Select a cocktail, reset the tap state, and save immediately."""
        cocktail_id = self.cocktail_option_to_id(option)
        current = self.get_tap(tap)

        if current.get("cocktail") == cocktail_id:
            return

        new_state = _new_tap_state()
        new_state["cocktail"] = cocktail_id
        self.taps[tap] = new_state
        self._taps_dirty = True

        selection_key = f"select.hane_{tap}_cocktail"
        self.stored_selections[selection_key] = option

        await self.store.async_save(self.stored_selections)
        await self._save_taps()
        self._taps_dirty = False
        self.async_set_updated_data(self.data or {})

    async def async_reload_cocktails(self) -> None:
        """Reload cocktail files and refresh coordinator entities."""
        await self.async_request_refresh()

    async def async_list_categories(self) -> list[str]:
        """Return cocktail categories without blocking Home Assistant."""
        return await self.hass.async_add_executor_job(
            self.cocktail_manager.list_categories
        )

    async def async_save_cocktail(
        self,
        data: dict,
        *,
        original_id: str | None = None,
    ) -> dict:
        """Create or update a cocktail and reload the library."""
        saved = await self.hass.async_add_executor_job(
            lambda: self.cocktail_manager.save_cocktail(
                data,
                original_id=original_id,
            )
        )
        await self.async_request_refresh()
        return saved

    async def async_delete_cocktail(
        self,
        cocktail_id: str,
    ) -> bool:
        """Delete a cocktail and reload the library."""
        deleted = await self.hass.async_add_executor_job(
            self.cocktail_manager.delete_cocktail,
            cocktail_id,
        )

        if deleted:
            await self.async_request_refresh()

        return deleted

    #
    # Tap helpers
    #
    def get_tap(self, tap: str) -> dict[str, object]:
        """Return tap data."""
        return self.taps.setdefault(tap, _new_tap_state())

    @property
    def active_tap_ids(self) -> tuple[str, ...]:
        """Return the IDs of taps enabled in the current configuration."""
        return tuple(str(i) for i in range(1, self.max_taps + 1))

    def get_all_taps(self) -> dict[str, dict]:
        """Return active taps only."""
        return {
            tap_id: self.get_tap(tap_id)
            for tap_id in self.active_tap_ids
        }

    def get_all_stored_taps(self) -> dict[str, dict]:
        """Return active and inactive stored taps."""
        return self.taps

    def update_tap(
        self,
        tap: str,
        **kwargs,
    ) -> None:
        """Update tap data."""
        current = self.taps.setdefault(
            tap,
            _new_tap_state(),
        )

        changed = False

        for key, value in kwargs.items():
            if current.get(key) != value:
                current[key] = value
                changed = True

        if changed:
            self._taps_dirty = True

    def clear_tap(
        self,
        tap: str,
    ) -> None:
        """Reset tap to its empty state and persist the change."""
        self.taps[tap] = _new_tap_state()
        self._taps_dirty = True

    #
    # Karboneringsmotor - offentligt API, delegerer til CarbonationEngine
    #
    async def start_carbonation(
        self,
        tap: str,
        duration: timedelta,
    ) -> None:
        """Start karbonering af en hane."""
        self.carbonation.start(tap, duration)

    async def stop_carbonation(
        self,
        tap: str,
    ) -> None:
        """Stop/nulstil karbonering af en hane."""
        self.carbonation.stop(tap)