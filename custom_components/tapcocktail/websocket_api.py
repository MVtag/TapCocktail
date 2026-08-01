"""WebSocket API used by the TapCocktail Library Card."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN

ERR_NOT_CONFIGURED = "not_configured"
ERR_NOT_FOUND = "not_found"
ERR_VALIDATION = "validation_error"
ERR_CONFIRMATION = "confirmation_required"


def _coordinator(hass: HomeAssistant, entry_id: str | None = None):
    """Return the requested coordinator, or the only configured instance."""
    coordinators = hass.data.get(DOMAIN, {})

    if entry_id:
        coordinator = coordinators.get(entry_id)
    elif len(coordinators) == 1:
        coordinator = next(iter(coordinators.values()))
    else:
        coordinator = None

    if coordinator is None:
        raise LookupError(
            "TapCocktail is not configured, or entry_id is required."
        )

    return coordinator


async def _ingredients(coordinator) -> dict[str, dict[str, Any]]:
    """Read ingredients across the v2 coordinator API."""
    getter = getattr(coordinator, "async_get_ingredients", None)
    if getter is not None:
        ingredients = await getter()
    else:
        ingredients = await coordinator.async_list_ingredients()

    if isinstance(ingredients, list):
        return {
            str(item["id"]): item
            for item in ingredients
            if isinstance(item, dict) and item.get("id")
        }

    return ingredients


def _send_error(connection, msg_id: int, code: str, error: Exception | str) -> None:
    """Return a safe, useful error to the dashboard card."""
    connection.send_error(msg_id, code, str(error))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tapcocktail/library/get",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_get_library(hass, connection, msg) -> None:
    """Return cocktail and ingredient libraries in one response."""
    connection.require_admin()

    try:
        coordinator = _coordinator(hass, msg.get("entry_id"))
        ingredients = await _ingredients(coordinator)
    except LookupError as err:
        _send_error(connection, msg["id"], ERR_NOT_CONFIGURED, err)
        return
    except ValueError as err:
        _send_error(connection, msg["id"], ERR_VALIDATION, err)
        return

    connection.send_result(
        msg["id"],
        {
            "cocktails": coordinator.get_all_cocktails(),
            "ingredients": ingredients,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tapcocktail/cocktail/save",
        vol.Required("data"): dict,
        vol.Optional("original_id"): str,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_save_cocktail(hass, connection, msg) -> None:
    """Create or update a cocktail through the existing manager."""
    connection.require_admin()

    try:
        coordinator = _coordinator(hass, msg.get("entry_id"))
        saved = await coordinator.async_save_cocktail(
            msg["data"],
            original_id=msg.get("original_id"),
        )
    except LookupError as err:
        _send_error(connection, msg["id"], ERR_NOT_CONFIGURED, err)
        return
    except (TypeError, ValueError) as err:
        _send_error(connection, msg["id"], ERR_VALIDATION, err)
        return

    connection.send_result(msg["id"], saved)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tapcocktail/cocktail/delete",
        vol.Required("cocktail_id"): str,
        vol.Required("confirm"): bool,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_delete_cocktail(hass, connection, msg) -> None:
    """Delete a cocktail after an explicit confirmation."""
    connection.require_admin()

    if not msg["confirm"]:
        _send_error(
            connection,
            msg["id"],
            ERR_CONFIRMATION,
            "Deletion must be confirmed.",
        )
        return

    try:
        coordinator = _coordinator(hass, msg.get("entry_id"))
        deleted = await coordinator.async_delete_cocktail(msg["cocktail_id"])
    except LookupError as err:
        _send_error(connection, msg["id"], ERR_NOT_CONFIGURED, err)
        return
    except ValueError as err:
        _send_error(connection, msg["id"], ERR_VALIDATION, err)
        return

    if not deleted:
        _send_error(
            connection,
            msg["id"],
            ERR_NOT_FOUND,
            "Cocktail not found.",
        )
        return

    connection.send_result(msg["id"], {"deleted": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tapcocktail/ingredient/save",
        vol.Required("data"): dict,
        vol.Optional("original_id"): str,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_save_ingredient(hass, connection, msg) -> None:
    """Create or update an ingredient through the existing manager."""
    connection.require_admin()

    try:
        coordinator = _coordinator(hass, msg.get("entry_id"))
        saved = await coordinator.async_save_ingredient(
            msg["data"],
            original_id=msg.get("original_id"),
        )
    except LookupError as err:
        _send_error(connection, msg["id"], ERR_NOT_CONFIGURED, err)
        return
    except (TypeError, ValueError) as err:
        _send_error(connection, msg["id"], ERR_VALIDATION, err)
        return

    connection.send_result(msg["id"], saved)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "tapcocktail/ingredient/delete",
        vol.Required("ingredient_id"): str,
        vol.Required("confirm"): bool,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_delete_ingredient(hass, connection, msg) -> None:
    """Delete an ingredient after an explicit confirmation."""
    connection.require_admin()

    if not msg["confirm"]:
        _send_error(
            connection,
            msg["id"],
            ERR_CONFIRMATION,
            "Deletion must be confirmed.",
        )
        return

    try:
        coordinator = _coordinator(hass, msg.get("entry_id"))
        deleted = await coordinator.async_delete_ingredient(msg["ingredient_id"])
    except LookupError as err:
        _send_error(connection, msg["id"], ERR_NOT_CONFIGURED, err)
        return
    except ValueError as err:
        _send_error(connection, msg["id"], ERR_VALIDATION, err)
        return

    if not deleted:
        _send_error(
            connection,
            msg["id"],
            ERR_NOT_FOUND,
            "Ingredient not found.",
        )
        return

    connection.send_result(msg["id"], {"deleted": True})


def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register Library Card commands once per Home Assistant runtime."""
    registration_key = f"{DOMAIN}_websocket_registered"
    if hass.data.get(registration_key):
        return

    for command in (
        websocket_get_library,
        websocket_save_cocktail,
        websocket_delete_cocktail,
        websocket_save_ingredient,
        websocket_delete_ingredient,
    ):
        websocket_api.async_register_command(hass, command)

    hass.data[registration_key] = True
