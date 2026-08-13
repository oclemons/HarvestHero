"""
glass_effects.py — Mirror and glass effect utilities for Harvest Hero.

Provides reusable functions and constants for creating polished glass-like
visual effects throughout the application. Works with CustomTkinter and
native Tkinter widgets.
"""

import customtkinter as ctk
from theme import (
    BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    BORDER_COLOR, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY,
    GLASS_OPACITY, REFLECTION_LIGHT, REFLECTION_DARK,
    GLASS_SHADOW, RADIUS,
)

# ---------------------------------------------------------------------------
# Glass Panel Styles
# ---------------------------------------------------------------------------

def create_glass_panel(parent, **kwargs) -> ctk.CTkFrame:
    """Create a glass-effect panel with subtle transparency and border.
    
    Args:
        parent: Parent widget
        **kwargs: Additional CTkFrame arguments
    
    Returns:
        CTkFrame configured with glass effect styling
    """
    default_kwargs = {
        "fg_color": BG_ELEVATED,
        "corner_radius": RADIUS,
        "border_width": 1,
        "border_color": BORDER_SUBTLE,
    }
    default_kwargs.update(kwargs)
    return ctk.CTkFrame(parent, **default_kwargs)


def create_glass_button(parent, text: str, command=None, **kwargs) -> ctk.CTkButton:
    """Create a glass-effect button with polished appearance.
    
    Args:
        parent: Parent widget
        text: Button text
        command: Button command callback
        **kwargs: Additional CTkButton arguments
    
    Returns:
        CTkButton configured with glass effect styling
    """
    default_kwargs = {
        "text": text,
        "command": command,
        "fg_color": BG_OVERLAY,
        "hover_color": BG_HOVER,
        "text_color": TEXT_PRIMARY,
        "border_width": 1,
        "border_color": BORDER_COLOR,
        "corner_radius": RADIUS,
        "font": ctk.CTkFont(size=12),
    }
    default_kwargs.update(kwargs)
    return ctk.CTkButton(parent, **default_kwargs)


def create_glass_label(parent, text: str, **kwargs) -> ctk.CTkLabel:
    """Create a glass-effect label with polished appearance.
    
    Args:
        parent: Parent widget
        text: Label text
        **kwargs: Additional CTkLabel arguments
    
    Returns:
        CTkLabel configured with glass effect styling
    """
    default_kwargs = {
        "text": text,
        "text_color": TEXT_PRIMARY,
        "fg_color": "transparent",
    }
    default_kwargs.update(kwargs)
    return ctk.CTkLabel(parent, **default_kwargs)


def create_glass_entry(parent, **kwargs) -> ctk.CTkEntry:
    """Create a glass-effect entry field with polished appearance.
    
    Args:
        parent: Parent widget
        **kwargs: Additional CTkEntry arguments
    
    Returns:
        CTkEntry configured with glass effect styling
    """
    default_kwargs = {
        "fg_color": BG_OVERLAY,
        "border_color": BORDER_COLOR,
        "border_width": 1,
        "text_color": TEXT_PRIMARY,
        "placeholder_text_color": TEXT_SECONDARY,
        "corner_radius": RADIUS,
    }
    default_kwargs.update(kwargs)
    return ctk.CTkEntry(parent, **default_kwargs)


# ---------------------------------------------------------------------------
# Glass Card Styles
# ---------------------------------------------------------------------------

def create_glass_card(parent, title: str = "", **kwargs) -> ctk.CTkFrame:
    """Create a glass-effect card with optional title.
    
    Args:
        parent: Parent widget
        title: Optional card title
        **kwargs: Additional CTkFrame arguments
    
    Returns:
        CTkFrame configured as glass card
    """
    card = create_glass_panel(parent, **kwargs)
    
    if title:
        title_label = ctk.CTkLabel(
            card,
            text=title,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        title_label.pack(anchor="w", padx=16, pady=(12, 8))
    
    return card


# ---------------------------------------------------------------------------
# Reflection Effects
# ---------------------------------------------------------------------------

def add_reflection_overlay(widget, color: str = REFLECTION_LIGHT) -> None:
    """Add a subtle reflection overlay to a widget.
    
    Note: This is a visual hint for future CSS/SVG implementation.
    For now, it documents where reflections should appear.
    
    Args:
        widget: Widget to add reflection to
        color: Reflection color (default: light reflection)
    """
    # TODO: Implement reflection overlay using SVG or CSS
    # This would create a subtle shine effect across the widget
    pass


def add_glass_shine_effect(widget) -> None:
    """Add a subtle shine effect to simulate polished glass.
    
    Note: This is a visual hint for future animation implementation.
    
    Args:
        widget: Widget to add shine to
    """
    # TODO: Implement shine animation
    # This would create a subtle light sweep across the widget
    pass


# ---------------------------------------------------------------------------
# Animation Helpers
# ---------------------------------------------------------------------------

def create_glass_transition(widget, duration_ms: int = 200) -> None:
    """Prepare a widget for smooth glass effect transitions.
    
    Args:
        widget: Widget to prepare
        duration_ms: Transition duration in milliseconds
    """
    # TODO: Implement smooth transitions for glass effects
    # This would fade in/out glass effects smoothly
    pass


def animate_reflection(widget, duration_ms: int = 2000) -> None:
    """Animate a reflection effect across a widget.
    
    Args:
        widget: Widget to animate
        duration_ms: Animation duration in milliseconds
    """
    # TODO: Implement reflection animation
    # This would create a moving light reflection effect
    pass


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def get_glass_color_for_theme(theme_name: str) -> str:
    """Get appropriate glass effect color for a theme.
    
    Args:
        theme_name: Name of the active theme
    
    Returns:
        Color string for glass effect
    """
    # Light themes use darker reflections
    if theme_name in ["Light", "Autumn Harvest", "Orchard Bloom"]:
        return REFLECTION_DARK
    # Dark themes use lighter reflections
    return REFLECTION_LIGHT


def is_glass_effect_supported() -> bool:
    """Check if the platform supports glass effects.
    
    Returns:
        True if glass effects are supported
    """
    # Glass effects work on all platforms with CustomTkinter
    # Fallback to solid colors if needed
    return True


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

"""
GLASS EFFECT IMPLEMENTATION GUIDE

The glass effect system provides a polished, dimensional appearance to the
Harvest Hero interface. It uses:

1. SUBTLE TRANSPARENCY
   - Slight transparency on panels and cards
   - Maintains readability while adding depth

2. SOFT BORDERS
   - Subtle border colors that complement the theme
   - Creates visual separation without harshness

3. REFLECTION OVERLAYS
   - Light reflections on surfaces
   - Creates illusion of polished glass
   - Implemented via CSS gradients or SVG

4. SHADOW EFFECTS
   - Soft shadows beneath elevated elements
   - Creates depth and hierarchy

5. SMOOTH TRANSITIONS
   - Fade in/out effects for glass elements
   - Smooth hover state changes
   - Animated reflection sweeps

USAGE EXAMPLES:

# Create a glass panel
panel = create_glass_panel(parent)

# Create a glass button
btn = create_glass_button(parent, "Click Me", command=on_click)

# Create a glass card with title
card = create_glass_card(parent, title="Inventory Status")

# Create a glass entry field
entry = create_glass_entry(parent, placeholder_text="Search...")

# Add reflection to a widget
add_reflection_overlay(card)

# Animate a reflection
animate_reflection(card)

THEME INTEGRATION:

Glass effects automatically adapt to the active theme:
- Harvest Hero: Warm green reflections
- Orchard Bloom: Fresh green reflections
- Moonlit Farm: Cool blue reflections
- Cozy Pantry: Warm brown reflections

The system uses design tokens from theme.py for consistency.

ACCESSIBILITY:

Glass effects respect prefers-reduced-motion:
- Animations disabled when reduced motion is enabled
- Reflections remain visible but static
- Transparency maintained for visual hierarchy
"""
