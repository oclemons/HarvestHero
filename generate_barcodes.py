"""generate_barcodes.py — Render printable Code 128 barcodes for the pantry.

Reads barcodes from the database and produces Scan-In and Scan-Out barcodes
(as Code 128, the same format a USB HID scanner speaks by default). All barcodes
are laid out on Letter-size pages inside a single PDF, ready to print, cut, and
stick on the shelves.

Layout:
  - 4 items per page (each item = one row containing Scan-In + Scan-Out
    side by side, plus a header with the item name and shelf location).

Usage:
    python generate_barcodes.py
    # writes output/barcodes/harvest_hero_barcodes.pdf
"""

from __future__ import annotations

import io
import os

from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

from paths import OUTPUT_DIR
from database import Database

# ---------------------------------------------------------------------------
# Page + layout constants (US Letter @ 150 DPI)
# ---------------------------------------------------------------------------

DPI          = 150
PAGE_W       = int(8.5 * DPI)   # 1275 px
PAGE_H       = int(11.0 * DPI)  # 1650 px
MARGIN_X     = int(0.5 * DPI)   # 0.5"
MARGIN_Y     = int(0.5 * DPI)
ITEMS_PER_PG = 4
ROW_H        = (PAGE_H - 2 * MARGIN_Y) // ITEMS_PER_PG
COL_W        = (PAGE_W - 2 * MARGIN_X) // 2  # scan-in | scan-out

OUT_DIR = os.path.join(OUTPUT_DIR, "barcodes")


# ---------------------------------------------------------------------------
# Font resolution (falls back to Pillow's built-in bitmap font)
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",       # macOS
        "/System/Library/Fonts/Helvetica.ttc",                 # macOS
        "C:/Windows/Fonts/arial.ttf",                          # Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",     # Linux
    ):
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                pass
    return ImageFont.load_default()


FONT_TITLE = _load_font(24)
FONT_LOC   = _load_font(15)
FONT_TAG   = _load_font(18)
FONT_CODE  = _load_font(16)


# ---------------------------------------------------------------------------
# Barcode rendering
# ---------------------------------------------------------------------------

def _render_barcode(value: str) -> Image.Image:
    """Return a PIL image of `value` encoded as Code 128 with NO embedded
    text — we render the human-readable value ourselves below the bars
    so it never overlaps the pattern."""
    writer = ImageWriter()
    buf = io.BytesIO()
    Code128(value, writer=writer).write(
        buf,
        options={
            "module_width":  0.32,
            "module_height": 14,
            "quiet_zone":    3,
            "write_text":    False,
        },
    )
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def _fit_barcode(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    ratio = min(max_w / img.width, max_h / img.height)
    if ratio >= 1.0:
        return img
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.LANCZOS)


def _text_size(draw: ImageDraw.ImageDraw, text: str,
               font: ImageFont.ImageFont) -> tuple[int, int]:
    """Return (width, height) of `text` in `font` — works for both truetype
    and Pillow's default bitmap font."""
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return r - l, b - t


# ---------------------------------------------------------------------------
# Page composition
# ---------------------------------------------------------------------------

TEXT_GAP    = 12   # gap between the barcode and the human-readable code
LABEL_GAP   = 10   # gap between the SCAN IN/OUT tag and the barcode
ROW_PAD_TOP = 12   # breathing room at the top of a row


def _draw_row(page: Image.Image, draw: ImageDraw.ImageDraw,
              row_top: int, row: dict) -> None:
    """Draw one item's Scan-In / Scan-Out pair as a single row."""
    title = row["item_name"]
    loc   = row["storage_location"]

    # Header block
    y = row_top + ROW_PAD_TOP
    draw.text((MARGIN_X, y), title, fill="black", font=FONT_TITLE)
    _, th = _text_size(draw, title, FONT_TITLE)
    y += th + 4
    draw.text((MARGIN_X, y), loc, fill="#555555", font=FONT_LOC)
    _, lh = _text_size(draw, loc, FONT_LOC)
    y += lh + 12

    # Divider under header
    draw.line([(MARGIN_X, y), (PAGE_W - MARGIN_X, y)],
              fill="#d0d0d0", width=1)
    y += 14

    # Reserve enough room in the row for: tag + barcode + code text
    remaining = (row_top + ROW_H) - y - 10
    max_bc_h  = max(60, remaining - 24 - LABEL_GAP - TEXT_GAP)  # 24 ~ tag+text lineheights
    max_bc_w  = COL_W - 30

    for col, (label, value, colour) in enumerate((
        ("SCAN IN",  row["barcode"],     "#0B7A3B"),
        ("SCAN OUT", row["barcode_out"], "#B4451E"),
    )):
        col_x = MARGIN_X + col * COL_W
        col_centre = col_x + COL_W // 2

        # Tag ("SCAN IN" / "SCAN OUT")
        tw, tth = _text_size(draw, label, FONT_TAG)
        draw.text((col_centre - tw // 2, y), label, fill=colour, font=FONT_TAG)

        # Barcode
        bc_img = _fit_barcode(_render_barcode(value), max_bc_w, max_bc_h)
        bc_x = col_centre - bc_img.width // 2
        bc_y = y + tth + LABEL_GAP
        page.paste(bc_img, (bc_x, bc_y))

        # Human-readable code
        cw, ch = _text_size(draw, value, FONT_CODE)
        code_x = col_centre - cw // 2
        code_y = bc_y + bc_img.height + TEXT_GAP
        draw.text((code_x, code_y), value, fill="black", font=FONT_CODE)


def _new_page() -> Image.Image:
    return Image.new("RGB", (PAGE_W, PAGE_H), "white")


def build_pdf(rows: list[dict], out_path: str) -> None:
    pages: list[Image.Image] = []
    page = _new_page()
    draw = ImageDraw.Draw(page)

    slot = 0
    for row in rows:
        if slot == ITEMS_PER_PG:
            pages.append(page)
            page = _new_page()
            draw = ImageDraw.Draw(page)
            slot = 0

        row_top = MARGIN_Y + slot * ROW_H
        _draw_row(page, draw, row_top, row)

        # Separator between rows (except the last one on the page)
        if slot < ITEMS_PER_PG - 1:
            sep_y = row_top + ROW_H - 4
            draw.line([(MARGIN_X, sep_y), (PAGE_W - MARGIN_X, sep_y)],
                      fill="#ececec", width=2)

        slot += 1

    if slot > 0:
        pages.append(page)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    first, *rest = pages
    first.save(
        out_path,
        format="PDF",
        resolution=DPI,
        save_all=True,
        append_images=rest,
    )
    print(f"Wrote {len(rows)} items across {len(pages)} pages -> {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def get_rows_from_database():
    """Get barcode rows from the database."""
    db = Database()
    items = db.get_all_items()
    
    rows = []
    for item in items:
        barcode = item.get("barcode", "").strip()
        barcode_out = item.get("barcode_out", "").strip()
        item_name = item.get("item_name", "Unknown")
        storage_location = item.get("storage_location", "")
        
        # Only include items with at least a barcode
        if barcode:
            rows.append({
                "barcode": barcode,
                "barcode_out": barcode_out,
                "item_name": item_name,
                "storage_location": storage_location,
            })
    
    return rows


if __name__ == "__main__":
    rows = get_rows_from_database()
    if not rows:
        print("No items with barcodes found in database.")
    else:
        os.makedirs(OUT_DIR, exist_ok=True)
        out_pdf = os.path.join(OUT_DIR, "harvest_hero_barcodes.pdf")
        build_pdf(rows, out_pdf)
