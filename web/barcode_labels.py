"""Generate printable internal Code 128 barcode images without external services."""

import io
import re

from barcode import Code128
from barcode.writer import SVGWriter


def render_barcode(value: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", value):
        raise ValueError("Barcode contains characters that cannot be printed as a pantry label.")
    image = io.BytesIO()
    Code128(value, writer=SVGWriter()).write(image, options={
        "write_text": False,
        "module_width": 0.30,
        "module_height": 14.0,
        "quiet_zone": 3.0,
    })
    return image.getvalue()
