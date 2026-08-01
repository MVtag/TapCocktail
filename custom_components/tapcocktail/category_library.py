"""Persistent user-defined categories for TapCocktail libraries."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from .const import CATEGORY_LIBRARY_PATH

_KINDS = {"cocktail", "ingredient"}


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value).strip("_").lower()
    if not slug:
        raise ValueError("Kategorinavnet kan ikke bruges.")
    return slug


def _label(category_id: str) -> str:
    return str(category_id).replace("_", " ").replace("-", " ").title()


class CategoryLibrary:
    """Store category labels while keeping stable category IDs in recipes."""

    def __init__(self, path: str = CATEGORY_LIBRARY_PATH) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, list[dict[str, str]]]:
        fallback = {"cocktail": [], "ingredient": []}
        if not self.path.exists():
            return fallback
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return fallback
        if not isinstance(data, dict):
            return fallback
        return {
            kind: [
                {"id": str(item["id"]), "name": str(item["name"])}
                for item in data.get(kind, [])
                if isinstance(item, dict) and item.get("id") and item.get("name")
            ]
            for kind in _KINDS
        }

    def save(self, data: dict[str, list[dict[str, str]]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    def list(self, kind: str, used_ids: set[str] | None = None) -> list[dict[str, Any]]:
        if kind not in _KINDS:
            raise ValueError("Ukendt kategoritype.")
        stored = {item["id"]: item for item in self.load()[kind]}
        for category_id in used_ids or set():
            stored.setdefault(category_id, {"id": category_id, "name": _label(category_id)})
        return sorted(stored.values(), key=lambda item: item["name"].casefold())

    def upsert(
        self,
        kind: str,
        category: dict[str, Any],
        original_id: str | None = None,
    ) -> dict[str, str]:
        if kind not in _KINDS:
            raise ValueError("Ukendt kategoritype.")
        name = str(category.get("name") or "").strip()
        if not name:
            raise ValueError("Kategorinavnet må ikke være tomt.")
        category_id = _slugify(str(category.get("id") or name))
        data = self.load()
        existing = {
            item["id"]: item for item in data[kind]
            if item["id"] != original_id
        }
        if category_id in existing and category_id != original_id:
            raise ValueError("Der findes allerede en kategori med det navn.")
        saved = {"id": category_id, "name": name}
        existing[category_id] = saved
        data[kind] = sorted(existing.values(), key=lambda item: item["name"].casefold())
        self.save(data)
        return saved

    def delete(self, kind: str, category_id: str, used_ids: set[str]) -> bool:
        if kind not in _KINDS:
            raise ValueError("Ukendt kategoritype.")
        if category_id in used_ids:
            raise ValueError("Kategorien bruges stadig. Flyt indholdet, før den slettes.")
        data = self.load()
        remaining = [item for item in data[kind] if item["id"] != category_id]
        if len(remaining) == len(data[kind]):
            return False
        data[kind] = remaining
        self.save(data)
        return True
