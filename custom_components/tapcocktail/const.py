DOMAIN = "tapcocktail"
COCKTAIL_PATH = "/config/cocktails"
INGREDIENT_LIBRARY_PATH = "/config/tapcocktail/ingredients.json"
CATEGORY_LIBRARY_PATH = "/config/tapcocktail/categories.json"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_selections"
TAPS_STORAGE_KEY = f"{DOMAIN}_taps"

CONF_MAX_TAPS = "max_taps"
CONF_TEMPERATURE_SENSOR_PREFIX = "temperature_sensor_hane"
DEFAULT_MAX_TAPS = 2
MIN_TAPS = 1
MAX_SUPPORTED_TAPS = 8

# Kept temporarily for backward compatibility with older local files.
MAX_TAPS = DEFAULT_MAX_TAPS

CARBONATION_OPTIONS = [
    "2 timer",
    "24 timer",
    "48 timer",
]

TAP_STATUS_IDLE = "idle"
TAP_STATUS_CARBONATING = "carbonating"
TAP_STATUS_READY = "ready"
