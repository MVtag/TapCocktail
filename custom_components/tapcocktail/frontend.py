"""Serve and register the dashboard cards bundled with TapCocktail."""

import logging
from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_ID, CONF_TYPE, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = f"/{DOMAIN}"
CARD_URL = f"{URL_BASE}/tapcocktail-card.js"
MODULE_TYPE = "module"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Expose the two JS files and register their single module entry point."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                URL_BASE,
                str(Path(__file__).parent / "www"),
                cache_headers=False,
            )
        ]
    )

    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.warning(
            "Lovelace is unavailable; add %s as a JavaScript module manually",
            CARD_URL,
        )
        return

    if lovelace.resource_mode != "storage":
        _LOGGER.info(
            "Lovelace resources are managed in YAML; add %s as a module "
            "in configuration.yaml",
            CARD_URL,
        )
        return

    resources = lovelace.resources

    # Lovelace resources are lazy-loaded. Always load the stored resources
    # before looking up or creating an entry to avoid overwriting other cards.
    await resources.async_get_info()

    integration = await async_get_integration(hass, DOMAIN)
    version = integration.version
    resource_url = f"{CARD_URL}?v={version}"

    existing = [
        item
        for item in resources.async_items()
        if urlsplit(item.get(CONF_URL, "")).path == CARD_URL
    ]

    if existing:
        item = existing[0]
        if item.get(CONF_URL) != resource_url or item.get(CONF_TYPE) != MODULE_TYPE:
            await resources.async_update_item(
                item[CONF_ID],
                {"url": resource_url, "res_type": MODULE_TYPE},
            )
        if len(existing) > 1:
            _LOGGER.warning(
                "Multiple TapCocktail dashboard resources exist; remove "
                "the duplicate entries in Settings > Dashboards > Resources"
            )
    else:
        await resources.async_create_item(
            {"url": resource_url, "res_type": MODULE_TYPE}
        )
