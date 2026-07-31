"""Persistent ingredient library for TapCocktail."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .const import INGREDIENT_LIBRARY_PATH

DEFAULT_INGREDIENTS = [
    {"id": "gin_37_5", "name": "Gin 37,5 %", "abv": 37.5},
    {"id": "gin_40", "name": "Gin 40 %", "abv": 40.0},
    {"id": "vodka_37_5", "name": "Vodka 37,5 %", "abv": 37.5},
    {"id": "vodka_40", "name": "Vodka 40 %", "abv": 40.0},
    {"id": "hvid_rom_37_5", "name": "Hvid rom 37,5 %", "abv": 37.5},
    {"id": "passoa", "name": "Passoã", "abv": 17.0},
    {"id": "fanta_exotic", "name": "Fanta Exotic", "abv": 0.0},
    {"id": "appelsinjuice", "name": "Appelsinjuice", "abv": 0.0},
    {"id": "limejuice", "name": "Limejuice", "abv": 0.0},
    {"id": "sukkersirup", "name": "Sukkersirup", "abv": 0.0},
]


class IngredientLibrary:
    """Read and write user ingredients without changing recipe snapshots."""

    def __init__(self, path: str = INGREDIENT_LIBRARY_PATH) -> None:
        self.path = Path(path)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return [dict(item) for item in DEFAULT_INGREDIENTS]
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return [dict(item) for item in DEFAULT_INGREDIENTS]
        return data if isinstance(data, list) else [dict(item) for item in DEFAULT_INGREDIENTS]

    def save(self, ingredients: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(ingredients, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    def upsert(self, ingredient: dict[str, Any], original_id: str | None = None) -> dict[str, Any]:
        ingredients = self.load()
        item_id = str(ingredient["id"]).strip().lower().replace(" ", "_")
        saved = {"id": item_id, "name": str(ingredient["name"]).strip(), "abv": float(ingredient["abv"])}
        if not saved["name"] or not 0 <= saved["abv"] <= 100:
            raise ValueError("Ingredient name and ABV must be valid.")
        ingredients = [item for item in ingredients if item.get("id") not in {item_id, original_id}]
        ingredients.append(saved)
        ingredients.sort(key=lambda item: str(item.get("name", "")).casefold())
        self.save(ingredients)
        return saved

    def delete(self, item_id: str) -> bool:
        ingredients = self.load()
        remaining = [item for item in ingredients if item.get("id") != item_id]
        if len(remaining) == len(ingredients):
            return False
        self.save(remaining)
        return True
