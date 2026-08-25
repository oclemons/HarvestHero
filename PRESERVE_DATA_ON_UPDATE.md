# Preserving User Data Across Updates

## Summary

**Starting in v2.0.3, your users' inventory, accounts, and settings live in a persistent OS-managed folder that is completely outside the Harvest Hero code folder.** You can re-extract a new release ZIP on top of the old folder, delete the code folder, or move it to another drive — the client's data stays put and their password still works.

## Where the data actually lives

| OS      | Path                                                     |
| ------- | -------------------------------------------------------- |
| macOS   | `~/Library/Application Support/HarvestHero`              |
| Windows | `%APPDATA%\HarvestHero`  (usually `C:\Users\<name>\AppData\Roaming\HarvestHero`) |
| Linux   | `$XDG_DATA_HOME/HarvestHero` (default `~/.local/share/HarvestHero`) |

Inside that folder:

```
HarvestHero/
├── data/
│   ├── inventory.db     ← users, shelves, items, weights, everything
│   └── .secret_key      ← per-machine key for encrypted fields
├── input/               ← CSV uploads
└── output/
    ├── backups/
    ├── exports/
    └── reports/
```

All of this is defined in <code>paths.py</code> and created automatically on first launch.

## Why v2.0.2 and earlier were still losing data

In v2.0.2, `paths.py` only used the persistent OS folder when running as a PyInstaller `.exe`. Clients running `py main.py` from an extracted ZIP hit the development branch, which set `USER_DIR` to **the code folder itself**. So:

- Every re-extract of the release ZIP overwrote `inventory_tracker/data/inventory.db` with whatever was inside the ZIP.
- The ZIP included the developer's `data/inventory.db`, which stomped the client's user table on top of that.

The result was the "the password isn't working" report — the admin hash the client had set was replaced by a different hash from the developer's machine.

## What v2.1.0 adds on top

- Windows clients now install via a real MSI-style installer (`HarvestHeroSetup-<version>.exe`, built with Inno Setup by GitHub Actions).
- The installer's install target is `%LOCALAPPDATA%\Programs\HarvestHero` — a code folder that has never held user data at any point in the app's history.
- Uninstalling from **Settings → Apps** only removes files the installer placed there. `%APPDATA%\HarvestHero` is intentionally left alone so a user can reinstall later and pick up exactly where they left off. To fully wipe data they delete that folder manually.
- The in-app updater downloads the installer, checks its SHA-256 against the release's `.exe.sha256` sidecar, and hands control to the installer with `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`. A corrupted or tampered download aborts before anything is installed.

## What v2.0.3 changed

1. **`paths.py` always uses the persistent OS folder**, whether running from source or from a frozen `.exe`. There is a `HARVESTHERO_DEV_DIR` env-var escape hatch for local development; it must never be set on a client machine.

2. **First-run migration**: if a legacy install left a database at `<code>/data/inventory.db` or `<code>/inventory.db`, the app copies it into the new persistent location on first launch, then renames the legacy file with a `.migrated` suffix so it isn't picked up again.

3. **The release ZIP is built with `git archive`** (see `build_source_zip.sh` / `.bat`) so it can only contain files that are tracked in git. Untracked developer files — `data/inventory.db`, `.secret_key`, `OpenAI.env`, `VercelToken/`, `.vercel/`, `.devin/` — cannot leak into the ZIP.

4. **The auto-updater already skipped `data/`** (see `update_manager.apply_update`), but that's now defence-in-depth: the data physically is not in the code folder anymore.

## For end users

They don't need to do anything different — the app just remembers them now.

- **First install of v2.0.3+**: they log in once with their existing credentials (or the admin resets their password once); after that, every future update leaves the account alone.
- **Manual re-install by re-extracting a ZIP**: safe. The code folder is replaced, but `~/Library/Application Support/HarvestHero` (or the Windows/Linux equivalent) is untouched.
- **Auto-update via the in-app update notification**: safe. `update_manager` copies new code into place and never touches the persistent data folder.

## For the developer / maintainer

- Build the release ZIP with **`./build_source_zip.sh`** (macOS/Linux) or **`build_source_zip.bat`** (Windows). Do **not** manually run `zip -r inventory_tracker/` — it will sweep up untracked files.
- The script uses `git archive HEAD`, so anything you want in the release must be committed first. It also verifies after packaging that no known-sensitive path (`VercelToken`, `.env`, `data/`, etc.) made it into the ZIP.
- Bump `VERSION.json` **before** running the build so the ZIP name matches the release tag.

## Backup and restore

Nothing changes here — a client who wants to move to a new machine copies the whole `HarvestHero` user-data folder to the same location on the new machine. There is nothing worth preserving inside the code folder.

The Reports view continues to write manual and scheduled DB backups to `output/backups/` inside the user-data folder.
