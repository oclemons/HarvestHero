"""barcode_manager.py — Manage barcode images and provide review functionality.

Handles loading, caching, and validating barcode reference images from
data/barcode_pic/. These are handwritten section/shelf inventory lists
that serve as reference material for the pantry layout.
"""

import os
from pathlib import Path
from PIL import Image
import threading
from typing import Optional, Dict, List, Tuple

from paths import DATA_DIR


BARCODE_PIC_DIR = os.path.join(DATA_DIR, "barcode_pic")


class BarcodeManager:
    """Manage barcode reference images."""

    def __init__(self):
        """Initialize the barcode manager."""
        self._cache: Dict[str, Optional[Image.Image]] = {}
        self._cache_lock = threading.Lock()
        self._load_errors: Dict[str, str] = {}

    def get_available_barcodes(self) -> List[str]:
        """Return sorted list of available barcode image filenames (without .jpg)."""
        if not os.path.isdir(BARCODE_PIC_DIR):
            return []
        
        files = []
        for f in os.listdir(BARCODE_PIC_DIR):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                name = os.path.splitext(f)[0]
                files.append(name)
        
        return sorted(files)

    def load_image(self, barcode_name: str, max_width: int = 800,
                   max_height: int = 600) -> Optional[Image.Image]:
        """Load and cache a barcode image, resizing to fit max dimensions.
        
        Args:
            barcode_name: Filename without extension (e.g., "82220")
            max_width: Maximum width for resizing
            max_height: Maximum height for resizing
        
        Returns:
            PIL Image or None if not found/failed to load
        """
        with self._cache_lock:
            if barcode_name in self._cache:
                return self._cache[barcode_name]
        
        # Try to find the file with any image extension
        for ext in ('.jpg', '.jpeg', '.png'):
            path = os.path.join(BARCODE_PIC_DIR, f"{barcode_name}{ext}")
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    img.load()  # Force load to catch corrupted files
                    
                    # Resize if needed
                    if img.width > max_width or img.height > max_height:
                        img.thumbnail((max_width, max_height), Image.LANCZOS)
                    
                    with self._cache_lock:
                        self._cache[barcode_name] = img
                    return img
                except Exception as e:
                    with self._cache_lock:
                        self._cache[barcode_name] = None
                        self._load_errors[barcode_name] = str(e)
                    return None
        
        with self._cache_lock:
            self._cache[barcode_name] = None
            self._load_errors[barcode_name] = "File not found"
        return None

    def get_thumbnail(self, barcode_name: str, size: int = 150) -> Optional[Image.Image]:
        """Load a barcode image as a small thumbnail.
        
        Args:
            barcode_name: Filename without extension
            size: Thumbnail size (square)
        
        Returns:
            PIL Image or None if not found/failed to load
        """
        img = self.load_image(barcode_name, max_width=size, max_height=size)
        if img:
            img.thumbnail((size, size), Image.LANCZOS)
        return img

    def get_error(self, barcode_name: str) -> Optional[str]:
        """Return the error message for a failed load, if any."""
        return self._load_errors.get(barcode_name)

    def clear_cache(self):
        """Clear the image cache to free memory."""
        with self._cache_lock:
            self._cache.clear()
            self._load_errors.clear()


# Global singleton instance
_manager = BarcodeManager()


def get_manager() -> BarcodeManager:
    """Return the global barcode manager instance."""
    return _manager
