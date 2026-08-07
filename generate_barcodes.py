"""generate_barcodes.py — Render printable Code 128 barcodes for the pantry.

For every item in seed_inventory.ITEMS, this script produces a Scan-In
and a Scan-Out barcode (as Code 128, the same format a USB HID scanner
speaks by default). All barcodes are laid out on Letter-size pages
inside a single PDF, ready to print, cut, and stick on the shelves.

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
from seed_inventory import build_rows

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


FONT_TITLE = _load_font(22)
FONT_LOC   = _load_font(16)
FONT_TAG   = _load_font(18)


# ---------------------------------------------------------------------------
# Barcode rendering
# ---------------------------------------------------------------------------

def _render_barcode(value: str) -> Image.Image:
    """Return a PIL image of `value` encoded as Code 128 with the human-
    readable text underneath."""
    writer = ImageWriter()
    buf = io.BytesIO()
    Code128(value, writer=writer).write(
        buf,
        options={
            "module_width":  0.28,
            "module_height": 12,
            "font_size":     10,
            "text_distance": 3,
            "quiet_zone":    3,
            "write_text":    True,
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


# ---------------------------------------------------------------------------
# Page composition
# ---------------------------------------------------------------------------

def _draw_row(page: Image.Image, draw: ImageDraw.ImageDraw,
              row_top: int, row: dict) -> None:
    """Draw one item's Scan-In / Scan-Out pair as a single row."""
    title = row["item_name"]
    loc   = row["storage_location"]

    # Header
    draw.text((MARGIN_X, row_top), title, fill="black", font=FONT_TITLE)
    draw.text((MARGIN_X, row_top + 28), loc, fill="#444444", font=FONT_LOC)

    # Divider under header
    y_bar = row_top + 56
    draw.line([(MARGIN_X, y_bar), (PAGE_W - MARGIN_X, y_bar)],
              fill="#cccccc", width=1)

    max_h = ROW_H - 90
    max_w = COL_W - 20

    for col, (label, value, colour) in enumerate((
        ("SCAN IN",  row["barcode"],     "#0B7A3B"),
        ("SCAN OUT", row["barcode_out"], "#B4451E"),
    )):
        col_x = MARGIN_X + col * COL_W
        draw.text((col_x, y_bar + 6), label, fill=colour, font=FONT_TAG)

        bc_img = _fit_barcode(_render_barcode(value), max_w, max_h - 22)
        # centre horizontally within the column
        x = col_x + (COL_W - bc_img.width) // 2
        y = y_bar + 34
        page.paste(bc_img, (x, y))


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
            sep_y = row_top + ROW_H - 6
            draw.line([(MARGIN_X, sep_y), (PAGE_W - MARGIN_X, sep_y)],
                      fill="#e6e6e6", width=1)

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

if __name__ == "__main__":
    rows = build_rows()
    out_pdf = os.path.join(OUT_DIR, "harvest_hero_barcodes.pdf")
    build_pdf(rows, out_pdf)
