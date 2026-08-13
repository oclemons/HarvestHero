"""
accessibility.py — Accessibility settings and utilities for Harvest Hero.

Provides support for:
- prefers-reduced-motion detection
- Accessibility settings management
- Reduced motion animations
- High contrast mode
- Keyboard navigation
"""

import os
import json
from typing import Dict, Any, Optional
from paths import USER_DIR

_ACCESSIBILITY_CONFIG = os.path.join(USER_DIR, "accessibility.json")


class AccessibilitySettings:
    """Manage accessibility preferences for Harvest Hero."""

    def __init__(self):
        """Initialize accessibility settings."""
        self.reduce_motion = self._detect_system_preference()
        self.high_contrast = False
        self.keyboard_nav_enabled = True
        self._load_settings()

    def _detect_system_preference(self) -> bool:
        """Detect if the system prefers reduced motion.
        
        Returns:
            True if system prefers reduced motion
        """
        # Check macOS
        if os.name == "posix":
            try:
                import subprocess
                result = subprocess.run(
                    ["defaults", "read", "-g", "com.apple.universalaccess", "reduceMotionEnabled"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                return result.returncode == 0 and "1" in result.stdout
            except Exception:
                pass
        
        # Check Windows
        if os.name == "nt":
            try:
                import subprocess
                result = subprocess.run(
                    ["reg", "query", "HKCU\\Control Panel\\Accessibility\\Display", "/v", "DisableAnimations"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                return result.returncode == 0 and "0x1" in result.stdout
            except Exception:
                pass
        
        return False

    def _load_settings(self) -> None:
        """Load accessibility settings from file."""
        if not os.path.exists(_ACCESSIBILITY_CONFIG):
            return
        
        try:
            with open(_ACCESSIBILITY_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.reduce_motion = data.get("reduce_motion", self.reduce_motion)
                self.high_contrast = data.get("high_contrast", False)
                self.keyboard_nav_enabled = data.get("keyboard_nav_enabled", True)
        except Exception:
            pass

    def save_settings(self) -> None:
        """Save accessibility settings to file."""
        try:
            data = {
                "reduce_motion": self.reduce_motion,
                "high_contrast": self.high_contrast,
                "keyboard_nav_enabled": self.keyboard_nav_enabled,
            }
            with open(_ACCESSIBILITY_CONFIG, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def set_reduce_motion(self, enabled: bool) -> None:
        """Set reduce motion preference.
        
        Args:
            enabled: Whether to reduce motion
        """
        self.reduce_motion = enabled
        self.save_settings()

    def set_high_contrast(self, enabled: bool) -> None:
        """Set high contrast preference.
        
        Args:
            enabled: Whether to enable high contrast
        """
        self.high_contrast = enabled
        self.save_settings()

    def set_keyboard_nav(self, enabled: bool) -> None:
        """Set keyboard navigation preference.
        
        Args:
            enabled: Whether to enable keyboard navigation
        """
        self.keyboard_nav_enabled = enabled
        self.save_settings()

    def get_animation_duration(self, default_ms: int = 200) -> int:
        """Get appropriate animation duration based on preferences.
        
        Args:
            default_ms: Default duration in milliseconds
        
        Returns:
            Animation duration (0 if reduce_motion enabled)
        """
        return 0 if self.reduce_motion else default_ms

    def should_animate(self) -> bool:
        """Check if animations should be enabled.
        
        Returns:
            True if animations should be shown
        """
        return not self.reduce_motion


# Global accessibility settings instance
_settings: Optional[AccessibilitySettings] = None


def get_accessibility_settings() -> AccessibilitySettings:
    """Get the global accessibility settings instance.
    
    Returns:
        AccessibilitySettings instance
    """
    global _settings
    if _settings is None:
        _settings = AccessibilitySettings()
    return _settings


def should_reduce_motion() -> bool:
    """Check if motion should be reduced.
    
    Returns:
        True if motion should be reduced
    """
    return get_accessibility_settings().reduce_motion


def should_use_high_contrast() -> bool:
    """Check if high contrast should be used.
    
    Returns:
        True if high contrast should be used
    """
    return get_accessibility_settings().high_contrast


def is_keyboard_nav_enabled() -> bool:
    """Check if keyboard navigation is enabled.
    
    Returns:
        True if keyboard navigation is enabled
    """
    return get_accessibility_settings().keyboard_nav_enabled


def get_animation_duration(default_ms: int = 200) -> int:
    """Get animation duration based on accessibility settings.
    
    Args:
        default_ms: Default duration in milliseconds
    
    Returns:
        Animation duration (0 if reduce_motion enabled)
    """
    return get_accessibility_settings().get_animation_duration(default_ms)
