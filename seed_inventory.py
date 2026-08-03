"""seed_inventory.py — Add the handwritten section/shelf inventory to the database.

Each bin gets two barcodes:
  - Scan-In barcode:  S21-S1-001
  - Scan-Out barcode: S21-S1-001-OUT

Scanning the "-OUT" barcode and pressing Enter triggers a scan-out automatically.
Run this script whenever you need to (re-)populate the starting inventory list.
"""

import csv
import os
from collections import defaultdict

from database import Database
from paths import INPUT_DIR

CSV_PATH = os.path.join(INPUT_DIR, "pantry_inventory.csv")

# (section, shelf, item_name)
# Items are listed exactly as written in the photos; duplicates/crossed-out entries omitted.
ITEMS = [
    # Section 21
    (21, 1, "Stuffing / Mashed potatoes"),
    (21, 1, "Oatmeal"),
    (21, 1, "Carrots"),
    (21, 2, "Rice"),
    (21, 2, "Refried beans can"),
    (21, 3, "Diapers"),
    (21, 4, "Misc. Hygiene"),
    # Section 23
    (23, 1, "Misc. Products"),
    (23, 2, "Snacks"),
    # Section 24
    (24, 1, "Chicken ramen"),
    (24, 2, "Beef ramen"),
    (24, 2, "Misc. Ramen"),
    # Section 22 (overflow)
    (22, 1, "Ravioli / Spaghetti"),
    (22, 1, "Peanut butter"),
    (22, 1, "Breakfast drinks"),
    (22, 1, "Mac & cheese"),
    (22, 1, "Pinto beans dry"),
    (22, 2, "Pasta"),
    (22, 2, "Potatoes"),
    (22, 2, "Mixed box meals"),
    (22, 3, "Northern beans dry"),
    (22, 3, "Black beans dry"),
    (22, 3, "Red kidney beans dry"),
    (22, 3, "Chickpeas dry"),
    (22, 3, "Lentils dry"),
    # Section 20
    (20, 1, "Whole corn"),
    (20, 1, "Sweet corn"),
    (20, 2, "Peas"),
    (20, 2, "Cream corn"),
    (20, 2, "Soup"),
    (20, 2, "Chili"),
    (20, 3, "Cut green beans"),
    (20, 4, "Can meat"),
    (20, 4, "French green beans"),
    # Section 19 (overflow)
    (19, 1, "Hams"),
    (19, 1, "Misc vegetables"),
    (19, 2, "Beans canned"),
    (19, 2, "Black beans canned"),
    (19, 3, "Fruits"),
    (19, 4, "Tomatoes"),
    (19, 4, "Can fish"),
    # Section 13
    (13, 1, "Breakfast drinks"),
    (13, 1, "Waffle / Pancake mix"),
    (13, 2, "Sweet baked goods"),
    (13, 3, "Baked goods"),
]


def _barcode(section: int, shelf: int, index: int) -> str:
    return f"S{section:02d}-S{shelf}-{index:03d}"


def build_rows():
    counters = defaultdict(int)
    rows = []
    for section, shelf, name in ITEMS:
        counters[(section, shelf)] += 1
        idx = counters[(section, shelf)]
        bc_in = _barcode(section, shelf, idx)
        bc_out = f"{bc_in}-OUT"
        rows.append({
            "barcode": bc_in,
            "barcode_out": bc_out,
            "item_name": name,
            "brand": "",
            "category": f"Section {section}",
            "current_quantity": 0,
            "minimum_stock": 0,
            "storage_location": f"Section {section}, Shelf {shelf}",
            "expiration_date": "",
            "notes": "",
        })
    return rows


def write_csv(rows):
    fieldnames = [
        "barcode", "barcode_out", "item_name", "brand", "category",
        "current_quantity", "minimum_stock", "storage_location",
        "expiration_date", "notes",
    ]
    os.makedirs(INPUT_DIR, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {CSV_PATH}")


def seed_database(rows):
    db = Database()
    added = skipped = 0
    for row in rows:
        if db.get_item_by_barcode(row["barcode"]):
            skipped += 1
            continue
        ok, msg = db.add_item(
            barcode=row["barcode"],
            barcode_out=row["barcode_out"],
            item_name=row["item_name"],
            category=row["category"],
            quantity=row["current_quantity"],
            minimum_stock=row["minimum_stock"],
            notes=row["notes"],
            brand=row["brand"],
            storage_location=row["storage_location"],
            shelf_life_days=0,
            expiration_date=row["expiration_date"],
            nutrition_data="{}",
        )
        if ok:
            added += 1
        else:
            print(f"  ERROR adding {row['item_name']}: {msg}")
    print(f"Seeded {added} item(s); {skipped} already existed.")


if __name__ == "__main__":
    rows = build_rows()
    write_csv(rows)
    seed_database(rows)
