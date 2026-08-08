from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]

replacements = {
    ROOT / "custom_components/tapcocktail/strings.json": (
        "Fælles temperatursensor – karboneringsrum",
        "Temperatursensor – karboneringsrum",
    ),
    ROOT / "custom_components/tapcocktail/translations/da.json": (
        "Fælles temperatursensor – karboneringsrum",
        "Temperatursensor – karboneringsrum",
    ),
    ROOT / "custom_components/tapcocktail/translations/en.json": (
        "Shared temperature sensor – carbonation room",
        "Temperature sensor – carbonation room",
    ),
}

for path, (old, new) in replacements.items():
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected label not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

manifest_path = ROOT / "custom_components/tapcocktail/manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "2.6.1"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
