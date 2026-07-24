import json
import logging
from pathlib import Path

from .const import COCKTAIL_PATH

_LOGGER = logging.getLogger(__name__)


def load_cocktails():
    """Load all cocktails from JSON files."""

    cocktails = {}

    folder = Path(COCKTAIL_PATH)

    if not folder.exists():
        _LOGGER.warning(
            "Cocktail folder not found: %s",
            COCKTAIL_PATH,
        )
        return cocktails

    for file in folder.rglob("*.json"):

        try:
            with open(
                file,
                "r",
                encoding="utf-8",
            ) as f:
                cocktail = json.load(f)

            cocktail_id = cocktail.get(
                "id",
                file.stem,
            )

            # Finder automatisk kategori
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