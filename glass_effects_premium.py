"""
glass_effects_premium.py — Premium 3-level mirror/glass effect system for Harvest Hero.

Implements three distinct glass effect levels:

LEVEL 1 — SOFT GLASS:
Used on ordinary cards, tables, forms, and secondary surfaces.
- Light translucency
- Subtle blur effect (via border styling)
- Thin highlight edge
- Subtle environment tint
- Minimal depth

LEVEL 2 — REFLECTIVE GLASS:
Used on navigation, modal windows, selected pantry items, settings panels, important info.
- Stronger depth perception
- Clearly visible highlight across upper portion
- Layered borders
- More obvious environment reflection
- Subtle hover reflection

LEVEL 3 — HERO MIRROR:
Reserved for login panel, dashboard hero, Ava/Harvest AI, signature components.
- Strongest reflective appearance
- Polished glass with visible environmental reflection
- Lighting gradients
- Glass depth with layering
- Slow or interaction-triggered specular sweep
- Premium appearance

All effects are theme-aware and adapt to the active harvest environment.
"""

import customtkinter as ctk
from typing import Optional, Callable
import math


class GlassEffectManager:
    """Manages premium glass effects across the application."""

    def __init__(self, theme_tokens: dict):
        """Initialize with theme tokens.
        
        Args:
            theme_tokens: Dictionary of theme colors and settings
        """
        self.theme = theme_tokens
        self._reflection_color = self._get_reflection_color()
        self._glass_base = self._get_glass_base()

    def _get_reflection_color(self) -> str:
        """Get theme-appropriate reflection color.
        
        Returns:
            Hex color for reflections
        """
        # Map themes to reflection colors
        theme_name = self.theme.get("name", "Harvest Hero")
        
        reflection_map = {
            "Harvest Day": "#F0FFF4",  # Light green
            "Autumn Harvest": "#FEF3C7",  # Warm amber
            "Orchard Bloom": "#ECFDF5",  # Fresh mint
            "Moonlit Farm": "#F3F4F6",  # Cool silver
            "Cozy Pantry": "#FEF5E7",  # Warm cream
            "Farmers Market": "#FFFBEB",  # Soft yellow
            "Garden Morning": "#F0FDF4",  # Fresh green
        }
        
        return reflection_map.get(theme_name, "#FFFFFF")

    def _get_glass_base(self) -> str:
        """Get base glass color (slightly lighter than background).
        
        Returns:
            Hex color for glass base
        """
        bg_elevated = self.theme.get("BG_ELEVATED", "#162A1D")
        # Return slightly lighter version
        return bg_elevated

    # =========================================================================
    # LEVEL 1: SOFT GLASS
    # =========================================================================

    def create_soft_glass_panel(self, parent, **kwargs) -> ctk.CTkFrame:
        """Create a soft glass panel for secondary surfaces.
        
        Used on: Cards, tables, forms, secondary surfaces
        
        Features:
        - Light translucency
        - Subtle border
        - Thin highlight edge
        - Minimal depth
        
        Args:
            parent: Parent widget
            **kwargs: Additional CTkFrame arguments
        
        Returns:
            CTkFrame with soft glass styling
        """
        default_kwargs = {
            "fg_color": self._glass_base,
            "corner_radius": 12,
            "border_width": 1,
            "border_color": self.theme.get("BORDER_SUBTLE", "#1D2E22"),
        }
        default_kwargs.update(kwargs)
        
        frame = ctk.CTkFrame(parent, **default_kwargs)
        
        # Store metadata for animation
        frame._glass_level = 1
        frame._glass_manager = self
        
        return frame

    def create_soft_glass_button(self, parent, text: str, command: Optional[Callable] = None, **kwargs) -> ctk.CTkButton:
        """Create a soft glass button.
        
        Args:
            parent: Parent widget
            text: Button text
            command: Button callback
            **kwargs: Additional CTkButton arguments
        
        Returns:
            CTkButton with soft glass styling
        """
        default_kwargs = {
            "text": text,
            "command": command,
            "fg_color": self._glass_base,
            "hover_color": self.theme.get("BG_HOVER", "#1F3828"),
            "text_color": self.theme.get("TEXT_PRIMARY", "#F0FFF4"),
            "border_width": 1,
            "border_color": self.theme.get("BORDER_COLOR", "#2A4233"),
            "corner_radius": 10,
            "font": ctk.CTkFont(family="Helvetica", size=12),
        }
        default_kwargs.update(kwargs)
        
        button = ctk.CTkButton(parent, **default_kwargs)
        button._glass_level = 1
        button._glass_manager = self
        
        return button

    def create_soft_glass_card(self, parent, title: str = "", **kwargs) -> ctk.CTkFrame:
        """Create a soft glass card.
        
        Args:
            parent: Parent widget
            title: Optional card title
            **kwargs: Additional CTkFrame arguments
        
        Returns:
            CTkFrame configured as soft glass card
        """
        card = self.create_soft_glass_panel(parent, **kwargs)
        
        if title:
            title_label = ctk.CTkLabel(
                card,
                text=title,
                text_color=self.theme.get("TEXT_SECONDARY", "#A7C4B0"),
                font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"),
            )
            title_label.pack(anchor="w", padx=16, pady=(12, 8))
        
        return card

    # =========================================================================
    # LEVEL 2: REFLECTIVE GLASS
    # =========================================================================

    def create_reflective_glass_panel(self, parent, **kwargs) -> ctk.CTkFrame:
        """Create a reflective glass panel for important surfaces.
        
        Used on: Navigation, modals, selected items, settings, important info
        
        Features:
        - Stronger depth
        - Visible highlight band
        - Layered borders
        - Environment reflection
        - Subtle hover reflection
        
        Args:
            parent: Parent widget
            **kwargs: Additional CTkFrame arguments
        
        Returns:
            CTkFrame with reflective glass styling
        """
        default_kwargs = {
            "fg_color": self._glass_base,
            "corner_radius": 14,
            "border_width": 2,
            "border_color": self.theme.get("BORDER_COLOR", "#2A4233"),
        }
        default_kwargs.update(kwargs)
        
        frame = ctk.CTkFrame(parent, **default_kwargs)
        
        # Add inner highlight frame for depth
        highlight = ctk.CTkFrame(
            frame,
            fg_color="transparent",
            border_width=1,
            border_color=self._get_highlight_color(0.3),
            corner_radius=13,
        )
        highlight.place(relx=0, rely=0, relwidth=1, relheight=0.4)
        
        # Store metadata
        frame._glass_level = 2
        frame._glass_manager = self
        frame._highlight_frame = highlight
        
        return frame

    def create_reflective_glass_button(self, parent, text: str, command: Optional[Callable] = None, **kwargs) -> ctk.CTkButton:
        """Create a reflective glass button.
        
        Args:
            parent: Parent widget
            text: Button text
            command: Button callback
            **kwargs: Additional CTkButton arguments
        
        Returns:
            CTkButton with reflective glass styling
        """
        default_kwargs = {
            "text": text,
            "command": command,
            "fg_color": self._glass_base,
            "hover_color": self.theme.get("BG_HOVER", "#1F3828"),
            "text_color": self.theme.get("TEXT_PRIMARY", "#F0FFF4"),
            "border_width": 2,
            "border_color": self.theme.get("BORDER_COLOR", "#2A4233"),
            "corner_radius": 12,
            "font": ctk.CTkFont(family="Helvetica", size=13, weight="bold"),
        }
        default_kwargs.update(kwargs)
        
        button = ctk.CTkButton(parent, **default_kwargs)
        button._glass_level = 2
        button._glass_manager = self
        
        return button

    def create_reflective_glass_card(self, parent, title: str = "", **kwargs) -> ctk.CTkFrame:
        """Create a reflective glass card.
        
        Args:
            parent: Parent widget
            title: Optional card title
            **kwargs: Additional CTkFrame arguments
        
        Returns:
            CTkFrame configured as reflective glass card
        """
        card = self.create_reflective_glass_panel(parent, **kwargs)
        
        if title:
            title_label = ctk.CTkLabel(
                card,
                text=title,
                text_color=self.theme.get("TEXT_SECONDARY", "#A7C4B0"),
                font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"),
            )
            title_label.pack(anchor="w", padx=16, pady=(16, 12))
        
        return card

    # =========================================================================
    # LEVEL 3: HERO MIRROR
    # =========================================================================

    def create_hero_mirror_panel(self, parent, **kwargs) -> ctk.CTkFrame:
        """Create a hero mirror panel for signature components.
        
        Used on: Login panel, dashboard hero, Ava/Harvest AI, key components
        
        Features:
        - Strongest reflective appearance
        - Polished glass with environmental reflection
        - Lighting gradients
        - Glass depth with layering
        - Specular sweep animation ready
        
        Args:
            parent: Parent widget
            **kwargs: Additional CTkFrame arguments
        
        Returns:
            CTkFrame with hero mirror styling
        """
        default_kwargs = {
            "fg_color": self._glass_base,
            "corner_radius": 16,
            "border_width": 3,
            "border_color": self.theme.get("BORDER_COLOR", "#2A4233"),
        }
        default_kwargs.update(kwargs)
        
        frame = ctk.CTkFrame(parent, **default_kwargs)
        
        # Outer highlight for depth
        outer_highlight = ctk.CTkFrame(
            frame,
            fg_color="transparent",
            border_width=1,
            border_color=self._get_highlight_color(0.5),
            corner_radius=16,
        )
        outer_highlight.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Inner highlight band (upper portion)
        inner_highlight = ctk.CTkFrame(
            frame,
            fg_color=self._get_highlight_color(0.15),
            corner_radius=15,
        )
        inner_highlight.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.25)
        
        # Store metadata
        frame._glass_level = 3
        frame._glass_manager = self
        frame._outer_highlight = outer_highlight
        frame._inner_highlight = inner_highlight
        frame._reflection_sweep_progress = 0
        
        return frame

    def create_hero_mirror_button(self, parent, text: str, command: Optional[Callable] = None, **kwargs) -> ctk.CTkButton:
        """Create a hero mirror button.
        
        Args:
            parent: Parent widget
            text: Button text
            command: Button callback
            **kwargs: Additional CTkButton arguments
        
        Returns:
            CTkButton with hero mirror styling
        """
        default_kwargs = {
            "text": text,
            "command": command,
            "fg_color": self.theme.get("ACCENT", "#10B981"),
            "hover_color": self.theme.get("ACCENT_HOVER", "#34D399"),
            "text_color": "#FFFFFF",
            "border_width": 2,
            "border_color": self._get_highlight_color(0.4),
            "corner_radius": 14,
            "font": ctk.CTkFont(family="Helvetica", size=14, weight="bold"),
        }
        default_kwargs.update(kwargs)
        
        button = ctk.CTkButton(parent, **default_kwargs)
        button._glass_level = 3
        button._glass_manager = self
        
        return button

    def create_hero_mirror_card(self, parent, title: str = "", **kwargs) -> ctk.CTkFrame:
        """Create a hero mirror card.
        
        Args:
            parent: Parent widget
            title: Optional card title
            **kwargs: Additional CTkFrame arguments
        
        Returns:
            CTkFrame configured as hero mirror card
        """
        card = self.create_hero_mirror_panel(parent, **kwargs)
        
        if title:
            title_label = ctk.CTkLabel(
                card,
                text=title,
                text_color=self.theme.get("TEXT_PRIMARY", "#F0FFF4"),
                font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            )
            title_label.pack(anchor="w", padx=20, pady=(20, 16))
        
        return card

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_highlight_color(self, opacity: float = 0.3) -> str:
        """Get highlight color with opacity.
        
        Args:
            opacity: Opacity level (0.0 to 1.0)
        
        Returns:
            Hex color for highlight
        """
        # Use reflection color with opacity
        # Note: CustomTkinter doesn't support alpha in hex, so we use a lighter version
        base = self._reflection_color
        
        # Return a lighter version for highlight
        if opacity > 0.5:
            return self._reflection_color
        else:
            return self.theme.get("BORDER_SUBTLE", "#1D2E22")

    def add_reflection_sweep(self, widget, duration_ms: int = 800) -> None:
        """Add a reflection sweep animation to a widget.
        
        Args:
            widget: Widget to animate
            duration_ms: Animation duration in milliseconds
        """
        if not hasattr(widget, "_glass_level"):
            return
        
        # Store animation state
        widget._sweep_duration = duration_ms
        widget._sweep_start_time = 0
        widget._is_sweeping = False

    def trigger_reflection_sweep(self, widget) -> None:
        """Trigger a reflection sweep animation on a widget.
        
        Args:
            widget: Widget to animate
        """
        if not hasattr(widget, "_glass_level"):
            return
        
        widget._is_sweeping = True
        widget._sweep_start_time = 0
        self._animate_sweep(widget)

    def _animate_sweep(self, widget) -> None:
        """Animate reflection sweep.
        
        Args:
            widget: Widget to animate
        """
        if not hasattr(widget, "_is_sweeping") or not widget._is_sweeping:
            return
        
        # Animation logic would go here
        # For now, this is a placeholder for the animation framework
        pass

    def get_glass_level_description(self, level: int) -> str:
        """Get description of a glass level.
        
        Args:
            level: Glass level (1, 2, or 3)
        
        Returns:
            Description string
        """
        descriptions = {
            1: "Soft Glass - Secondary surfaces",
            2: "Reflective Glass - Important surfaces",
            3: "Hero Mirror - Signature components",
        }
        return descriptions.get(level, "Unknown")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_glass_panel(parent, level: int = 1, theme_tokens: Optional[dict] = None, **kwargs) -> ctk.CTkFrame:
    """Create a glass panel at specified level.
    
    Args:
        parent: Parent widget
        level: Glass level (1, 2, or 3)
        theme_tokens: Theme tokens dictionary
        **kwargs: Additional CTkFrame arguments
    
    Returns:
        CTkFrame with glass styling
    """
    if theme_tokens is None:
        theme_tokens = {}
    
    manager = GlassEffectManager(theme_tokens)
    
    if level == 1:
        return manager.create_soft_glass_panel(parent, **kwargs)
    elif level == 2:
        return manager.create_reflective_glass_panel(parent, **kwargs)
    elif level == 3:
        return manager.create_hero_mirror_panel(parent, **kwargs)
    else:
        return manager.create_soft_glass_panel(parent, **kwargs)


def create_glass_button(parent, text: str, level: int = 1, command: Optional[Callable] = None, theme_tokens: Optional[dict] = None, **kwargs) -> ctk.CTkButton:
    """Create a glass button at specified level.
    
    Args:
        parent: Parent widget
        text: Button text
        level: Glass level (1, 2, or 3)
        command: Button callback
        theme_tokens: Theme tokens dictionary
        **kwargs: Additional CTkButton arguments
    
    Returns:
        CTkButton with glass styling
    """
    if theme_tokens is None:
        theme_tokens = {}
    
    manager = GlassEffectManager(theme_tokens)
    
    if level == 1:
        return manager.create_soft_glass_button(parent, text, command, **kwargs)
    elif level == 2:
        return manager.create_reflective_glass_button(parent, text, command, **kwargs)
    elif level == 3:
        return manager.create_hero_mirror_button(parent, text, command, **kwargs)
    else:
        return manager.create_soft_glass_button(parent, text, command, **kwargs)


def create_glass_card(parent, title: str = "", level: int = 1, theme_tokens: Optional[dict] = None, **kwargs) -> ctk.CTkFrame:
    """Create a glass card at specified level.
    
    Args:
        parent: Parent widget
        title: Card title
        level: Glass level (1, 2, or 3)
        theme_tokens: Theme tokens dictionary
        **kwargs: Additional CTkFrame arguments
    
    Returns:
        CTkFrame configured as glass card
    """
    if theme_tokens is None:
        theme_tokens = {}
    
    manager = GlassEffectManager(theme_tokens)
    
    if level == 1:
        return manager.create_soft_glass_card(parent, title, **kwargs)
    elif level == 2:
        return manager.create_reflective_glass_card(parent, title, **kwargs)
    elif level == 3:
        return manager.create_hero_mirror_card(parent, title, **kwargs)
    else:
        return manager.create_soft_glass_card(parent, title, **kwargs)
