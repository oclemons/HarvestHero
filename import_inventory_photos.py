"""import_inventory_photos.py — Parse the handwritten inventory notes in
input/Inventory/*.txt and add every item to the database with unique
scan-in / scan-out barcodes.

Run any time the .txt files change to bring the database up to date.
"""

import csv
import os
import re
import glob

from database import Database
from paths import INPUT_DIR

CSV_PATH = os.path.join(INPUT_DIR, "pantry_inventory.csv")
TEXT_DIR = os.path.join(INPUT_DIR, "Inventory")

SKIP_RE = re.compile(r"\b(empty|blank|crossed out|skip)\b", re.IGNORECASE)


def _parse_txt(path: str):
    """Yield (section, shelf, item_name) tuples from a text file."""
    section = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^Section\s+(\d+)", line, re.IGNORECASE)
            if m:
                section = int(m.group(1))
                continue
            m = re.match(r"^Shelf\s+(\d+):\s*(.*)", line, re.IGNORECASE)
            if m and section is not None:
                shelf = int(m.group(1))
                name = m.group(2).strip()
                if name and not SKIP_RE.search(name):
                    yield section, shelf, name


def _next_barcodes(db: Database, section: int, shelf: int):
    """Return the next unused (barcode, barcode_out) for a section/shelf."""
    prefix = f"S{section:02d}-S{shelf}-"
    existing = db.get_all_items()
    max_idx = 0
    for it in existing:
        if it["barcode"].startswith(prefix):
            suffix = it["barcode"][len(prefix):]
            if suffix[:3].isdigit():
                max_idx = max(max_idx, int(suffix[:3]))
    candidate = max_idx + 1
    while True:
        bc = f"{prefix}{candidate:03d}"
        if not db.get_item_by_barcode(bc):
            return bc, f"{bc}-OUT"
        candidate += 1


def _write_csv(db: Database):
    items = db.get_all_items()
    fieldnames = [
        "barcode", "barcode_out", "item_name", "brand", "category",
        "current_quantity", "minimum_stock", "storage_location",
        "expiration_date", "notes",
    ]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for it in items:
            writer.writerow({
                "barcode": it["barcode"],
                "barcode_out": it.get("barcode_out") or "",
                "item_name": it["item_name"],
                "brand": it.get("brand") or "",
                "category": it.get("category") or "",
                "current_quantity": it["current_quantity"],
                "minimum_stock": it["minimum_stock"],
                "storage_location": it.get("storage_location") or "",
                "expiration_date": it.get("expiration_date") or "",
                "notes": it.get("notes") or "",
            })


def main():
    db = Database()
    existing = {
        (it["item_name"], it["storage_location"]): it
        for it in db.get_all_items()
    }
    added = skipped = 0

    txt_files = sorted(glob.glob(os.path.join(TEXT_DIR, "*.txt")))
    for path in txt_files:
        for section, shelf, name in _parse_txt(path):
            storage = f"Section {section}, Shelf {shelf}"
            if (name, storage) in existing:
                skipped += 1
                continue

            barcode, barcode_out = _next_barcodes(db, section, shelf)
            ok, msg = db.add_item(
                barcode=barcode,
                barcode_out=barcode_out,
                item_name=name,
                category=f"Section {section}",
                quantity=0,
                minimum_stock=0,
                notes="",
                brand="",
                storage_location=storage,
                shelf_life_days=0,
                expiration_date="",
                nutrition_data="{}",
            )
            if ok:
                added += 1
            else:
                print(f"  ERROR adding {name}: {msg}")

    _write_csv(db)
    print(f"Added {added} new item(s); {skipped} already present.")
    print(f"Updated {CSV_PATH}")


if __name__ == "__main__":
    main()
