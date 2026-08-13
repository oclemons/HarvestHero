"""generate_barcode_reference.py — Generate a reference guide for barcode images.

Creates a document that maps barcode sections to their reference images,
helping staff understand the pantry layout and verify barcode coverage.
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from paths import OUTPUT_DIR, DATA_DIR
from barcode_manager import get_manager


def _load_font(size: int) -> ImageFont.ImageFont:
    """Load a system font or fall back to default."""
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


def generate_reference_guide() -> str:
    """Generate a barcode reference guide and return the output path.
    
    Creates a PDF that shows:
    - List of all barcode sections
    - Thumbnail of each reference image
    - Status (found, missing, etc.)
    
    Returns:
        Path to the generated PDF
    """
    manager = get_manager()
    barcodes = manager.get_available_barcodes()
    
    if not barcodes:
        print("No barcode reference images found in data/barcode_pic/")
        return None
    
    # Create reference document
    DPI = 150
    PAGE_W = int(8.5 * DPI)   # 1275 px
    PAGE_H = int(11.0 * DPI)  # 1650 px
    MARGIN = int(0.5 * DPI)
    
    pages = []
    
    # Title page
    title_page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(title_page)
    
    font_title = _load_font(36)
    font_subtitle = _load_font(18)
    font_text = _load_font(12)
    
    draw.text(
        (MARGIN, PAGE_H // 2 - 100),
        "Harvest Hero",
        fill="black",
        font=font_title,
    )
    draw.text(
        (MARGIN, PAGE_H // 2 - 20),
        "Barcode Reference Guide",
        fill="#555555",
        font=font_subtitle,
    )
    draw.text(
        (MARGIN, PAGE_H // 2 + 60),
        f"Sections: {', '.join(barcodes)}",
        fill="#888888",
        font=font_text,
    )
    
    pages.append(title_page)
    
    # Content pages - one section per page
    for barcode_name in barcodes:
        page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
        draw = ImageDraw.Draw(page)
        
        # Header
        draw.text(
            (MARGIN, MARGIN),
            f"Section {barcode_name}",
            fill="black",
            font=font_title,
        )
        
        # Try to load and display the reference image
        img = manager.load_image(barcode_name, max_width=PAGE_W - 2*MARGIN,
                                 max_height=PAGE_H - 200)
        if img:
            # Center the image
            img_x = (PAGE_W - img.width) // 2
            img_y = MARGIN + 80
            page.paste(img, (img_x, img_y))
            status = "✓ Reference image available"
        else:
            error = manager.get_error(barcode_name)
            draw.text(
                (MARGIN, MARGIN + 100),
                f"Error: {error}",
                fill="#cc0000",
                font=font_text,
            )
            status = f"✗ Failed to load: {error}"
        
        # Footer with status
        draw.text(
            (MARGIN, PAGE_H - MARGIN - 30),
            status,
            fill="#666666",
            font=font_text,
        )
        
        pages.append(page)
    
    # Save as PDF
    out_dir = os.path.join(OUTPUT_DIR, "barcodes")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "barcode_reference_guide.pdf")
    
    first, *rest = pages
    first.save(
        out_path,
        format="PDF",
        resolution=DPI,
        save_all=True,
        append_images=rest,
    )
    
    print(f"✓ Generated barcode reference guide: {out_path}")
    print(f"  Sections: {len(barcodes)}")
    print(f"  Pages: {len(pages)}")
    
    return out_path


if __name__ == "__main__":
    generate_reference_guide()
