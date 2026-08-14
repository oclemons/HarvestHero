"""
theme.py — Multi-theme design tokens for Harvest Hero.
Active theme is read from config.json at import time; restart to apply changes.
"""

import json
import os

from paths import USER_DIR

_CFG  = os.path.join(USER_DIR, "config.json")

# ---------------------------------------------------------------------------
# Theme presets
# ---------------------------------------------------------------------------

_PRESETS: dict = {
    "Harvest Green": {
        "ctk_mode": "dark",
        "BG_BASE": "#0B1510", "BG_SURFACE": "#111E16",
        "BG_ELEVATED": "#162A1D", "BG_OVERLAY": "#1A3022", "BG_HOVER": "#1F3828",
        "BORDER_SUBTLE": "#1D2E22", "BORDER_COLOR": "#2A4233", "BORDER_STRONG": "#3A5443",
        "TEXT_PRIMARY": "#F0FFF4", "TEXT_SECONDARY": "#A7C4B0", "TEXT_MUTED": "#5A7A64",
        "ACCENT": "#10B981", "ACCENT_HOVER": "#34D399",
        "ACCENT_MUTED": "#051A0F", "ACCENT_GOLD": "#F59E0B",
        "SECONDARY_ACCENT": "#065F46", "SECONDARY_ACCENT_HOVER": "#047857",
        "ACCENT_GREEN": "#22C55E", "ACCENT_RED": "#EF4444",
        "ACCENT_AMBER": "#F59E0B", "ACCENT_BLUE": "#3B82F6",
        "GREEN_DIM": "#052E16", "RED_DIM": "#1C0606", "AMBER_DIM": "#1C1205",
        "swatches": ["#0B1510", "#10B981", "#F59E0B", "#EF4444"],
    },
    "Golden Wheat": {
        "ctk_mode": "dark",
        "BG_BASE": "#0F0D08", "BG_SURFACE": "#1A1610",
        "BG_ELEVATED": "#2A2018", "BG_OVERLAY": "#3A3020", "BG_HOVER": "#4A4028",
        "BORDER_SUBTLE": "#2A2018", "BORDER_COLOR": "#4A4028", "BORDER_STRONG": "#5A5038",
        "TEXT_PRIMARY": "#F5F0E8", "TEXT_SECONDARY": "#D4C4A8", "TEXT_MUTED": "#A89880",
        "ACCENT": "#D4A574", "ACCENT_HOVER": "#E0B588",
        "ACCENT_MUTED": "#3A2410", "ACCENT_GOLD": "#E6C200",
        "SECONDARY_ACCENT": "#8B7355", "SECONDARY_ACCENT_HOVER": "#9B8365",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#D9534F",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B9BD5",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0F0D08", "#D4A574", "#7CB342", "#E6C200"],
    },
    "Pumpkin Patch": {
        "ctk_mode": "dark",
        "BG_BASE": "#1A0F08", "BG_SURFACE": "#2A1810",
        "BG_ELEVATED": "#3A2818", "BG_OVERLAY": "#4A3820", "BG_HOVER": "#5A4828",
        "BORDER_SUBTLE": "#3A2818", "BORDER_COLOR": "#5A4828", "BORDER_STRONG": "#6A5838",
        "TEXT_PRIMARY": "#F5E8D8", "TEXT_SECONDARY": "#D4B8A0", "TEXT_MUTED": "#A89080",
        "ACCENT": "#E67E22", "ACCENT_HOVER": "#F39C12",
        "ACCENT_MUTED": "#4A2410", "ACCENT_GOLD": "#F5A623",
        "SECONDARY_ACCENT": "#8B6F47", "SECONDARY_ACCENT_HOVER": "#9B7F57",
        "ACCENT_GREEN": "#6B8E23", "ACCENT_RED": "#C9302C",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B7A8F",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#1A0F08", "#E67E22", "#6B8E23", "#F5A623"],
    },
    "Orchard Green": {
        "ctk_mode": "dark",
        "BG_BASE": "#0F1A12", "BG_SURFACE": "#142018",
        "BG_ELEVATED": "#1A2B22", "BG_OVERLAY": "#1F3428", "BG_HOVER": "#24402E",
        "BORDER_SUBTLE": "#1D3025", "BORDER_COLOR": "#2A4535", "BORDER_STRONG": "#365A45",
        "TEXT_PRIMARY": "#E8F5E8", "TEXT_SECONDARY": "#A8D4A8", "TEXT_MUTED": "#6B9A6B",
        "ACCENT": "#4CAF50", "ACCENT_HOVER": "#66BB6A",
        "ACCENT_MUTED": "#0D2D0D", "ACCENT_GOLD": "#FFC107",
        "SECONDARY_ACCENT": "#2E7D32", "SECONDARY_ACCENT_HOVER": "#388E3C",
        "ACCENT_GREEN": "#81C784", "ACCENT_RED": "#E57373",
        "ACCENT_AMBER": "#FFB74D", "ACCENT_BLUE": "#64B5F6",
        "GREEN_DIM": "#0D2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0F1A12", "#4CAF50", "#FFC107", "#E57373"],
    },
    "Berry Farm": {
        "ctk_mode": "dark",
        "BG_BASE": "#1A0F18", "BG_SURFACE": "#241820",
        "BG_ELEVATED": "#2E2228", "BG_OVERLAY": "#382C36", "BG_HOVER": "#423640",
        "BORDER_SUBTLE": "#2E2228", "BORDER_COLOR": "#423640", "BORDER_STRONG": "#4C4050",
        "TEXT_PRIMARY": "#F0E8F0", "TEXT_SECONDARY": "#C8B8C8", "TEXT_MUTED": "#9A8A9A",
        "ACCENT": "#9C27B0", "ACCENT_HOVER": "#AB47BC",
        "ACCENT_MUTED": "#3A1A3A", "ACCENT_GOLD": "#E6C200",
        "SECONDARY_ACCENT": "#6A4C8A", "SECONDARY_ACCENT_HOVER": "#7A5C9A",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#E91E63",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B9BD5",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D1A", "AMBER_DIM": "#2D2008",
        "swatches": ["#1A0F18", "#9C27B0", "#7CB342", "#E91E63"],
    },
    "Blue Meadow": {
        "ctk_mode": "dark",
        "BG_BASE": "#0A1520", "BG_SURFACE": "#0F1F2E",
        "BG_ELEVATED": "#152A3A", "BG_OVERLAY": "#1A3548", "BG_HOVER": "#1F4056",
        "BORDER_SUBTLE": "#152A3A", "BORDER_COLOR": "#1F4056", "BORDER_STRONG": "#2A5070",
        "TEXT_PRIMARY": "#E0EEF8", "TEXT_SECONDARY": "#A8C8D8", "TEXT_MUTED": "#6A8A9A",
        "ACCENT": "#4A9FD8", "ACCENT_HOVER": "#6AAFDB",
        "ACCENT_MUTED": "#0A2540", "ACCENT_GOLD": "#D4AF37",
        "SECONDARY_ACCENT": "#2E5A7A", "SECONDARY_ACCENT_HOVER": "#3A6A8A",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#D9534F",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#4A9FD8",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0A1520", "#4A9FD8", "#7CB342", "#D4AF37"],
    },
    "Autumn Harvest": {
        "ctk_mode": "light",
        "BG_BASE": "#FBF3E7", "BG_SURFACE": "#FFFFFF",
        "BG_ELEVATED": "#FBF0DF", "BG_OVERLAY": "#F5E6CC", "BG_HOVER": "#EFDBB8",
        "BORDER_SUBTLE": "#EEDCC0", "BORDER_COLOR": "#DFC49B", "BORDER_STRONG": "#C9A876",
        "TEXT_PRIMARY": "#3A2A18", "TEXT_SECONDARY": "#6B5236", "TEXT_MUTED": "#9A8362",
        "ACCENT": "#C6621B", "ACCENT_HOVER": "#DE7530",
        "ACCENT_MUTED": "#FBE4CC", "ACCENT_GOLD": "#B8860B",
        "SECONDARY_ACCENT": "#7A8B4A", "SECONDARY_ACCENT_HOVER": "#8FA05C",
        "ACCENT_GREEN": "#6E8B3D", "ACCENT_RED": "#B23A2E",
        "ACCENT_AMBER": "#B8860B", "ACCENT_BLUE": "#4A7A96",
        "GREEN_DIM": "#EAF0DC", "RED_DIM": "#F7E2DE", "AMBER_DIM": "#F6EAD2",
        "swatches": ["#FFFFFF", "#C6621B", "#6E8B3D", "#B23A2E"],
    },
    "Apple Orchard": {
        "ctk_mode": "dark",
        "BG_BASE": "#0F0A08", "BG_SURFACE": "#1A1410",
        "BG_ELEVATED": "#2A2018", "BG_OVERLAY": "#3A3028", "BG_HOVER": "#4A4038",
        "BORDER_SUBTLE": "#2A2018", "BORDER_COLOR": "#4A4038", "BORDER_STRONG": "#5A5048",
        "TEXT_PRIMARY": "#F5E8D8", "TEXT_SECONDARY": "#D4B8A0", "TEXT_MUTED": "#A89080",
        "ACCENT": "#C9302C", "ACCENT_HOVER": "#E74C3C",
        "ACCENT_MUTED": "#4A1810", "ACCENT_GOLD": "#E6C200",
        "SECONDARY_ACCENT": "#8B5A3C", "SECONDARY_ACCENT_HOVER": "#9B6A4C",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#C9302C",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B9BD5",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0F0A08", "#C9302C", "#7CB342", "#E6C200"],
    },
    "Vineyard": {
        "ctk_mode": "dark",
        "BG_BASE": "#1A0F15", "BG_SURFACE": "#251820",
        "BG_ELEVATED": "#2F2228", "BG_OVERLAY": "#3A2C38", "BG_HOVER": "#453640",
        "BORDER_SUBTLE": "#2F2228", "BORDER_COLOR": "#453640", "BORDER_STRONG": "#5A4650",
        "TEXT_PRIMARY": "#F0E8F0", "TEXT_SECONDARY": "#D4B8C8", "TEXT_MUTED": "#A89AA8",
        "ACCENT": "#8B4789", "ACCENT_HOVER": "#A85BA3",
        "ACCENT_MUTED": "#3A1A30", "ACCENT_GOLD": "#D4AF37",
        "SECONDARY_ACCENT": "#6B4C7A", "SECONDARY_ACCENT_HOVER": "#7B5C8A",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#C9302C",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B9BD5",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#1A0F15", "#8B4789", "#7CB342", "#D4AF37"],
    },
    "Corn Field": {
        "ctk_mode": "dark",
        "BG_BASE": "#0F0D08", "BG_SURFACE": "#1A1610",
        "BG_ELEVATED": "#2A2018", "BG_OVERLAY": "#3A3020", "BG_HOVER": "#4A4028",
        "BORDER_SUBTLE": "#2A2018", "BORDER_COLOR": "#4A4028", "BORDER_STRONG": "#5A5038",
        "TEXT_PRIMARY": "#F5F0E8", "TEXT_SECONDARY": "#D4C4A8", "TEXT_MUTED": "#A89880",
        "ACCENT": "#F5A623", "ACCENT_HOVER": "#F5B844",
        "ACCENT_MUTED": "#4A3410", "ACCENT_GOLD": "#E6C200",
        "SECONDARY_ACCENT": "#8B7A4A", "SECONDARY_ACCENT_HOVER": "#9B8A5A",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#D9534F",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B9BD5",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0F0D08", "#F5A623", "#7CB342", "#E6C200"],
    },
    "Sunflower": {
        "ctk_mode": "dark",
        "BG_BASE": "#0F0D08", "BG_SURFACE": "#1A1610",
        "BG_ELEVATED": "#2A2018", "BG_OVERLAY": "#3A3020", "BG_HOVER": "#4A4028",
        "BORDER_SUBTLE": "#2A2018", "BORDER_COLOR": "#4A4028", "BORDER_STRONG": "#5A5038",
        "TEXT_PRIMARY": "#F5F0E8", "TEXT_SECONDARY": "#D4C4A8", "TEXT_MUTED": "#A89880",
        "ACCENT": "#FFD700", "ACCENT_HOVER": "#FFE44D",
        "ACCENT_MUTED": "#4A3A10", "ACCENT_GOLD": "#FFD700",
        "SECONDARY_ACCENT": "#8B7A4A", "SECONDARY_ACCENT_HOVER": "#9B8A5A",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#D9534F",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B9BD5",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0F0D08", "#FFD700", "#7CB342", "#D4AF37"],
    },
    "Herb Garden": {
        "ctk_mode": "dark",
        "BG_BASE": "#0A1510", "BG_SURFACE": "#0F1E18",
        "BG_ELEVATED": "#152A20", "BG_OVERLAY": "#1A3528", "BG_HOVER": "#1F4030",
        "BORDER_SUBTLE": "#152A20", "BORDER_COLOR": "#1F4030", "BORDER_STRONG": "#2A5040",
        "TEXT_PRIMARY": "#E0F0E8", "TEXT_SECONDARY": "#A8D4A8", "TEXT_MUTED": "#6B9A6B",
        "ACCENT": "#5CB85C", "ACCENT_HOVER": "#7AC97A",
        "ACCENT_MUTED": "#0D2D0D", "ACCENT_GOLD": "#D4AF37",
        "SECONDARY_ACCENT": "#2E7D32", "SECONDARY_ACCENT_HOVER": "#388E3C",
        "ACCENT_GREEN": "#81C784", "ACCENT_RED": "#E57373",
        "ACCENT_AMBER": "#FFB74D", "ACCENT_BLUE": "#64B5F6",
        "GREEN_DIM": "#0D2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0A1510", "#5CB85C", "#D4AF37", "#E57373"],
    },
    "Root Cellar": {
        "ctk_mode": "dark",
        "BG_BASE": "#0F0A08", "BG_SURFACE": "#1A1410",
        "BG_ELEVATED": "#2A2018", "BG_OVERLAY": "#3A3028", "BG_HOVER": "#4A4038",
        "BORDER_SUBTLE": "#2A2018", "BORDER_COLOR": "#4A4038", "BORDER_STRONG": "#5A5048",
        "TEXT_PRIMARY": "#E8D4C0", "TEXT_SECONDARY": "#C4A890", "TEXT_MUTED": "#9A7860",
        "ACCENT": "#A0522D", "ACCENT_HOVER": "#B8704F",
        "ACCENT_MUTED": "#3A1810", "ACCENT_GOLD": "#D4AF37",
        "SECONDARY_ACCENT": "#6B5A47", "SECONDARY_ACCENT_HOVER": "#7B6A57",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#D9534F",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B9BD5",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0F0A08", "#A0522D", "#7CB342", "#D4AF37"],
    },
    "Moonlit Farm": {
        "ctk_mode": "dark",
        "BG_BASE": "#0A0D15", "BG_SURFACE": "#0F1420",
        "BG_ELEVATED": "#151D2B", "BG_OVERLAY": "#1A2535", "BG_HOVER": "#1F2E40",
        "BORDER_SUBTLE": "#1A2535", "BORDER_COLOR": "#253A50", "BORDER_STRONG": "#304A60",
        "TEXT_PRIMARY": "#D4E4F0", "TEXT_SECONDARY": "#8FA8B8", "TEXT_MUTED": "#5A7A8A",
        "ACCENT": "#4A9FD8", "ACCENT_HOVER": "#6AAFDB",
        "ACCENT_MUTED": "#0A1F35", "ACCENT_GOLD": "#D4AF37",
        "SECONDARY_ACCENT": "#2E5A7A", "SECONDARY_ACCENT_HOVER": "#3A6A8A",
        "ACCENT_GREEN": "#5CB85C", "ACCENT_RED": "#D9534F",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#4A9FD8",
        "GREEN_DIM": "#0D2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#0A0D15", "#4A9FD8", "#D4AF37", "#5CB85C"],
    },
    "Cozy Pantry": {
        "ctk_mode": "dark",
        "BG_BASE": "#1A1410", "BG_SURFACE": "#2A1F18",
        "BG_ELEVATED": "#3A2F28", "BG_OVERLAY": "#4A3F38", "BG_HOVER": "#5A4F48",
        "BORDER_SUBTLE": "#3A2F28", "BORDER_COLOR": "#5A4F48", "BORDER_STRONG": "#6A5F58",
        "TEXT_PRIMARY": "#F5E6D3", "TEXT_SECONDARY": "#D4B8A0", "TEXT_MUTED": "#A89080",
        "ACCENT": "#C67C4E", "ACCENT_HOVER": "#D89060",
        "ACCENT_MUTED": "#3A1F10", "ACCENT_GOLD": "#D4A574",
        "SECONDARY_ACCENT": "#8B6F47", "SECONDARY_ACCENT_HOVER": "#9B7F57",
        "ACCENT_GREEN": "#7CB342", "ACCENT_RED": "#D9534F",
        "ACCENT_AMBER": "#F0AD4E", "ACCENT_BLUE": "#5B9BD5",
        "GREEN_DIM": "#1A2D0D", "RED_DIM": "#2D0D0D", "AMBER_DIM": "#2D2008",
        "swatches": ["#1A1410", "#C67C4E", "#7CB342", "#D9534F"],
    },
}


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def get_active_theme_name() -> str:
    """Return the stored theme name, defaulting to 'Harvest Green'."""
    try:
        with open(_CFG) as f:
            return json.load(f).get("theme", "Harvest Green")
    except Exception:
        return "Harvest Green"


def set_theme_name(name: str) -> None:
    """Persist the chosen theme name to config.json."""
    try:
        cfg: dict = {}
        if os.path.exists(_CFG):
            with open(_CFG) as f:
                cfg = json.load(f)
        cfg["theme"] = name
        with open(_CFG, "w") as f:
            json.dump(cfg, f, indent=2)
        try:
            os.chmod(_CFG, 0o600)
        except OSError:
            pass
    except Exception:
        pass


def get_preset_names() -> list:
    return list(_PRESETS.keys())


def get_preset_swatches(name: str) -> list:
    return _PRESETS.get(name, _PRESETS["Harvest Green"]).get("swatches", [])


# ---------------------------------------------------------------------------
# Apply active preset at import time
# ---------------------------------------------------------------------------

_t = _PRESETS.get(get_active_theme_name(), _PRESETS["Harvest Green"])

BG_BASE      = _t["BG_BASE"]
BG_SURFACE   = _t["BG_SURFACE"]
BG_ELEVATED  = _t["BG_ELEVATED"]
BG_OVERLAY   = _t["BG_OVERLAY"]
BG_HOVER     = _t["BG_HOVER"]

BG_PRIMARY   = BG_SURFACE
BG_SECONDARY = BG_BASE
BG_CARD      = BG_ELEVATED

BORDER_SUBTLE = _t["BORDER_SUBTLE"]
BORDER_COLOR  = _t["BORDER_COLOR"]
BORDER_STRONG = _t["BORDER_STRONG"]

TEXT_PRIMARY   = _t["TEXT_PRIMARY"]
TEXT_SECONDARY = _t["TEXT_SECONDARY"]
TEXT_MUTED     = _t["TEXT_MUTED"]

ACCENT                 = _t["ACCENT"]
ACCENT_HOVER           = _t["ACCENT_HOVER"]
ACCENT_MUTED           = _t["ACCENT_MUTED"]
ACCENT_GOLD            = _t["ACCENT_GOLD"]
SECONDARY_ACCENT       = _t["SECONDARY_ACCENT"]
SECONDARY_ACCENT_HOVER = _t["SECONDARY_ACCENT_HOVER"]

ACCENT_GREEN  = _t["ACCENT_GREEN"]
ACCENT_RED    = _t["ACCENT_RED"]
ACCENT_AMBER  = _t["ACCENT_AMBER"]
ACCENT_BLUE   = _t["ACCENT_BLUE"]

GREEN_DIM  = _t["GREEN_DIM"]
RED_DIM    = _t["RED_DIM"]
AMBER_DIM  = _t["AMBER_DIM"]

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

FONT_FAMILY = "Segoe UI"


def font(size: int = 12, weight: str = "normal") -> tuple:
    return (FONT_FAMILY, size, weight)


FONT_TITLE   = (FONT_FAMILY, 24, "bold")
FONT_HEADING = (FONT_FAMILY, 16, "bold")
FONT_SUBHEAD = (FONT_FAMILY, 13, "bold")
FONT_BODY    = (FONT_FAMILY, 12, "normal")
FONT_SMALL   = (FONT_FAMILY, 10, "normal")
FONT_MONO    = ("Consolas",  12, "normal")

# ---------------------------------------------------------------------------
# Spacing & shape
# ---------------------------------------------------------------------------

PAD_SM    = 8
PAD_MD    = 16
PAD_LG    = 24
PAD_XL    = 36
RADIUS    = 12
RADIUS_SM = 8
SIDEBAR_W = 228

# ---------------------------------------------------------------------------
# Mirror/Glass effect tokens
# ---------------------------------------------------------------------------

# Glass effect opacity (0.0 to 1.0)
GLASS_OPACITY = 0.1  # Subtle glass effect

# Reflection colors (theme-aware)
REFLECTION_LIGHT = f"rgba(255, 255, 255, 0.08)"  # Light reflection
REFLECTION_DARK = f"rgba(0, 0, 0, 0.15)"  # Dark reflection

# Backdrop blur (CSS filter value)
BACKDROP_BLUR = "blur(10px)"

# Shadow for glass effect
GLASS_SHADOW = f"0 8px 32px 0 rgba(0, 0, 0, 0.2)"

# ---------------------------------------------------------------------------
# Status badge dict   { key: (bg, fg) }
# ---------------------------------------------------------------------------

BADGE = {
    "READY":          (ACCENT_MUTED,  ACCENT),
    "SUCCESS":        (GREEN_DIM,     ACCENT_GREEN),
    "LOW STOCK":      (AMBER_DIM,     ACCENT_AMBER),
    "OUT OF STOCK":   (RED_DIM,       ACCENT_RED),
    "ERROR":          (RED_DIM,       ACCENT_RED),
    "ITEM NOT FOUND": (RED_DIM,       ACCENT_RED),
    "CONNECTED":      (GREEN_DIM,     ACCENT_GREEN),
    "DISCONNECTED":   (BORDER_COLOR,  TEXT_MUTED),
    "PROCESSING":     (AMBER_DIM,     ACCENT_AMBER),
}

# ---------------------------------------------------------------------------
# Bootstrap CustomTkinter appearance
# ---------------------------------------------------------------------------

def apply_theme():
    """Call once at startup before creating any CTk widgets."""
    import customtkinter as ctk
    ctk.set_appearance_mode(_t.get("ctk_mode", "dark"))
    ctk.set_default_color_theme("blue")
