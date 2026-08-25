# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Harvest Hero.

Produces a onedir Windows build (dist/HarvestHero/) that Inno Setup then
packages into a single installer .exe. Onedir is preferred over onefile
for installer distribution because:
  * faster launch (no per-launch temp unpack)
  * fewer antivirus false positives
  * easier to codesign the exe itself
"""

import json
import os
import sys

from PyInstaller.utils.hooks import collect_data_files

# ── Version metadata ───────────────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(SPEC))
with open(os.path.join(_here, "VERSION.json")) as _vf:
    _VERSION = json.load(_vf)["version"]

# Windows expects a 4-part "file version" tuple. Pad the semantic version
# with a trailing zero (2.1.0 -> 2.1.0.0). Non-numeric suffixes are stripped.
_parts = [int("".join(c for c in p if c.isdigit()) or "0")
          for p in _VERSION.split(".")]
while len(_parts) < 4:
    _parts.append(0)
_FILE_VERSION_TUPLE = tuple(_parts[:4])
_FILE_VERSION_STR = ".".join(str(p) for p in _FILE_VERSION_TUPLE)

# ── Data files bundled into the frozen build ───────────────────────────────
# assets/ ships images and icons; VERSION.json is read at runtime by the
# update manager to know what version the installed copy claims to be.
datas = [
    ("assets", "assets"),
    ("VERSION.json", "."),
    ("update_config.json", "."),
]
datas += collect_data_files("customtkinter")

# ── Analysis ───────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # customtkinter has some lazy imports the analyzer can miss.
        "customtkinter",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # pyobjc pulls macOS-only frameworks that will fail to import on
        # Windows; exclude explicitly so PyInstaller doesn't try to bundle
        # a broken stub.
        "pyobjc_framework_Cocoa",
        "PyObjCTools",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# ── Windows VERSIONINFO resource ───────────────────────────────────────────
# Written to build/HarvestHero/file_version_info.txt so Windows Explorer
# right-click -> Properties -> Details shows real version metadata.
_VER_INFO_TXT = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={_FILE_VERSION_TUPLE},
    prodvers={_FILE_VERSION_TUPLE},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [
          StringStruct(u'CompanyName', u'Harvest Hero'),
          StringStruct(u'FileDescription', u'Harvest Hero Inventory Tracker'),
          StringStruct(u'FileVersion', u'{_FILE_VERSION_STR}'),
          StringStruct(u'InternalName', u'HarvestHero'),
          StringStruct(u'OriginalFilename', u'HarvestHero.exe'),
          StringStruct(u'ProductName', u'Harvest Hero'),
          StringStruct(u'ProductVersion', u'{_FILE_VERSION_STR}'),
        ])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
""".strip()

_ver_info_path = os.path.join(_here, "build", "file_version_info.txt")
os.makedirs(os.path.dirname(_ver_info_path), exist_ok=True)
with open(_ver_info_path, "w", encoding="utf-8") as _f:
    _f.write(_VER_INFO_TXT)

# ── EXE (onedir) ───────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HarvestHero",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX triggers AV false positives; leave off.
    console=False,      # windowed app, no cmd window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico" if sys.platform == "win32" else None,
    version=_ver_info_path if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HarvestHero",
)
