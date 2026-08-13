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
    "Harvest Hero": {
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
    "Luxury Dark": {
        "ctk_mode": "dark",
        "BG_BASE": "#0C1519", "BG_SURFACE": "#162127",
        "BG_ELEVATED": "#1A262C", "BG_OVERLAY": "#1E2D35", "BG_HOVER": "#243038",
        "BORDER_SUBTLE": "#252A2D", "BORDER_COLOR": "#3A3534", "BORDER_STRONG": "#4A4240",
        "TEXT_PRIMARY": "#F5EFEA", "TEXT_SECONDARY": "#C7B8AD", "TEXT_MUTED": "#8B7D75",
        "ACCENT": "#CF9D7B", "ACCENT_HOVER": "#D8A989",
        "ACCENT_MUTED": "#1F1610", "ACCENT_GOLD": "#CF9D7B",
        "SECONDARY_ACCENT": "#724B39", "SECONDARY_ACCENT_HOVER": "#8A5A46",
        "ACCENT_GREEN": "#4A7C59", "ACCENT_RED": "#8B3A3A",
        "ACCENT_AMBER": "#B87333", "ACCENT_BLUE": "#4A6B8A",
        "GREEN_DIM": "#0C1E12", "RED_DIM": "#1E0C0C", "AMBER_DIM": "#1E1508",
        "swatches": ["#0C1519", "#CF9D7B", "#4A7C59", "#8B3A3A"],
    },
    "Windsurf Dark": {
        "ctk_mode": "dark",
        "BG_BASE": "#0D1117", "BG_SURFACE": "#161B22",
        "BG_ELEVATED": "#1C2128", "BG_OVERLAY": "#22272E", "BG_HOVER": "#2D333B",
        "BORDER_SUBTLE": "#21262D", "BORDER_COLOR": "#30363D", "BORDER_STRONG": "#3D444D",
        "TEXT_PRIMARY": "#E6EDF3", "TEXT_SECONDARY": "#8D96A0", "TEXT_MUTED": "#484F58",
        "ACCENT": "#58A6FF", "ACCENT_HOVER": "#79B8FF",
        "ACCENT_MUTED": "#0A1929", "ACCENT_GOLD": "#F0C040",
        "SECONDARY_ACCENT": "#1F4E8C", "SECONDARY_ACCENT_HOVER": "#2A6AB8",
        "ACCENT_GREEN": "#3FB950", "ACCENT_RED": "#F85149",
        "ACCENT_AMBER": "#D29922", "ACCENT_BLUE": "#58A6FF",
        "GREEN_DIM": "#041D08", "RED_DIM": "#1C0A09", "AMBER_DIM": "#1C1007",
        "swatches": ["#0D1117", "#58A6FF", "#3FB950", "#F85149"],
    },
    "Dracula": {
        "ctk_mode": "dark",
        "BG_BASE": "#191622", "BG_SURFACE": "#22212C",
        "BG_ELEVATED": "#2B2A3B", "BG_OVERLAY": "#343343", "BG_HOVER": "#3C3B4C",
        "BORDER_SUBTLE": "#2E2C3D", "BORDER_COLOR": "#44475A", "BORDER_STRONG": "#565869",
        "TEXT_PRIMARY": "#F8F8F2", "TEXT_SECONDARY": "#BFBFCF", "TEXT_MUTED": "#6272A4",
        "ACCENT": "#BD93F9", "ACCENT_HOVER": "#CDA6FA",
        "ACCENT_MUTED": "#2A1F50", "ACCENT_GOLD": "#FFB86C",
        "SECONDARY_ACCENT": "#6272A4", "SECONDARY_ACCENT_HOVER": "#7282B4",
        "ACCENT_GREEN": "#50FA7B", "ACCENT_RED": "#FF5555",
        "ACCENT_AMBER": "#FFB86C", "ACCENT_BLUE": "#8BE9FD",
        "GREEN_DIM": "#0A2011", "RED_DIM": "#200A0A", "AMBER_DIM": "#201507",
        "swatches": ["#22212C", "#BD93F9", "#50FA7B", "#FF5555"],
    },
    "Nord": {
        "ctk_mode": "dark",
        "BG_BASE": "#2E3440", "BG_SURFACE": "#3B4252",
        "BG_ELEVATED": "#434C5E", "BG_OVERLAY": "#4C566A", "BG_HOVER": "#556070",
        "BORDER_SUBTLE": "#3E4758", "BORDER_COLOR": "#4C566A", "BORDER_STRONG": "#5E6A7D",
        "TEXT_PRIMARY": "#ECEFF4", "TEXT_SECONDARY": "#D8DEE9", "TEXT_MUTED": "#8A99B0",
        "ACCENT": "#88C0D0", "ACCENT_HOVER": "#9ECFDF",
        "ACCENT_MUTED": "#1E3040", "ACCENT_GOLD": "#EBCB8B",
        "SECONDARY_ACCENT": "#5E81AC", "SECONDARY_ACCENT_HOVER": "#7291BC",
        "ACCENT_GREEN": "#A3BE8C", "ACCENT_RED": "#BF616A",
        "ACCENT_AMBER": "#EBCB8B", "ACCENT_BLUE": "#81A1C1",
        "GREEN_DIM": "#1E2D1A", "RED_DIM": "#2D1A1B", "AMBER_DIM": "#2D2818",
        "swatches": ["#2E3440", "#88C0D0", "#A3BE8C", "#BF616A"],
    },
    "Monokai": {
        "ctk_mode": "dark",
        "BG_BASE": "#1A1A1A", "BG_SURFACE": "#272822",
        "BG_ELEVATED": "#2E2E2E", "BG_OVERLAY": "#3A3A3A", "BG_HOVER": "#404040",
        "BORDER_SUBTLE": "#303030", "BORDER_COLOR": "#454545", "BORDER_STRONG": "#555555",
        "TEXT_PRIMARY": "#F8F8F2", "TEXT_SECONDARY": "#CFCFC2", "TEXT_MUTED": "#75715E",
        "ACCENT": "#FD971F", "ACCENT_HOVER": "#FFA840",
        "ACCENT_MUTED": "#2A1A05", "ACCENT_GOLD": "#E6DB74",
        "SECONDARY_ACCENT": "#75715E", "SECONDARY_ACCENT_HOVER": "#90896E",
        "ACCENT_GREEN": "#A6E22E", "ACCENT_RED": "#F92672",
        "ACCENT_AMBER": "#FD971F", "ACCENT_BLUE": "#66D9E8",
        "GREEN_DIM": "#1A2208", "RED_DIM": "#220A0F", "AMBER_DIM": "#221408",
        "swatches": ["#272822", "#FD971F", "#A6E22E", "#F92672"],
    },
    "Light": {
        "ctk_mode": "light",
        "BG_BASE": "#F0F0F0", "BG_SURFACE": "#FFFFFF",
        "BG_ELEVATED": "#F7F7F7", "BG_OVERLAY": "#EDEDED", "BG_HOVER": "#E4E4E4",
        "BORDER_SUBTLE": "#DEDEDE", "BORDER_COLOR": "#CCCCCC", "BORDER_STRONG": "#BBBBBB",
        "TEXT_PRIMARY": "#1A1A1A", "TEXT_SECONDARY": "#444444", "TEXT_MUTED": "#888888",
        "ACCENT": "#0078D4", "ACCENT_HOVER": "#106EBE",
        "ACCENT_MUTED": "#E6F2FA", "ACCENT_GOLD": "#C27B00",
        "SECONDARY_ACCENT": "#0050A0", "SECONDARY_ACCENT_HOVER": "#0060B8",
        "ACCENT_GREEN": "#107C10", "ACCENT_RED": "#C50F1F",
        "ACCENT_AMBER": "#9A6B00", "ACCENT_BLUE": "#0078D4",
        "GREEN_DIM": "#E8F5E8", "RED_DIM": "#FAE8E8", "AMBER_DIM": "#FAF0E0",
        "swatches": ["#FFFFFF", "#0078D4", "#107C10", "#C50F1F"],
    },
    "Solarized Dark": {
        "ctk_mode": "dark",
        "BG_BASE": "#002B36", "BG_SURFACE": "#073642",
        "BG_ELEVATED": "#0A4A58", "BG_OVERLAY": "#0D5865", "BG_HOVER": "#125A68",
        "BORDER_SUBTLE": "#0D4C59", "BORDER_COLOR": "#155A68", "BORDER_STRONG": "#1F6B7A",
        "TEXT_PRIMARY": "#FDF6E3", "TEXT_SECONDARY": "#93A1A1", "TEXT_MUTED": "#586E75",
        "ACCENT": "#268BD2", "ACCENT_HOVER": "#3399E6",
        "ACCENT_MUTED": "#002A35", "ACCENT_GOLD": "#B58900",
        "SECONDARY_ACCENT": "#2AA198", "SECONDARY_ACCENT_HOVER": "#38B3A9",
        "ACCENT_GREEN": "#859900", "ACCENT_RED": "#DC322F",
        "ACCENT_AMBER": "#B58900", "ACCENT_BLUE": "#268BD2",
        "GREEN_DIM": "#1A2E05", "RED_DIM": "#2E0D0C", "AMBER_DIM": "#2E2205",
        "swatches": ["#002B36", "#268BD2", "#859900", "#DC322F"],
    },
    "Gruvbox Dark": {
        "ctk_mode": "dark",
        "BG_BASE": "#1D2021", "BG_SURFACE": "#282828",
        "BG_ELEVATED": "#3C3836", "BG_OVERLAY": "#504945", "BG_HOVER": "#665C54",
        "BORDER_SUBTLE": "#3C3836", "BORDER_COLOR": "#504945", "BORDER_STRONG": "#665C54",
        "TEXT_PRIMARY": "#EBDBB2", "TEXT_SECONDARY": "#D5C4A1", "TEXT_MUTED": "#928374",
        "ACCENT": "#FE8019", "ACCENT_HOVER": "#FEA44C",
        "ACCENT_MUTED": "#3A2412", "ACCENT_GOLD": "#FABD2F",
        "SECONDARY_ACCENT": "#D65D0E", "SECONDARY_ACCENT_HOVER": "#E67318",
        "ACCENT_GREEN": "#B8BB26", "ACCENT_RED": "#FB4934",
        "ACCENT_AMBER": "#FABD2F", "ACCENT_BLUE": "#83A598",
        "GREEN_DIM": "#2B2E0A", "RED_DIM": "#2E0D0C", "AMBER_DIM": "#2E2508",
        "swatches": ["#282828", "#FE8019", "#B8BB26", "#FB4934"],
    },
    "Tokyo Night": {
        "ctk_mode": "dark",
        "BG_BASE": "#1A1B26", "BG_SURFACE": "#24283B",
        "BG_ELEVATED": "#2F3549", "BG_OVERLAY": "#3B4261", "BG_HOVER": "#414868",
        "BORDER_SUBTLE": "#292E42", "BORDER_COLOR": "#3B4261", "BORDER_STRONG": "#545C7E",
        "TEXT_PRIMARY": "#C0CAF5", "TEXT_SECONDARY": "#A9B1D6", "TEXT_MUTED": "#565F89",
        "ACCENT": "#7AA2F7", "ACCENT_HOVER": "#89B4FA",
        "ACCENT_MUTED": "#1F2335", "ACCENT_GOLD": "#E0AF68",
        "SECONDARY_ACCENT": "#BB9AF7", "SECONDARY_ACCENT_HOVER": "#C8A6FF",
        "ACCENT_GREEN": "#9ECE6A", "ACCENT_RED": "#F7768E",
        "ACCENT_AMBER": "#E0AF68", "ACCENT_BLUE": "#7AA2F7",
        "GREEN_DIM": "#1C2B1A", "RED_DIM": "#2B1A1F", "AMBER_DIM": "#2B2318",
        "swatches": ["#1A1B26", "#7AA2F7", "#9ECE6A", "#F7768E"],
    },
    "Catppuccin Mocha": {
        "ctk_mode": "dark",
        "BG_BASE": "#1E1E2E", "BG_SURFACE": "#181825",
        "BG_ELEVATED": "#313244", "BG_OVERLAY": "#45475A", "BG_HOVER": "#585B70",
        "BORDER_SUBTLE": "#313244", "BORDER_COLOR": "#45475A", "BORDER_STRONG": "#585B70",
        "TEXT_PRIMARY": "#CDD6F4", "TEXT_SECONDARY": "#BAC2DE", "TEXT_MUTED": "#6C7086",
        "ACCENT": "#CBA6F7", "ACCENT_HOVER": "#D8B8FA",
        "ACCENT_MUTED": "#241F30", "ACCENT_GOLD": "#F9E2AF",
        "SECONDARY_ACCENT": "#89B4FA", "SECONDARY_ACCENT_HOVER": "#9CC1FB",
        "ACCENT_GREEN": "#A6E3A1", "ACCENT_RED": "#F38BA8",
        "ACCENT_AMBER": "#F9E2AF", "ACCENT_BLUE": "#89B4FA",
        "GREEN_DIM": "#1D2B1C", "RED_DIM": "#2B1C22", "AMBER_DIM": "#2B2718",
        "swatches": ["#1E1E2E", "#CBA6F7", "#A6E3A1", "#F38BA8"],
    },
    "Rosé Pine": {
        "ctk_mode": "dark",
        "BG_BASE": "#191724", "BG_SURFACE": "#1F1D2E",
        "BG_ELEVATED": "#26233A", "BG_OVERLAY": "#2A2837", "BG_HOVER": "#393552",
        "BORDER_SUBTLE": "#26233A", "BORDER_COLOR": "#403D52", "BORDER_STRONG": "#524F67",
        "TEXT_PRIMARY": "#E0DEF4", "TEXT_SECONDARY": "#908CAA", "TEXT_MUTED": "#6E6A86",
        "ACCENT": "#EB6F92", "ACCENT_HOVER": "#F28CA8",
        "ACCENT_MUTED": "#2B1C22", "ACCENT_GOLD": "#F6C177",
        "SECONDARY_ACCENT": "#9CCFD8", "SECONDARY_ACCENT_HOVER": "#B1D9E0",
        "ACCENT_GREEN": "#31748F", "ACCENT_RED": "#EB6F92",
        "ACCENT_AMBER": "#F6C177", "ACCENT_BLUE": "#9CCFD8",
        "GREEN_DIM": "#14262B", "RED_DIM": "#2B1820", "AMBER_DIM": "#2B2418",
        "swatches": ["#191724", "#EB6F92", "#9CCFD8", "#F6C177"],
    },
    "Cyberpunk Neon": {
        "ctk_mode": "dark",
        "BG_BASE": "#0A0E17", "BG_SURFACE": "#10141F",
        "BG_ELEVATED": "#161C2B", "BG_OVERLAY": "#1D2438", "BG_HOVER": "#262E47",
        "BORDER_SUBTLE": "#1A2036", "BORDER_COLOR": "#263050", "BORDER_STRONG": "#354268",
        "TEXT_PRIMARY": "#F2F4FF", "TEXT_SECONDARY": "#9AA3C7", "TEXT_MUTED": "#545E82",
        "ACCENT": "#FF2FB0", "ACCENT_HOVER": "#FF5CC4",
        "ACCENT_MUTED": "#2B0A20", "ACCENT_GOLD": "#00E5FF",
        "SECONDARY_ACCENT": "#7B2FFF", "SECONDARY_ACCENT_HOVER": "#9257FF",
        "ACCENT_GREEN": "#39FF8F", "ACCENT_RED": "#FF3860",
        "ACCENT_AMBER": "#FFD400", "ACCENT_BLUE": "#00E5FF",
        "GREEN_DIM": "#072318", "RED_DIM": "#2B0A12", "AMBER_DIM": "#2B2408",
        "swatches": ["#0A0E17", "#FF2FB0", "#39FF8F", "#00E5FF"],
    },
    "Ocean Blue": {
        "ctk_mode": "dark",
        "BG_BASE": "#0A1A2A", "BG_SURFACE": "#0F2438",
        "BG_ELEVATED": "#163049", "BG_OVERLAY": "#1D3C5C", "BG_HOVER": "#24486E",
        "BORDER_SUBTLE": "#16324A", "BORDER_COLOR": "#21455F", "BORDER_STRONG": "#2E5A78",
        "TEXT_PRIMARY": "#EAF4FF", "TEXT_SECONDARY": "#A9C4DE", "TEXT_MUTED": "#5F7E99",
        "ACCENT": "#2EC4E6", "ACCENT_HOVER": "#52D2EF",
        "ACCENT_MUTED": "#08222F", "ACCENT_GOLD": "#F2C14E",
        "SECONDARY_ACCENT": "#1A6FA8", "SECONDARY_ACCENT_HOVER": "#2483C4",
        "ACCENT_GREEN": "#2FBF8F", "ACCENT_RED": "#E4573D",
        "ACCENT_AMBER": "#F2C14E", "ACCENT_BLUE": "#2EC4E6",
        "GREEN_DIM": "#0A2A20", "RED_DIM": "#2A120D", "AMBER_DIM": "#2A2210",
        "swatches": ["#0A1A2A", "#2EC4E6", "#2FBF8F", "#E4573D"],
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
    "Orchard Bloom": {
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
    """Return the stored theme name, defaulting to 'Harvest Hero'."""
    try:
        with open(_CFG) as f:
            return json.load(f).get("theme", "Harvest Hero")
    except Exception:
        return "Harvest Hero"


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
    return _PRESETS.get(name, _PRESETS["Luxury Dark"]).get("swatches", [])


# ---------------------------------------------------------------------------
# Apply active preset at import time
# ---------------------------------------------------------------------------

_t = _PRESETS.get(get_active_theme_name(), _PRESETS["Harvest Hero"])

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
