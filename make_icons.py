#!/usr/bin/env python3
"""
make_icons.py — Generate icon.icns (Mac) and icon.ico (Windows)
from assets/HarvestHeroIcon.png.

Run once before packaging with PyInstaller:
    python make_icons.py
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile

SRC  = os.path.join(os.path.dirname(__file__), "assets", "HarvestHeroIcon.png")
ICO  = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
ICNS = os.path.join(os.path.dirname(__file__), "assets", "icon.icns")

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required — run:  pip install Pillow")

if not os.path.exists(SRC):
    sys.exit(f"Source image not found: {SRC}")

print(f"[make_icons] Reading {SRC} ...")
base = Image.open(SRC).convert("RGBA")

# ── Windows .ico ────────────────────────────────────────────────────────────
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
frames = [base.resize((s, s), Image.LANCZOS) for s in ICO_SIZES]
frames[0].save(
    ICO, format="ICO",
    sizes=[(s, s) for s in ICO_SIZES],
    append_images=frames[1:],
)
print(f"[make_icons] Saved {ICO}")

# ── macOS .icns ─────────────────────────────────────────────────────────────
if platform.system() == "Darwin":
    iconset = tempfile.mkdtemp(suffix=".iconset")
    try:
        for size in [16, 32, 64, 128, 256, 512]:
            base.resize((size, size),    Image.LANCZOS).save(
                os.path.join(iconset, f"icon_{size}x{size}.png"))
            base.resize((size * 2, size * 2), Image.LANCZOS).save(
                os.path.join(iconset, f"icon_{size}x{size}@2x.png"))
        subprocess.run(
            ["iconutil", "-c", "icns", iconset, "-o", ICNS],
            check=True,
        )
        print(f"[make_icons] Saved {ICNS}")
    finally:
        shutil.rmtree(iconset, ignore_errors=True)
else:
    fallback = ICNS.replace(".icns", "_512.png")
    base.resize((512, 512), Image.LANCZOS).save(fallback)
    print(f"[make_icons] Note: .icns requires macOS (iconutil). Saved 512px PNG instead: {fallback}")

print()
icon_flag = f"assets/icon.icns" if platform.system() == "Darwin" else "assets/icon.ico"
BUILD_CMD = [
    sys.executable, "-m", "PyInstaller",
    "--onefile", "--windowed",
    f"--icon={icon_flag}",
    "--name", "HarvestHero",
    "--collect-data", "customtkinter",
    "--add-data", f"assets{os.pathsep}assets",
    "main.py",
]

answer = input("Build the HarvestHero executable now? [Y/n]: ").strip().lower()
if answer in ("", "y", "yes"):
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[make_icons] PyInstaller not found — installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    print(f"\n[make_icons] Running PyInstaller...")
    subprocess.run(BUILD_CMD, check=True)
    dist = os.path.join(os.path.dirname(__file__), "dist")
    print(f"\n✓ Build complete!  Find your executable in:  {dist}/")
    print("  Share the entire dist/HarvestHero/ folder with end users.")
else:
    print()
    print("When ready to build, run:")
    print("  " + " ".join(BUILD_CMD[2:]))
