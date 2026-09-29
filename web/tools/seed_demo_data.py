"""Populate only an explicitly configured demonstration database with sample stock."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def seed_demo_data():
    if os.environ.get("HARVESTHERO_ENVIRONMENT") != "demo":
        raise RuntimeError("Refusing to seed outside the demonstration environment")
    if not os.environ.get("HARVESTHERO_DEV_DIR"):
        raise RuntimeError("Set an isolated HARVESTHERO_DEV_DIR before seeding")

    from database import Database
    from seed_inventory import build_rows

    db = Database()
    added = 0
    for index, row in enumerate(build_rows()[:12]):
        if db.get_item_by_barcode(row["barcode"]):
            continue
        ok, message = db.add_item(
            barcode=row["barcode"], barcode_out=row["barcode_out"],
            item_name=row["item_name"], category=row["category"],
            quantity=(12, 4, 7, 9)[index % 4], minimum_stock=5,
            notes="Sample inventory — not actual pantry stock", brand="",
            storage_location=row["storage_location"],
        )
        if not ok:
            raise RuntimeError(f"Could not seed item {index}: {message}")
        added += 1
    return added


if __name__ == "__main__":
    print(f"Seeded {seed_demo_data()} sample items")
