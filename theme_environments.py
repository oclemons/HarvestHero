"""
theme_environments.py — Visual environment definitions for Harvest Hero themes.

Each theme represents a distinct harvest/farming environment with:
- Visual characteristics (background, lighting, mood)
- Animation sets (ambient animations specific to theme)
- Glass effect appearance (reflection colors, depth)
- Decorative elements (crops, clouds, leaves, etc.)
- Overall atmosphere

This module defines the visual identity of each theme beyond just color tokens.
"""

# ============================================================================
# THEME ENVIRONMENT DEFINITIONS
# ============================================================================

THEME_ENVIRONMENTS = {
    "Harvest Day": {
        "name": "Harvest Day",
        "description": "Bright daytime farm with green fields and golden crops",
        "category": "harvest",
        "is_default": True,
        "visual_direction": [
            "Green fields with golden crops",
            "Blue sky with white clouds",
            "Sunlight and warm lighting",
            "Wheat, produce, harvest baskets",
            "Rolling hills",
        ],
        "mood": ["Fresh", "Optimistic", "Welcoming", "Productive"],
        "primary_colors": ["#10B981", "#22C55E"],  # Greens
        "secondary_colors": ["#F59E0B", "#FBBF24"],  # Golds
        "accent_color": "#F0FFF4",  # Warm white
        "shadow_color": "#051A0F",  # Dark green
        "glass_reflection": "#F0FFF4",  # Light green reflection
        "glass_appearance": "bright, naturally reflective, warm sunlight",
        "animations": [
            "slow_clouds_drifting",
            "gentle_crop_sway",
            "subtle_sunlight_shifts",
            "leaf_flutter",
        ],
        "background_style": "farm_landscape_day",
        "lighting": "bright_daylight",
        "time_of_day": "daytime",
    },
    "Autumn Harvest": {
        "name": "Autumn Harvest",
        "description": "Fall farm with pumpkins and orange foliage",
        "category": "harvest",
        "is_default": False,
        "visual_direction": [
            "Pumpkins and gourds",
            "Orange/red foliage",
            "Golden crops ready for harvest",
            "Harvest baskets and crates",
            "Warm sunset lighting",
            "Late-season fields",
        ],
        "mood": ["Warm", "Abundant", "Harvest-focused", "Grateful"],
        "primary_colors": ["#F97316", "#FB923C"],  # Oranges
        "secondary_colors": ["#DC2626", "#EF4444"],  # Reds
        "accent_color": "#F59E0B",  # Gold
        "shadow_color": "#7C2D12",  # Dark brown
        "glass_reflection": "#FEF3C7",  # Warm amber
        "glass_appearance": "warm amber reflections, sunset-tinted glass, rich warm appearance",
        "animations": [
            "falling_leaves",
            "gentle_cloud_movement",
            "warm_light_shifts",
            "subtle_pumpkin_sway",
        ],
        "background_style": "farm_landscape_autumn",
        "lighting": "warm_sunset",
        "time_of_day": "late_afternoon",
    },
    "Orchard Bloom": {
        "name": "Orchard Bloom",
        "description": "Orchard and garden with fruit trees and blossoms",
        "category": "harvest",
        "is_default": False,
        "visual_direction": [
            "Fruit trees (apples, pears, berries)",
            "Blossoms and leaves",
            "Garden rows",
            "Spring/early summer sunlight",
            "Fresh, growing plants",
            "Baskets of fresh fruit",
        ],
        "mood": ["Fresh", "Bright", "Growing", "Natural"],
        "primary_colors": ["#10B981", "#34D399"],  # Fresh greens
        "secondary_colors": ["#EC4899", "#F472B6"],  # Pinks
        "accent_color": "#ECFDF5",  # White
        "shadow_color": "#064E3B",  # Dark green
        "glass_reflection": "#ECFDF5",  # Fresh light
        "glass_appearance": "fresh bright glass, natural light reflections, clear transparent",
        "animations": [
            "floating_leaves",
            "gentle_blossoms",
            "drifting_petals",
            "subtle_daylight_effects",
        ],
        "background_style": "orchard_garden",
        "lighting": "bright_natural",
        "time_of_day": "morning",
    },
    "Moonlit Farm": {
        "name": "Moonlit Farm",
        "description": "Night farm with moonlight and stars (dark theme)",
        "category": "harvest",
        "is_default": False,
        "is_dark_theme": True,
        "visual_direction": [
            "Dark crop rows",
            "Barn silhouette",
            "Moonlight and stars",
            "Lantern-style lighting",
            "Subtle illuminated windows",
            "Night sky with clouds",
        ],
        "mood": ["Calm", "Peaceful", "Professional", "Night-time"],
        "primary_colors": ["#1E3A8A", "#1E40AF"],  # Dark blues
        "secondary_colors": ["#E5E7EB", "#F3F4F6"],  # Cool silvers
        "accent_color": "#F3F4F6",  # Cool white
        "shadow_color": "#0F172A",  # Very dark
        "glass_reflection": "#F3F4F6",  # Cool silver
        "glass_appearance": "dark smoked glass, cool reflections, moonlight highlights, subtle luminescence",
        "animations": [
            "very_slow_cloud_movement",
            "subtle_stars",
            "moonlight_reflection_shifts",
            "gentle_barn_light_flicker",
        ],
        "background_style": "farm_landscape_night",
        "lighting": "moonlight",
        "time_of_day": "night",
        "note": "Clearly feels like the same farm at night, maintaining brand continuity",
    },
    "Cozy Pantry": {
        "name": "Cozy Pantry",
        "description": "Indoor wooden pantry with shelves and baskets",
        "category": "indoor",
        "is_default": False,
        "visual_direction": [
            "Wooden shelves",
            "Produce baskets",
            "Food jars and containers",
            "Wooden crates",
            "Warm indoor lighting",
            "Farm-market styling",
            "Rustic wooden details",
        ],
        "mood": ["Warm", "Welcoming", "Organized", "Community-focused"],
        "primary_colors": ["#92400E", "#B45309"],  # Warm browns
        "secondary_colors": ["#FEF3C7", "#FEF08A"],  # Warm creams
        "accent_color": "#F59E0B",  # Warm gold
        "shadow_color": "#78350F",  # Dark brown
        "glass_reflection": "#FEF3C7",  # Warm cream
        "glass_appearance": "warm indoor reflective surfaces, wooden frame reflections, cozy intimate appearance",
        "animations": [
            "gentle_shelf_highlights",
            "subtle_light_shifts",
            "soft_item_sway",
            "warm_glow_effects",
        ],
        "background_style": "indoor_pantry",
        "lighting": "warm_indoor",
        "time_of_day": "indoor",
    },
    "Farmers Market": {
        "name": "Farmers Market",
        "description": "Community produce market with stalls",
        "category": "community",
        "is_default": False,
        "visual_direction": [
            "Produce stalls",
            "Baskets and crates",
            "Canvas awnings",
            "Market signs",
            "Fresh fruits and vegetables",
            "Community gathering space",
            "Outdoor market setting",
        ],
        "mood": ["Community-focused", "Vibrant", "Fresh", "Welcoming"],
        "primary_colors": ["#16A34A", "#22C55E"],  # Vibrant greens
        "secondary_colors": ["#EA580C", "#F97316"],  # Market oranges
        "accent_color": "#FAFAFA",  # White
        "shadow_color": "#15803D",  # Dark green
        "glass_reflection": "#FFFBEB",  # Soft yellow
        "glass_appearance": "outdoor sunlit glass, clear transparent, natural light reflections",
        "animations": [
            "gentle_awning_sway",
            "subtle_light_shifts",
            "item_arrangement_hints",
            "community_activity_suggestions",
        ],
        "background_style": "farmers_market",
        "lighting": "outdoor_sunlight",
        "time_of_day": "daytime",
    },
    "Garden Morning": {
        "name": "Garden Morning",
        "description": "Garden beds with vegetables and herbs",
        "category": "harvest",
        "is_default": False,
        "visual_direction": [
            "Garden beds with vegetables",
            "Herbs and plants",
            "Greenhouse details",
            "Morning sunlight",
            "Fresh leaves and dew",
            "Growing plants",
            "Natural garden setting",
        ],
        "mood": ["Fresh", "Natural", "Growing", "Hopeful"],
        "primary_colors": ["#059669", "#10B981"],  # Fresh greens
        "secondary_colors": ["#FCD34D", "#FBBF24"],  # Soft yellows
        "accent_color": "#DCFCE7",  # Light green
        "shadow_color": "#065F46",  # Dark green
        "glass_reflection": "#F0FDF4",  # Fresh green
        "glass_appearance": "morning dew-like appearance, fresh clear glass, soft light reflections",
        "animations": [
            "gentle_plant_sway",
            "morning_dew_sparkle",
            "soft_light_shifts",
            "growing_plant_hints",
        ],
        "background_style": "garden_beds",
        "lighting": "morning_sunlight",
        "time_of_day": "early_morning",
    },
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_theme_environment(theme_name: str) -> dict:
    """Get environment definition for a theme.
    
    Args:
        theme_name: Theme name
    
    Returns:
        Theme environment dictionary
    """
    return THEME_ENVIRONMENTS.get(theme_name, THEME_ENVIRONMENTS["Harvest Day"])


def get_all_theme_names() -> list:
    """Get list of all theme names.
    
    Returns:
        List of theme names
    """
    return list(THEME_ENVIRONMENTS.keys())


def get_harvest_themes() -> list:
    """Get list of harvest-focused themes.
    
    Returns:
        List of harvest theme names
    """
    return [
        name for name, env in THEME_ENVIRONMENTS.items()
        if env.get("category") == "harvest"
    ]


def get_default_theme() -> str:
    """Get the default theme name.
    
    Returns:
        Default theme name
    """
    for name, env in THEME_ENVIRONMENTS.items():
        if env.get("is_default"):
            return name
    return "Harvest Day"


def get_theme_mood(theme_name: str) -> list:
    """Get mood descriptors for a theme.
    
    Args:
        theme_name: Theme name
    
    Returns:
        List of mood descriptors
    """
    env = get_theme_environment(theme_name)
    return env.get("mood", [])


def get_theme_animations(theme_name: str) -> list:
    """Get animation set for a theme.
    
    Args:
        theme_name: Theme name
    
    Returns:
        List of animation names
    """
    env = get_theme_environment(theme_name)
    return env.get("animations", [])


def get_glass_reflection_color(theme_name: str) -> str:
    """Get glass reflection color for a theme.
    
    Args:
        theme_name: Theme name
    
    Returns:
        Hex color for glass reflection
    """
    env = get_theme_environment(theme_name)
    return env.get("glass_reflection", "#FFFFFF")


def get_theme_description(theme_name: str) -> str:
    """Get description of a theme.
    
    Args:
        theme_name: Theme name
    
    Returns:
        Theme description
    """
    env = get_theme_environment(theme_name)
    return env.get("description", "")


def is_dark_theme(theme_name: str) -> bool:
    """Check if a theme is a dark theme.
    
    Args:
        theme_name: Theme name
    
    Returns:
        True if theme is dark
    """
    env = get_theme_environment(theme_name)
    return env.get("is_dark_theme", False)


def get_theme_lighting(theme_name: str) -> str:
    """Get lighting characteristic of a theme.
    
    Args:
        theme_name: Theme name
    
    Returns:
        Lighting description
    """
    env = get_theme_environment(theme_name)
    return env.get("lighting", "")


def get_theme_time_of_day(theme_name: str) -> str:
    """Get time of day for a theme.
    
    Args:
        theme_name: Theme name
    
    Returns:
        Time of day
    """
    env = get_theme_environment(theme_name)
    return env.get("time_of_day", "")
