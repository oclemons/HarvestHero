"""Validate an inventory catalog CSV without trusting its stock counts."""

import csv
import io
import re
from uuid import uuid4

CODE = re.compile(r"[A-Za-z0-9-]{1,64}\Z")
LOCATION = re.compile(r"Section\s+(\d{1,3}),\s*Shelf\s+(\d{1,3})\Z", re.IGNORECASE)


def parse_catalog(contents: bytes) -> list[dict]:
    try:
        text = contents.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), strict=True)
        if not reader.fieldnames or not {"item_name", "storage_location"}.issubset(reader.fieldnames):
            raise ValueError("CSV needs item_name and storage_location columns.")
        source = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError("Upload a UTF-8 inventory CSV with a valid header.") from exc
    if not source or len(source) > 150:
        raise ValueError("Upload a CSV with 1–150 product rows.")

    rows = []
    seen_names = set()
    seen_codes = set()
    for number, raw in enumerate(source, start=1):
        name = (raw.get("item_name") or "").strip()
        location = (raw.get("storage_location") or "").strip()
        matched = LOCATION.fullmatch(location)
        token = uuid4().hex[:16].upper()
        code_in = (raw.get("barcode") or "").strip() or f"HHI-{token}"
        code_out = (raw.get("barcode_out") or "").strip() or f"HHO-{token}"
        duplicate_name = name.casefold() in seen_names
        seen_names.add(name.casefold())
        problem = None
        if not name or len(name) > 200:
            problem = "Missing or overlong item name"
        elif not matched or not int(matched[1]) or not int(matched[2]):
            problem = "Location must be Section N, Shelf N with positive numbers"
        elif not CODE.fullmatch(code_in) or not CODE.fullmatch(code_out) or code_in == code_out:
            problem = "Unsupported or matching pantry barcode values"
        elif code_in in seen_codes or code_out in seen_codes:
            problem = "Repeated pantry barcode in file"
        seen_codes.update((code_in, code_out))
        category = (raw.get("category") or "").strip()
        rows.append({
            "row_number": number, "item_name": name, "barcode": code_in,
            "barcode_out": code_out, "section_name": f"Section {int(matched[1])}" if matched else "",
            "shelf_name": f"Shelf {int(matched[2])}" if matched else "",
            "category": category if category and not re.fullmatch(r"Section\s+\d+", category, re.I) else "Uncategorized",
            "source_quantity": (raw.get("current_quantity") or "").strip()[:20],
            "duplicate_name": duplicate_name, "problem": problem,
        })
    return rows
