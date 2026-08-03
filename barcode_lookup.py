"""barcode_lookup.py — Open Food Facts product lookup (no API key required).

Returns a normalized product dict so the scan screen can pre-fill every field.
Falls back gracefully when the network is unavailable or the product is unknown.
"""

import json
from typing import Optional

_OFF_URL = "https://world.openfoodfacts.org/api/v3/product/{}.json"

# ---------------------------------------------------------------------------
# Shelf-life estimates (days) keyed by lowercase category fragment
# ---------------------------------------------------------------------------
_SHELF_LIFE: dict = {
    "frozen":      540,
    "dairy":        14,
    "produce":       7,
    "bread":         7,
    "baked":        10,
    "meat":          4,
    "seafood":       3,
    "deli":          7,
    "juice":        30,
    "beverage":    365,
    "drink":       365,
    "water":       730,
    "canned":      730,
    "soup":        730,
    "pasta":       730,
    "rice":        730,
    "grain":       730,
    "cereal":      365,
    "snack":       180,
    "chip":        180,
    "cracker":     180,
    "cookie":      180,
    "candy":       365,
    "chocolate":   365,
    "sauce":       365,
    "condiment":   365,
    "oil":         730,
    "vinegar":     730,
    "coffee":      365,
    "tea":         365,
    "baby":        365,
    "infant":      365,
    "formula":     365,
    "supplement":  730,
    "vitamin":     730,
}

# ---------------------------------------------------------------------------
# Storage suggestions
# ---------------------------------------------------------------------------
_STORAGE: dict = {
    "frozen":    "Freezer",
    "dairy":     "Refrigerator",
    "produce":   "Refrigerator",
    "meat":      "Refrigerator",
    "seafood":   "Refrigerator",
    "deli":      "Refrigerator",
    "bread":     "Shelf",
    "baked":     "Shelf",
    "canned":    "Shelf",
    "soup":      "Shelf",
    "pasta":     "Shelf",
    "rice":      "Shelf",
    "grain":     "Shelf",
    "cereal":    "Shelf",
    "snack":     "Shelf",
    "chip":      "Shelf",
    "beverage":  "Shelf",
    "drink":     "Shelf",
    "water":     "Shelf",
    "baby":      "Shelf",
}


def _best_category(tags: list) -> str:
    """Pick the most specific English category label from Open Food Facts tags."""
    skip = {"foods", "food", "plant-based", "plant based", "groceries", "grocery"}
    for tag in tags:
        if not tag.startswith("en:"):
            continue
        label = tag[3:].replace("-", " ").title()
        if label.lower() in skip:
            continue
        return label
    return "Food"


def _estimate_shelf_life(category: str) -> int:
    cat = category.lower()
    for key, days in _SHELF_LIFE.items():
        if key in cat:
            return days
    return 365


def _suggest_storage(category: str) -> str:
    cat = category.lower()
    for key, loc in _STORAGE.items():
        if key in cat:
            return loc
    return "Shelf"


def _parse_nutrition(nutriments: dict) -> dict:
    return {
        "calories_per_100g": nutriments.get("energy-kcal_100g"),
        "protein_g":         nutriments.get("proteins_100g"),
        "fat_g":             nutriments.get("fat_100g"),
        "carbs_g":           nutriments.get("carbohydrates_100g"),
        "sodium_mg":         nutriments.get("sodium_100g") and
                             round(float(nutriments["sodium_100g"]) * 1000, 1),
        "sugar_g":           nutriments.get("sugars_100g"),
        "fiber_g":           nutriments.get("fiber_100g"),
    }


def lookup_barcode(barcode: str) -> Optional[dict]:
    """
    Query Open Food Facts for product data.

    Returns a dict with:
        name, brand, category, storage_suggestion, shelf_life_days,
        nutrition (dict), image_url, off_url

    Returns None when the barcode is unknown or the network is unavailable.
    """
    try:
        import requests  # lazy import so startup is fast if not available

        resp = requests.get(
            _OFF_URL.format(barcode),
            timeout=6,
            headers={"User-Agent": "InventoryControlCenter/2.0"},
        )
        if resp.status_code != 200:
            return None

        data = resp.json()

        if data.get("status") not in ("success", 1):
            return None

        p = data.get("product", {})

        name = (
            p.get("product_name_en")
            or p.get("product_name")
            or ""
        ).strip()
        if not name:
            return None

        brand = (p.get("brands") or "").split(",")[0].strip()
        category = _best_category(p.get("categories_tags", []))
        shelf_life = _estimate_shelf_life(category)
        storage    = _suggest_storage(category)
        nutrition  = _parse_nutrition(p.get("nutriments", {}))
        image_url  = p.get("image_front_url") or p.get("image_url") or ""

        return {
            "name":             name,
            "brand":            brand,
            "category":         category,
            "storage_suggestion": storage,
            "shelf_life_days":  shelf_life,
            "nutrition":        nutrition,
            "image_url":        image_url,
            "off_url":          f"https://world.openfoodfacts.org/product/{barcode}",
        }

    except Exception:
        return None
