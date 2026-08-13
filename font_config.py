"""
font_config.py — Global font configuration for Harvest Hero.

Provides consistent Times New Roman font throughout the application
with configurable sizes for different UI elements.
"""

import customtkinter as ctk

# Global font family
FONT_FAMILY = "Times New Roman"

# Font sizes for different UI elements
class FontSizes:
    """Standard font sizes for UI elements."""
    
    # Headings
    TITLE_LARGE = 32      # Main titles (HARVEST HERO)
    TITLE_MEDIUM = 24     # Section titles
    TITLE_SMALL = 18      # Subsection titles
    
    # Body text
    BODY_LARGE = 14       # Large body text
    BODY_MEDIUM = 13      # Standard body text
    BODY_SMALL = 12       # Small body text
    
    # UI Elements
    LABEL_LARGE = 13      # Large labels
    LABEL_MEDIUM = 12     # Standard labels
    LABEL_SMALL = 11      # Small labels
    
    # Buttons
    BUTTON_LARGE = 16     # Large buttons
    BUTTON_MEDIUM = 14    # Standard buttons
    BUTTON_SMALL = 12     # Small buttons
    
    # Navigation
    NAV_LARGE = 14        # Large nav items
    NAV_MEDIUM = 13       # Standard nav items
    NAV_SMALL = 12        # Small nav items
    
    # Input fields
    INPUT_LARGE = 14      # Large input fields
    INPUT_MEDIUM = 13     # Standard input fields
    INPUT_SMALL = 12      # Small input fields


def create_font(size: int = 12, weight: str = "normal", family: str = None) -> ctk.CTkFont:
    """Create a font with consistent family and specified size.
    
    Args:
        size: Font size in points
        weight: Font weight ("normal", "bold")
        family: Font family (defaults to Times New Roman)
    
    Returns:
        CTkFont object
    """
    return ctk.CTkFont(
        family=family or FONT_FAMILY,
        size=size,
        weight=weight
    )


# Predefined font styles for common UI elements
FONT_TITLE_LARGE = create_font(FontSizes.TITLE_LARGE, "bold")
FONT_TITLE_MEDIUM = create_font(FontSizes.TITLE_MEDIUM, "bold")
FONT_TITLE_SMALL = create_font(FontSizes.TITLE_SMALL, "bold")

FONT_BODY_LARGE = create_font(FontSizes.BODY_LARGE)
FONT_BODY_MEDIUM = create_font(FontSizes.BODY_MEDIUM)
FONT_BODY_SMALL = create_font(FontSizes.BODY_SMALL)

FONT_LABEL_LARGE = create_font(FontSizes.LABEL_LARGE, "bold")
FONT_LABEL_MEDIUM = create_font(FontSizes.LABEL_MEDIUM, "bold")
FONT_LABEL_SMALL = create_font(FontSizes.LABEL_SMALL, "bold")

FONT_BUTTON_LARGE = create_font(FontSizes.BUTTON_LARGE, "bold")
FONT_BUTTON_MEDIUM = create_font(FontSizes.BUTTON_MEDIUM, "bold")
FONT_BUTTON_SMALL = create_font(FontSizes.BUTTON_SMALL, "bold")

FONT_NAV_LARGE = create_font(FontSizes.NAV_LARGE, "bold")
FONT_NAV_MEDIUM = create_font(FontSizes.NAV_MEDIUM, "bold")
FONT_NAV_SMALL = create_font(FontSizes.NAV_SMALL, "bold")

FONT_INPUT_LARGE = create_font(FontSizes.INPUT_LARGE)
FONT_INPUT_MEDIUM = create_font(FontSizes.INPUT_MEDIUM)
FONT_INPUT_SMALL = create_font(FontSizes.INPUT_SMALL)
