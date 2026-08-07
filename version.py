"""version.py — single source of truth for the app version.

Bump this before every release build. The updater compares the value
here (baked into the frozen bundle) with the "version" field in the
remote manifest to decide whether a newer build is available.
"""

__version__ = "1.0.0"

# Default location of the release manifest. Can be overridden per-install
# with the "update_url" key in config.json — useful for staging or for a
# customer who mirrors the file internally.
DEFAULT_MANIFEST_URL = (
    "https://github.com/oclemons/HarvestHero/releases/latest/download/latest.json"
)
