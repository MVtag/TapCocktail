from __future__ import annotations

import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .const import COCKTAIL_PATH
from .themes import get_theme

_CATEGORY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

class CocktailValidationError(ValueError):
    pass

def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value).strip("_").lower()
    if not slug:
        raise CocktailValidationError("Cocktailnavnet kan ikke bruges som ID.")
    return slug

def _normalise_category(value: str) -> str:
    category = value.strip().lower().replace(" ", "_")
    if not _CATEGORY_PATTERN.fullmatch(category):
        raise CocktailValidationError(
            "Kategori må kun indeholde små bogstaver, tal, bindestreg og underscore."
        )
    return category

def _as_float(value: Any, field_name: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise CocktailValidationError(f"{field_name} skal være et tal.") from err
    if not minimum <= number <= maximum:
        raise CocktailValidationError(
            f"{field_name} skal være mellem {minimum} og {maximum}."
        )
    return number

_VOLUME_PATTERN = re.compile(
    r"^\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>ml|cl|dl|l)\s*$",
    re.IGNORECASE,
)


def _volume_to_ml(value: str) -> Decimal | None:
    """Parse ml, cl, dl or l and return millilitres."""
    text = str(value or "").strip()
    if not text:
        return None

    match = _VOLUME_PATTERN.fullmatch(text)
    if not match:
        raise CocktailValidationError(
            f"Kunne ikke forstå mængden '{text}'. Brug f.eks. 4 cl, 250 ml eller 1,5 l."
        )

    try:
        number = Decimal(match.group("value").replace(",", "."))
    except InvalidOperation as err:
        raise CocktailValidationError(
            f"Kunne ikke forstå mængden '{text}'."
        ) from err

    unit = match.group("unit").lower()
    factor = {
        "ml": Decimal("1"),
        "cl": Decimal("10"),
        "dl": Decimal("100"),
        "l": Decimal("1000"),
    }[unit]

    return number * factor


def _format_ml(value_ml: Decimal) -> str:
    """Format millilitres using a practical cocktail unit."""
    value_ml = value_ml.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    if value_ml >= 1000 and value_ml % 1000 == 0:
        return f"{int(value_ml / 1000)} l"

    if value_ml >= 100 and value_ml % 10 == 0:
        cl = value_ml / 10
        text = f"{cl.normalize():f}".rstrip("0").rstrip(".")
        return f"{text} cl"

    if value_ml % 10 == 0:
        cl = value_ml / 10
        text = f"{cl.normalize():f}".rstrip("0").rstrip(".")
        return f"{text} cl"

    text = f"{value_ml.normalize():f}".rstrip("0").rstrip(".")
    return f"{text} ml"


def _column_key(source: str) -> str:
    return {
        "glass": "glas",
        "two_liter": "2_liter",
        "nine_liter": "9_liter",
    }.get(source, "glas")


def _target_ml(source: str) -> Decimal:
    return {
        "two_liter": Decimal("2000"),
        "nine_liter": Decimal("9000"),
    }.get(source, Decimal("0"))


def _calculate_ingredient_amounts(
    ingredients: list[dict[str, str]],
    *,
    enabled: bool,
    source: str,
) -> tuple[list[dict[str, str]], dict[str, float | str | bool]]:
    """Calculate missing recipe sizes while preserving explicitly entered values."""
    if not ingredients:
        return ingredients, {
            "enabled": enabled,
            "source": source,
            "source_total_ml": 0.0,
            "two_liter_total_ml": 0.0,
            "nine_liter_total_ml": 0.0,
            "two_liter_difference_ml": -2000.0,
            "nine_liter_difference_ml": -9000.0,
        }

    source_key = _column_key(source)
    parsed_source: list[Decimal] = []

    for item in ingredients:
        parsed = _volume_to_ml(item.get(source_key, ""))
        if parsed is None:
            raise CocktailValidationError(
                f"Ingrediensen '{item.get('navn', '')}' mangler en mængde i beregningskolonnen."
            )
        parsed_source.append(parsed)

    source_total = sum(parsed_source, Decimal("0"))
    if source_total <= 0:
        raise CocktailValidationError("Den valgte beregningskolonne har ingen samlet mængde.")

    if enabled:
        for item, source_ml in zip(ingredients, parsed_source):
            ratio = source_ml / source_total

            if source != "two_liter" or not item.get("2_liter"):
                item["2_liter"] = _format_ml(ratio * Decimal("2000"))

            if source != "nine_liter" or not item.get("9_liter"):
                item["9_liter"] = _format_ml(ratio * Decimal("9000"))

            # Per-glass values cannot be inferred without a selected serving size.
            # Keep explicitly entered glass values as-is.

    totals: dict[str, Decimal] = {}
    for key in ("glas", "2_liter", "9_liter"):
        total = Decimal("0")
        for item in ingredients:
            parsed = _volume_to_ml(item.get(key, ""))
            if parsed is not None:
                total += parsed
        totals[key] = total

    return ingredients, {
        "enabled": enabled,
        "source": source,
        "source_total_ml": float(source_total),
        "two_liter_total_ml": float(totals["2_liter"]),
        "nine_liter_total_ml": float(totals["9_liter"]),
        "two_liter_difference_ml": float(totals["2_liter"] - Decimal("2000")),
        "nine_liter_difference_ml": float(totals["9_liter"] - Decimal("9000")),
        "two_liter_ok": abs(totals["2_liter"] - Decimal("2000")) <= Decimal("5"),
        "nine_liter_ok": abs(totals["9_liter"] - Decimal("9000")) <= Decimal("5"),
    }


def parse_ingredients(value):
    if isinstance(value, list):
        return value
    result = []
    for line_number, raw_line in enumerate((value or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 4:
            raise CocktailValidationError(
                f"Ingredienslinje {line_number} skal være: Navn | pr. glas | 2 liter | 9 liter"
            )
        result.append({
            "navn": parts[0],
            "glas": parts[1],
            "2_liter": parts[2],
            "9_liter": parts[3],
        })
    return result

class CocktailManager:
    def __init__(self, folder_path: str = COCKTAIL_PATH) -> None:
        self.root = Path(folder_path)

    def list_categories(self) -> list[str]:
        self.root.mkdir(parents=True, exist_ok=True)
        return sorted(
            p.name for p in self.root.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )

    def get_cocktail_file(self, cocktail_id: str) -> Path | None:
        safe_id = _slugify(cocktail_id)
        for file_path in self.root.rglob("*.json"):
            try:
                with file_path.open("r", encoding="utf-8") as file:
                    data = json.load(file)
            except (OSError, json.JSONDecodeError):
                continue
            if str(data.get("id", file_path.stem)) == safe_id:
                return file_path
        return None

    def save_cocktail(self, data: dict[str, Any], *, original_id: str | None = None):
        name = str(data.get("navn", "")).strip()
        if not name:
            raise CocktailValidationError("Navn må ikke være tomt.")

        cocktail_id = _slugify(str(data.get("id") or name))
        category = _normalise_category(str(data.get("kategori") or "cocktails"))
        theme_id = str(data.get("tema") or "klassisk")
        theme = get_theme(theme_id)

        icon = str(data.get("ikon_override") or "").strip() or theme["icon"]
        custom_color = str(data.get("brugerdefineret_farve") or "").strip()
        color = custom_color or theme["color"]

        if not _COLOR_PATTERN.fullmatch(color):
            raise CocktailValidationError(
                "Brugerdefineret farve skal være en HEX-farve som #7ed957."
            )

        co2 = _as_float(data.get("co2", 2.5), "CO₂", 0, 6)

        ingredients = parse_ingredients(data.get("ingredienser"))
        auto_calculate = bool(data.get("automatisk_beregning", True))
        calculation_source = str(data.get("beregn_fra") or "glass")

        ingredients, calculation = _calculate_ingredient_amounts(
            ingredients,
            enabled=auto_calculate,
            source=calculation_source,
        )

        cocktail = {
            "id": cocktail_id,
            "navn": name,
            "tema": theme_id,
            "ikon": icon,
            "farve": color.upper(),
            "abv": _as_float(data.get("abv", 0), "ABV", 0, 100),
            "co2": co2,
            "temperatur": _as_float(data.get("temperatur", 4), "Temperatur", -10, 30),
            "glas": str(data.get("glas") or "").strip(),
            "ingredienser": ingredients,
            "beregning": calculation,
            "fremgangsmaade": str(data.get("fremgangsmaade") or "").strip(),
            "pynt": str(data.get("pynt") or "").strip(),
            "noter": str(data.get("noter") or "").strip(),
            "karbonering": {
                "tid_timer": _as_float(
                    data.get("karboneringstid_timer", 24),
                    "Karboneringstid",
                    0,
                    168,
                ),
                "vol_co2": co2,
            },
            "serveringstips": str(data.get("serveringstips") or "").strip(),
        }

        self.root.mkdir(parents=True, exist_ok=True)
        category_path = self.root / category
        category_path.mkdir(parents=True, exist_ok=True)
        target_path = category_path / f"{cocktail_id}.json"

        existing_path = self.get_cocktail_file(original_id) if original_id else (
            target_path if target_path.exists() else None
        )

        if (
            target_path.exists()
            and existing_path is not None
            and target_path.resolve() != existing_path.resolve()
        ):
            raise CocktailValidationError(
                f"Der findes allerede en cocktail med ID '{cocktail_id}'."
            )

        with target_path.open("w", encoding="utf-8") as file:
            json.dump(cocktail, file, ensure_ascii=False, indent=2)
            file.write("\n")

        if (
            existing_path is not None
            and existing_path.exists()
            and existing_path.resolve() != target_path.resolve()
        ):
            existing_path.unlink()

        result = cocktail.copy()
        result["kategori"] = category
        return result

    def delete_cocktail(self, cocktail_id: str) -> bool:
        file_path = self.get_cocktail_file(cocktail_id)
        if file_path is None:
            return False
        file_path.unlink()
        return True
