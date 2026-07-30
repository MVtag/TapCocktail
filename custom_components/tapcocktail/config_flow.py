from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    selector,
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .cocktail_manager import CocktailValidationError
from .themes import COCKTAIL_THEMES

INGREDIENT_EXAMPLE = """Gin | 4 cl | 40 cl | 180 cl
Mangopuré | 3 cl | 30 cl | 135 cl
Limesaft | 2 cl | 20 cl | 90 cl"""
from .const import (
    CONF_MAX_TAPS,
    DEFAULT_MAX_TAPS,
    DOMAIN,
    MAX_SUPPORTED_TAPS,
    MIN_TAPS,
)


def _tap_schema(default: int) -> vol.Schema:
    """Return a dropdown for selecting the number of active taps."""
    choices = {
        tap_count: (
            f"{tap_count} hane"
            if tap_count == 1
            else f"{tap_count} haner"
        )
        for tap_count in range(
            MIN_TAPS,
            MAX_SUPPORTED_TAPS + 1,
        )
    }

    return vol.Schema(
        {
            vol.Required(
                CONF_MAX_TAPS,
                default=default,
            ): vol.In(choices),
        }
    )


def _hex_to_rgb(value: str | None) -> list[int]:
    """Convert #RRGGBB to the value used by Home Assistant's RGB selector."""
    color = str(value or "#FF8C00").lstrip("#")
    if len(color) != 6:
        return [255, 140, 0]
    try:
        return [
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
        ]
    except ValueError:
        return [255, 140, 0]


def _ingredients_to_form(cocktail: dict[str, Any]) -> dict[str, str]:
    """Convert saved ingredient objects into six structured form rows."""
    result: dict[str, str] = {}
    ingredients = cocktail.get("ingredienser", [])

    for index in range(1, 13):
        item = ingredients[index - 1] if index <= len(ingredients) else {}
        result[f"ingrediens_{index}_navn"] = str(item.get("navn", ""))
        result[f"ingrediens_{index}_alkoholprocent"] = item.get(
            "alkoholprocent", 0
        )
        result[f"ingrediens_{index}_glas"] = str(item.get("glas", ""))
        result[f"ingrediens_{index}_2l"] = str(item.get("2_liter", ""))
        result[f"ingrediens_{index}_9l"] = str(item.get("9_liter", ""))

    return result


class TapCocktailConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle the TapCocktail config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle initial setup."""
        if user_input is not None:
            return self.async_create_entry(
                title="TapCocktail",
                data={
                    CONF_MAX_TAPS: int(
                        user_input[CONF_MAX_TAPS]
                    ),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_tap_schema(DEFAULT_MAX_TAPS),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return TapCocktailOptionsFlow()


class TapCocktailOptionsFlow(config_entries.OptionsFlow):
    """Manage TapCocktail settings and cocktail recipes."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._selected_cocktail_id: str | None = None
        self._pending_cocktail_data: dict[str, Any] = {}
        self._ingredient_count: int = 3
        self._selected_theme: str = "klassisk"
        self._editing: bool = False

    @property
    def _coordinator(self):
        """Return the active TapCocktail coordinator."""
        return self.hass.data[DOMAIN][self.config_entry.entry_id]

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Show the TapCocktail management menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "settings": "Indstillinger",
                "create_cocktail": "Opret cocktail",
                "edit_cocktail": "Rediger cocktail",
                "delete_cocktail": "Slet cocktail",
            },
        )

    async def async_step_settings(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Change the number of active taps."""
        current = int(
            self.config_entry.options.get(
                CONF_MAX_TAPS,
                self.config_entry.data.get(
                    CONF_MAX_TAPS,
                    DEFAULT_MAX_TAPS,
                ),
            )
        )

        if user_input is not None:
            new_options = {
                **self.config_entry.options,
                CONF_MAX_TAPS: int(
                    user_input[CONF_MAX_TAPS]
                ),
            }

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=new_options,
            )
            await self.hass.config_entries.async_reload(
                self.config_entry.entry_id
            )

            return self.async_abort(reason="settings_saved")

        return self.async_show_form(
            step_id="settings",
            data_schema=_tap_schema(current),
        )

    async def async_step_create_cocktail(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Choose ingredient count before creating a cocktail."""
        self._editing = False

        if user_input is not None:
            self._ingredient_count = int(user_input["ingredient_count"])
            self._selected_theme = str(user_input["tema"])
            self._pending_cocktail_data = {}
            return await self.async_step_create_cocktail_form()

        return self.async_show_form(
            step_id="create_cocktail",
            data_schema=self._ingredient_count_schema(
                3,
                theme_default="klassisk",
                include_theme=True,
            ),
        )

    async def async_step_create_cocktail_form(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Create a new cocktail."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                data = self._prepare_cocktail_data(user_input)
                saved = await self._coordinator.async_save_cocktail(data)

                return self.async_abort(
                    reason="cocktail_created",
                    description_placeholders={
                        "name": str(saved["navn"]),
                    },
                )
            except CocktailValidationError as err:
                errors["base"] = "cocktail_validation"
                return self.async_show_form(
                    step_id="create_cocktail_form",
                    data_schema=await self._cocktail_schema(
                        user_input,
                        ingredient_count=self._ingredient_count,
                    ),
                    errors=errors,
                    description_placeholders={
                        "error": str(err),
                    },
                )

        theme = COCKTAIL_THEMES.get(
            self._selected_theme,
            COCKTAIL_THEMES["klassisk"],
        )

        return self.async_show_form(
            step_id="create_cocktail_form",
            data_schema=await self._cocktail_schema(
                {
                    "tema": self._selected_theme,
                    "farve": theme["color"],
                },
                ingredient_count=self._ingredient_count,
            ),
            errors=errors,
        )

    async def async_step_edit_cocktail(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Choose a cocktail to edit."""
        cocktails = self._coordinator.get_all_cocktails()

        if not cocktails:
            return self.async_abort(reason="no_cocktails")

        if user_input is not None:
            self._selected_cocktail_id = str(
                user_input["cocktail_id"]
            )
            self._editing = True
            return await self.async_step_edit_ingredient_count()

        options = [
            {
                "value": cocktail_id,
                "label": self._cocktail_label(
                    cocktail_id,
                    cocktail,
                ),
            }
            for cocktail_id, cocktail in sorted(
                cocktails.items(),
                key=lambda item: str(
                    item[1].get("navn", item[0])
                ).lower(),
            )
        ]

        return self.async_show_form(
            step_id="edit_cocktail",
            data_schema=vol.Schema(
                {
                    vol.Required("cocktail_id"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            sort=False,
                        )
                    )
                }
            ),
        )

    async def async_step_edit_ingredient_count(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Choose how many ingredient rows to show while editing."""
        cocktail_id = self._selected_cocktail_id

        if not cocktail_id:
            return await self.async_step_edit_cocktail()

        cocktail = self._coordinator.get_cocktail(cocktail_id)
        if not cocktail:
            return self.async_abort(reason="cocktail_not_found")

        current_count = max(
            1,
            min(12, len(cocktail.get("ingredienser", [])) or 1),
        )

        if user_input is not None:
            self._ingredient_count = int(user_input["ingredient_count"])
            self._selected_theme = str(user_input["tema"])
            return await self.async_step_edit_cocktail_form()

        return self.async_show_form(
            step_id="edit_ingredient_count",
            data_schema=self._ingredient_count_schema(
                current_count,
                theme_default=str(cocktail.get("tema", "klassisk")),
                include_theme=True,
            ),
        )

    async def async_step_edit_cocktail_form(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Edit the selected cocktail."""
        cocktail_id = self._selected_cocktail_id

        if not cocktail_id:
            return await self.async_step_edit_cocktail()

        cocktail = self._coordinator.get_cocktail(cocktail_id)

        if not cocktail:
            return self.async_abort(reason="cocktail_not_found")

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                data = self._prepare_cocktail_data(user_input)
                saved = await self._coordinator.async_save_cocktail(
                    data,
                    original_id=cocktail_id,
                )

                return self.async_abort(
                    reason="cocktail_updated",
                    description_placeholders={
                        "name": str(saved["navn"]),
                    },
                )
            except CocktailValidationError as err:
                errors["base"] = "cocktail_validation"
                return self.async_show_form(
                    step_id="edit_cocktail_form",
                    data_schema=await self._cocktail_schema(
                        user_input,
                        include_id=True,
                        ingredient_count=self._ingredient_count,
                    ),
                    errors=errors,
                    description_placeholders={
                        "error": str(err),
                    },
                )

        defaults = {
            "id": cocktail_id,
            "navn": cocktail.get("navn", ""),
            "kategori": cocktail.get("kategori", "cocktails"),
            "ny_kategori": "",
            "tema": self._selected_theme or cocktail.get("tema", "klassisk"),
            "ikon_override": "",
            "brug_tema_farve": (
                str(cocktail.get("farve", "")).upper()
                == str(
                    COCKTAIL_THEMES.get(
                        self._selected_theme
                        or cocktail.get("tema", "klassisk"),
                        COCKTAIL_THEMES["klassisk"],
                    )["color"]
                ).upper()
            ),
            "brugerdefineret_farve_rgb": _hex_to_rgb(
                (
                    COCKTAIL_THEMES.get(
                        self._selected_theme,
                        COCKTAIL_THEMES["klassisk"],
                    )["color"]
                    if (
                        self._selected_theme
                        and self._selected_theme
                        != cocktail.get("tema", "klassisk")
                        and str(cocktail.get("farve", "")).upper()
                        == str(
                            COCKTAIL_THEMES.get(
                                cocktail.get("tema", "klassisk"),
                                COCKTAIL_THEMES["klassisk"],
                            )["color"]
                        ).upper()
                    )
                    else cocktail.get("farve")
                )
                or COCKTAIL_THEMES.get(
                    self._selected_theme,
                    COCKTAIL_THEMES["klassisk"],
                )["color"]
            ),
            "automatisk_beregning": cocktail.get(
                "beregning", {}
            ).get("enabled", True),
            "beregn_fra": cocktail.get(
                "beregning", {}
            ).get("source", "glass"),
            "automatisk_abv": cocktail.get(
                "abv_beregning", {}
            ).get(
                "enabled",
                any(
                    "alkoholprocent" in ingredient
                    for ingredient in cocktail.get("ingredienser", [])
                ),
            ),
            "abv": cocktail.get("abv", 0),
            "co2": cocktail.get("co2", 2.5),
            "temperatur": cocktail.get("temperatur", 4),
            "glas": cocktail.get("glas", ""),
            **_ingredients_to_form(cocktail),
            "fremgangsmaade": cocktail.get("fremgangsmaade", ""),
            "pynt": cocktail.get("pynt", ""),
            "noter": cocktail.get("noter", ""),
            "karboneringstid_timer": cocktail.get(
                "karbonering", {}
            ).get("tid_timer", 24),
            "serveringstips": cocktail.get(
                "serveringstips",
                "",
            ),
        }

        return self.async_show_form(
            step_id="edit_cocktail_form",
            data_schema=await self._cocktail_schema(
                defaults,
                include_id=True,
                ingredient_count=self._ingredient_count,
            ),
            errors=errors,
        )

    async def async_step_delete_cocktail(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Choose and confirm a cocktail deletion."""
        cocktails = self._coordinator.get_all_cocktails()

        if not cocktails:
            return self.async_abort(reason="no_cocktails")

        if user_input is not None:
            cocktail_id = str(user_input["cocktail_id"])

            if not user_input.get("confirm_delete", False):
                return self.async_show_form(
                    step_id="delete_cocktail",
                    data_schema=await self._delete_schema(
                        cocktail_id
                    ),
                    errors={
                        "confirm_delete": "confirmation_required"
                    },
                )

            cocktail = self._coordinator.get_cocktail(
                cocktail_id
            )
            name = str(
                cocktail.get("navn", cocktail_id)
            )

            deleted = await self._coordinator.async_delete_cocktail(
                cocktail_id
            )

            if not deleted:
                return self.async_abort(
                    reason="cocktail_not_found"
                )

            return self.async_abort(
                reason="cocktail_deleted",
                description_placeholders={
                    "name": name,
                },
            )

        return self.async_show_form(
            step_id="delete_cocktail",
            data_schema=await self._delete_schema(),
        )

    async def _cocktail_schema(
        self,
        defaults: dict[str, Any] | None = None,
        *,
        include_id: bool = False,
        ingredient_count: int | None = None,
    ) -> vol.Schema:
        """Build the create/edit cocktail form."""
        values = defaults or {}
        categories = await self._coordinator.async_list_categories()

        if not categories:
            categories = ["cocktails"]

        fields: dict[Any, Any] = {}

        if include_id:
            fields[
                vol.Required(
                    "id",
                    default=values.get("id", ""),
                )
            ] = TextSelector(
                TextSelectorConfig()
            )

        fields[
            vol.Required(
                "navn",
                default=values.get("navn", ""),
            )
        ] = TextSelector(
            TextSelectorConfig()
        )

        fields[
            vol.Required(
                "kategori",
                default=values.get(
                    "kategori",
                    categories[0],
                ),
            )
        ] = SelectSelector(
            SelectSelectorConfig(
                options=categories,
                sort=True,
            )
        )

        fields[
            vol.Optional(
                "ny_kategori",
                default=values.get("ny_kategori", ""),
            )
        ] = TextSelector(
            TextSelectorConfig()
        )

        fields[
            vol.Required(
                "tema",
                default=values.get("tema", self._selected_theme),
            )
        ] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    {
                        "value": values.get("tema", self._selected_theme),
                        "label": COCKTAIL_THEMES.get(
                            values.get("tema", self._selected_theme),
                            COCKTAIL_THEMES["klassisk"],
                        )["label"],
                    }
                ],
                sort=False,
            )
        )

        fields[
            vol.Optional(
                "ikon_override",
                default=values.get("ikon_override", ""),
            )
        ] = TextSelector(TextSelectorConfig())

        theme_id = values.get("tema", self._selected_theme or "klassisk")
        theme_color = COCKTAIL_THEMES.get(
            theme_id,
            COCKTAIL_THEMES["klassisk"],
        )["color"]

        fields[
            vol.Required(
                "brug_tema_farve",
                default=values.get(
                    "brug_tema_farve",
                    str(values.get("farve", theme_color)).upper()
                    == str(theme_color).upper(),
                ),
            )
        ] = BooleanSelector()

        fields[
            vol.Optional(
                "brugerdefineret_farve_rgb",
                default=values.get(
                    "brugerdefineret_farve_rgb",
                    _hex_to_rgb(values.get("farve") or theme_color),
                ),
            )
        ] = selector({"color_rgb": {}})

        fields[
            vol.Required(
                "automatisk_beregning",
                default=values.get("automatisk_beregning", True),
            )
        ] = BooleanSelector()

        fields[
            vol.Required(
                "beregn_fra",
                default=values.get("beregn_fra", "glass"),
            )
        ] = SelectSelector(
            SelectSelectorConfig(
                options=[
                    {"value": "glass", "label": "Pr. glas"},
                    {"value": "two_liter", "label": "2 liter"},
                    {"value": "nine_liter", "label": "9 liter"},
                ],
                sort=False,
            )
        )

        fields[
            vol.Required(
                "automatisk_abv",
                default=values.get("automatisk_abv", True),
            )
        ] = BooleanSelector()

        fields[
            vol.Required(
                "abv",
                default=values.get("abv", 0),
            )
        ] = NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=100,
                step=0.1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="%",
            )
        )

        fields[
            vol.Required(
                "co2",
                default=values.get("co2", 2.5),
            )
        ] = NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=6,
                step=0.1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="vol",
            )
        )

        fields[
            vol.Required(
                "temperatur",
                default=values.get("temperatur", 4),
            )
        ] = NumberSelector(
            NumberSelectorConfig(
                min=-10,
                max=30,
                step=0.5,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="°C",
            )
        )

        fields[
            vol.Optional(
                "glas",
                default=values.get("glas", ""),
            )
        ] = TextSelector(
            TextSelectorConfig()
        )

        row_count = ingredient_count or self._ingredient_count or 1

        for index in range(1, row_count + 1):
            fields[
                vol.Optional(
                    f"ingrediens_{index}_navn",
                    default=values.get(
                        f"ingrediens_{index}_navn",
                        (
                            ("Gin", "Mangopuré", "Limesaft")[index - 1]
                            if not defaults and index <= 3
                            else ""
                        ),
                    ),
                )
            ] = TextSelector(TextSelectorConfig())

            fields[
                vol.Required(
                    f"ingrediens_{index}_alkoholprocent",
                    default=values.get(
                        f"ingrediens_{index}_alkoholprocent",
                        37.5 if not defaults and index == 1 else 0,
                    ),
                )
            ] = NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=0.1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            )

            fields[
                vol.Optional(
                    f"ingrediens_{index}_glas",
                    default=values.get(
                        f"ingrediens_{index}_glas",
                        (
                            ("4 cl", "3 cl", "2 cl")[index - 1]
                            if not defaults and index <= 3
                            else ""
                        ),
                    ),
                )
            ] = TextSelector(TextSelectorConfig())

            fields[
                vol.Optional(
                    f"ingrediens_{index}_2l",
                    default=values.get(
                        f"ingrediens_{index}_2l",
                        (
                            ("40 cl", "30 cl", "20 cl")[index - 1]
                            if not defaults and index <= 3
                            else ""
                        ),
                    ),
                )
            ] = TextSelector(TextSelectorConfig())

            fields[
                vol.Optional(
                    f"ingrediens_{index}_9l",
                    default=values.get(
                        f"ingrediens_{index}_9l",
                        (
                            ("180 cl", "135 cl", "90 cl")[index - 1]
                            if not defaults and index <= 3
                            else ""
                        ),
                    ),
                )
            ] = TextSelector(TextSelectorConfig())

        fields[
            vol.Optional(
                "fremgangsmaade",
                default=values.get("fremgangsmaade", ""),
            )
        ] = TextSelector(TextSelectorConfig(multiline=True))

        fields[
            vol.Optional(
                "pynt",
                default=values.get("pynt", ""),
            )
        ] = TextSelector(TextSelectorConfig())

        fields[
            vol.Optional(
                "noter",
                default=values.get("noter", ""),
            )
        ] = TextSelector(TextSelectorConfig(multiline=True))

        fields[
            vol.Required(
                "karboneringstid_timer",
                default=values.get("karboneringstid_timer", 24),
            )
        ] = NumberSelector(
            NumberSelectorConfig(
                min=0,
                max=168,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="timer",
            )
        )

        fields[
            vol.Optional(
                "serveringstips",
                default=values.get("serveringstips", ""),
            )
        ] = TextSelector(TextSelectorConfig(multiline=True))

        return vol.Schema(fields)

    @staticmethod
    def _ingredient_count_schema(
        default: int,
        *,
        theme_default: str = "klassisk",
        include_theme: bool = False,
    ) -> vol.Schema:
        """Return selectors for ingredient rows and optionally cocktail theme."""
        fields: dict[Any, Any] = {
            vol.Required(
                "ingredient_count",
                default=str(default),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {
                            "value": str(count),
                            "label": (
                                "1 ingrediens"
                                if count == 1
                                else f"{count} ingredienser"
                            ),
                        }
                        for count in range(1, 13)
                    ],
                    sort=False,
                )
            )
        }

        if include_theme:
            fields[
                vol.Required(
                    "tema",
                    default=theme_default,
                )
            ] = SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {
                            "value": key,
                            "label": value["label"],
                        }
                        for key, value in COCKTAIL_THEMES.items()
                    ],
                    sort=False,
                )
            )

        return vol.Schema(fields)

    async def _delete_schema(
        self,
        selected: str | None = None,
    ) -> vol.Schema:
        """Build the delete confirmation form."""
        cocktails = self._coordinator.get_all_cocktails()

        options = [
            {
                "value": cocktail_id,
                "label": self._cocktail_label(
                    cocktail_id,
                    cocktail,
                ),
            }
            for cocktail_id, cocktail in sorted(
                cocktails.items(),
                key=lambda item: str(
                    item[1].get("navn", item[0])
                ).lower(),
            )
        ]

        selector = SelectSelector(
            SelectSelectorConfig(
                options=options,
                sort=False,
            )
        )

        schema: dict[Any, Any] = {
            vol.Required(
                "cocktail_id",
                default=selected or options[0]["value"],
            ): selector,
            vol.Required(
                "confirm_delete",
                default=False,
            ): BooleanSelector(),
        }

        return vol.Schema(schema)

    @staticmethod
    def _cocktail_label(
        cocktail_id: str,
        cocktail: dict[str, Any],
    ) -> str:
        """Return a readable cocktail selector label."""
        icon = cocktail.get("ikon", "🍹")
        name = cocktail.get("navn", cocktail_id)
        category = cocktail.get("kategori", "ukendt")

        return f"{icon} {name} · {category}"

    def _prepare_cocktail_data(
        self,
        user_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare form data for CocktailManager."""
        data = dict(user_input)
        new_category = str(
            data.pop("ny_kategori", "")
        ).strip()

        if new_category:
            data["kategori"] = new_category

        use_theme_color = bool(data.pop("brug_tema_farve", False))
        rgb = data.pop("brugerdefineret_farve_rgb", None)

        if use_theme_color:
            data["brugerdefineret_farve"] = ""
        elif isinstance(rgb, (list, tuple)) and len(rgb) == 3:
            try:
                data["brugerdefineret_farve"] = (
                    f"#{int(rgb[0]):02X}{int(rgb[1]):02X}{int(rgb[2]):02X}"
                )
            except (TypeError, ValueError):
                data["brugerdefineret_farve"] = ""

        ingredients = []
        for index in range(1, self._ingredient_count + 1):
            name = str(data.pop(f"ingrediens_{index}_navn", "")).strip()
            alcohol_percentage = data.pop(
                f"ingrediens_{index}_alkoholprocent", 0
            )
            glass = str(data.pop(f"ingrediens_{index}_glas", "")).strip()
            two_liter = str(data.pop(f"ingrediens_{index}_2l", "")).strip()
            nine_liter = str(data.pop(f"ingrediens_{index}_9l", "")).strip()

            if name:
                ingredients.append(
                    {
                        "navn": name,
                        "alkoholprocent": alcohol_percentage,
                        "glas": glass,
                        "2_liter": two_liter,
                        "9_liter": nine_liter,
                    }
                )

        data["ingredienser"] = ingredients
        return data
