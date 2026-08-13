"""
settings_ui_enhanced.py — Enhanced settings interface with visual controls.

Provides:
- Theme selection with visual previews
- Color customization
- Animation controls
- Accessibility settings
- Sound and notification settings
- Professional UI
"""

import customtkinter as ctk
from typing import Callable, Optional
from glass_effects_premium import GlassEffectManager
from theme import (
    BG_BASE, BG_ELEVATED, BG_HOVER,
    ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE,
)
from theme_environments import get_all_theme_names, get_theme_description


class ThemePreviewCard(ctk.CTkFrame):
    """Visual preview of a theme."""

    def __init__(self, parent, theme_name: str, on_select: Callable, **kwargs):
        super().__init__(parent, fg_color=BG_ELEVATED, corner_radius=12,
                         border_width=1, border_color=BORDER_SUBTLE, **kwargs)
        self.theme_name = theme_name
        self.on_select = on_select
        self._build()
        self.bind("<Button-1>", lambda e: on_select(theme_name))
        for w in self.winfo_children():
            w.bind("<Button-1>", lambda e: on_select(theme_name))

    def _build(self):
        """Build preview card."""
        # Theme name
        ctk.CTkLabel(
            self, text=self.theme_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", padx=12, pady=(12, 4))

        # Description
        desc = get_theme_description(self.theme_name)
        ctk.CTkLabel(
            self, text=desc,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_SECONDARY, fg_color="transparent",
            wraplength=150
        ).pack(anchor="w", padx=12, pady=(0, 12))

    def set_selected(self, selected: bool):
        """Set selected state."""
        if selected:
            self.configure(border_width=2, border_color=ACCENT)
        else:
            self.configure(border_width=1, border_color=BORDER_SUBTLE)


class SettingsPanel(ctk.CTkFrame):
    """Enhanced settings panel with visual controls."""

    def __init__(self, parent, db, on_theme_change: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color=BG_BASE, **kwargs)
        self.db = db
        self.on_theme_change = on_theme_change
        self._glass_manager = GlassEffectManager({
            "name": "Harvest Day",
            "BG_ELEVATED": BG_ELEVATED,
            "BORDER_SUBTLE": BORDER_SUBTLE,
            "BORDER_COLOR": BORDER_COLOR,
            "TEXT_PRIMARY": TEXT_PRIMARY,
            "TEXT_SECONDARY": TEXT_SECONDARY,
        })
        self._build()

    def _build(self):
        """Build settings panel."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 12))

        ctk.CTkLabel(
            header, text="Settings",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w")

        # Scrollable content
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG_BASE
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Theme section
        self._build_theme_section()

        # Accessibility section
        self._build_accessibility_section()

        # Animation section
        self._build_animation_section()

        # Notifications section
        self._build_notifications_section()

    def _build_theme_section(self):
        """Build theme selection section."""
        section = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        section.pack(fill="x", pady=(0, 20))

        # Section title
        ctk.CTkLabel(
            section, text="Theme",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", pady=(0, 12))

        # Theme grid
        themes_frame = ctk.CTkFrame(section, fg_color="transparent")
        themes_frame.pack(fill="x")

        self.theme_cards = {}
        themes = get_all_theme_names()

        for i, theme in enumerate(themes):
            card = ThemePreviewCard(
                themes_frame, theme,
                on_select=self._on_theme_select,
                width=160, height=100
            )
            row = i // 3
            col = i % 3
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.theme_cards[theme] = card

        for i in range(3):
            themes_frame.grid_columnconfigure(i, weight=1)

    def _build_accessibility_section(self):
        """Build accessibility settings section."""
        section = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        section.pack(fill="x", pady=(0, 20))

        # Section title
        ctk.CTkLabel(
            section, text="Accessibility",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", pady=(0, 12))

        # Reduce motion toggle
        motion_frame = ctk.CTkFrame(section, fg_color="transparent")
        motion_frame.pack(fill="x", pady=8)

        self.reduce_motion_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            motion_frame, text="Reduce motion (respects prefers-reduced-motion)",
            variable=self.reduce_motion_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT,
            border_color=BORDER_COLOR, checkmark_color="white",
            corner_radius=4, width=16, height=16
        ).pack(anchor="w")

        # High contrast toggle
        contrast_frame = ctk.CTkFrame(section, fg_color="transparent")
        contrast_frame.pack(fill="x", pady=8)

        self.high_contrast_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            contrast_frame, text="High contrast mode",
            variable=self.high_contrast_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT,
            border_color=BORDER_COLOR, checkmark_color="white",
            corner_radius=4, width=16, height=16
        ).pack(anchor="w")

        # Larger text toggle
        text_frame = ctk.CTkFrame(section, fg_color="transparent")
        text_frame.pack(fill="x", pady=8)

        self.larger_text_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            text_frame, text="Larger text size",
            variable=self.larger_text_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT,
            border_color=BORDER_COLOR, checkmark_color="white",
            corner_radius=4, width=16, height=16
        ).pack(anchor="w")

    def _build_animation_section(self):
        """Build animation settings section."""
        section = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        section.pack(fill="x", pady=(0, 20))

        # Section title
        ctk.CTkLabel(
            section, text="Animations",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", pady=(0, 12))

        # Animation speed slider
        speed_frame = ctk.CTkFrame(section, fg_color="transparent")
        speed_frame.pack(fill="x", pady=8)

        ctk.CTkLabel(
            speed_frame, text="Animation Speed:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY, fg_color="transparent"
        ).pack(anchor="w", pady=(0, 4))

        self.animation_speed_var = ctk.DoubleVar(value=1.0)
        ctk.CTkSlider(
            speed_frame, from_=0.0, to=2.0, variable=self.animation_speed_var,
            fg_color=BORDER_COLOR, progress_color=ACCENT,
            button_color=ACCENT, button_hover_color=ACCENT
        ).pack(fill="x")

        # Enable ambient animations toggle
        ambient_frame = ctk.CTkFrame(section, fg_color="transparent")
        ambient_frame.pack(fill="x", pady=8)

        self.ambient_animations_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            ambient_frame, text="Enable ambient animations",
            variable=self.ambient_animations_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT,
            border_color=BORDER_COLOR, checkmark_color="white",
            corner_radius=4, width=16, height=16
        ).pack(anchor="w")

    def _build_notifications_section(self):
        """Build notification settings section."""
        section = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        section.pack(fill="x", pady=(0, 20))

        # Section title
        ctk.CTkLabel(
            section, text="Notifications",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", pady=(0, 12))

        # Low stock alerts toggle
        low_stock_frame = ctk.CTkFrame(section, fg_color="transparent")
        low_stock_frame.pack(fill="x", pady=8)

        self.low_stock_alerts_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            low_stock_frame, text="Low stock alerts",
            variable=self.low_stock_alerts_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT,
            border_color=BORDER_COLOR, checkmark_color="white",
            corner_radius=4, width=16, height=16
        ).pack(anchor="w")

        # Client visit notifications toggle
        visit_frame = ctk.CTkFrame(section, fg_color="transparent")
        visit_frame.pack(fill="x", pady=8)

        self.visit_notifications_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            visit_frame, text="Client visit notifications",
            variable=self.visit_notifications_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT,
            border_color=BORDER_COLOR, checkmark_color="white",
            corner_radius=4, width=16, height=16
        ).pack(anchor="w")

    def _on_theme_select(self, theme_name: str):
        """Handle theme selection."""
        # Update card selection
        for name, card in self.theme_cards.items():
            card.set_selected(name == theme_name)

        # Call callback
        if self.on_theme_change:
            self.on_theme_change(theme_name)

    def get_settings(self) -> dict:
        """Get current settings."""
        return {
            "reduce_motion": self.reduce_motion_var.get(),
            "high_contrast": self.high_contrast_var.get(),
            "larger_text": self.larger_text_var.get(),
            "animation_speed": self.animation_speed_var.get(),
            "ambient_animations": self.ambient_animations_var.get(),
            "low_stock_alerts": self.low_stock_alerts_var.get(),
            "visit_notifications": self.visit_notifications_var.get(),
        }
