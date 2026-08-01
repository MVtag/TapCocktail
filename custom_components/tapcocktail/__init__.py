from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    CONF_MAX_TAPS,
    DEFAULT_MAX_TAPS,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    TAPS_STORAGE_KEY,
)
from .coordinator import TapCocktailCoordinator
from .websocket_api import async_register_websocket_api


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up TapCocktail from a config entry."""
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored_selections = await store.async_load() or {}

    taps_store = Store(hass, STORAGE_VERSION, TAPS_STORAGE_KEY)
    stored_taps = await taps_store.async_load() or {}

    max_taps = int(
        entry.options.get(
            CONF_MAX_TAPS,
            entry.data.get(CONF_MAX_TAPS, DEFAULT_MAX_TAPS),
        )
    )

    coordinator = TapCocktailCoordinator(
        hass,
        store,
        stored_selections,
        taps_store,
        stored_taps,
        max_taps,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    async_register_websocket_api(hass)

    await hass.config_entries.async_forward_entry_setups(
        entry,
        [
            "sensor",
            "button",
            "select",
        ],
    )

    return True
