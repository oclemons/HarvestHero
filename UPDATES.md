# Shipping updates to installed clients

Harvest Hero checks for a newer version on every launch. If one exists,
a small **"↑ Update available: X.Y.Z"** badge appears above the user
chip in the sidebar. Clicking the badge opens the download URL in the
default browser; the user then unzips the new bundle and replaces the
installed `.app` / `.exe` manually.

This is a **check-only** update mechanism today. The app never
downloads or replaces itself. The manifest format is a superset of what
a future auto-apply implementation needs, so the manifest you publish
today will keep working after that upgrade.

---

## 1. Bump the version constant

Edit `version.py`:

```python
__version__ = "1.1.0"
```

Follow semver:

- Patch (`1.1.0` → `1.1.1`): bug fixes only.
- Minor (`1.1.0` → `1.2.0`): new features, no breaking changes.
- Major (`1.1.0` → `2.0.0`): breaking changes to config, schema, or the API contract.

## 2. Build the release bundle

```bash
./build_release.sh          # macOS
build_release.bat           # Windows
```

Zip the produced `.app` / release folder if the script hasn't already.
The default output is `dist/HarvestHero-<yyyymmdd>.zip`.

## 3. Cut a GitHub Release

Upload the zip to a new tag on the repository.

```bash
gh release create v1.1.0 \
    dist/HarvestHero-mac-1.1.0.zip \
    dist/HarvestHero-win-1.1.0.zip \
    --title "Harvest Hero 1.1.0" \
    --notes-file RELEASE_NOTES.md
```

## 4. Upload the manifest

Publish a `latest.json` file **on the same release** — the client
fetches it from
`https://github.com/oclemons/HarvestHero/releases/latest/download/latest.json`,
which GitHub redirects to the current release's assets automatically.

Minimum manifest:

```json
{
  "version": "1.1.0",
  "released_at": "2026-08-15",
  "url_mac":     "https://github.com/oclemons/HarvestHero/releases/download/v1.1.0/HarvestHero-mac-1.1.0.zip",
  "url_windows": "https://github.com/oclemons/HarvestHero/releases/download/v1.1.0/HarvestHero-win-1.1.0.zip",
  "notes": "Bug fixes and security updates. See release notes on GitHub."
}
```

Optional keys the client ignores today but a future auto-apply build
will use:

| Key            | Meaning |
|----------------|---------|
| `url`          | Fallback download URL when the platform-specific one is missing. |
| `url_linux`    | Linux download URL. |
| `sha256_mac` / `sha256_windows` | Hex digest of the corresponding zip. |
| `signature`    | Ed25519 signature over the manifest body (minus this field). Enables trusted auto-apply. |
| `min_supported_version` | If set, clients older than this are told they must update rather than "you can update". |

## 5. Push and verify

```bash
gh release upload v1.1.0 latest.json --clobber
```

Open the running app on any installed machine. Within a few seconds of
launch the update badge should appear in the sidebar. Clicking it opens
the browser to the zip URL.

---

## Overriding the manifest URL per install

Add an `update_url` key to `config.json`:

```json
{
  "mode": "local",
  "update_url": "https://updates.example.com/harvest-hero/latest.json"
}
```

Useful for:

- A customer who mirrors updates behind their own firewall.
- A staging / beta channel — point a few installs at a different
  manifest so they get preview builds.

If the key is absent or empty, the default URL from `version.py`
(`DEFAULT_MANIFEST_URL`) is used.

---

## When you're ready to enable auto-apply

The client already:

- Fetches, parses, and semver-compares the manifest.
- Picks the right platform URL.
- Does the check on a background thread that can't stall the UI.
- Has a stable place to plug in signature verification (`updater.py`).

To turn on auto-apply later, the client would need to:

1. Verify `signature` with a known public key (private key stays on
   your build machine — never in the repo).
2. Download the zip into a staging directory in `USER_DIR`.
3. Verify `sha256`.
4. On macOS: replace the `.app` bundle atomically and relaunch.
5. On Windows: write a helper `update.bat` that waits for the exe to
   exit, replaces it, and starts the new version.

Until that's built, the manifest fields for it (`signature`, `sha256_*`)
are optional and ignored by the current client.
