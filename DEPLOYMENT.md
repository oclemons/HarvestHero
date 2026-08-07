# Harvest Hero — Deployment Runbook

This document walks you through installing Harvest Hero for a real
customer, keeping it healthy day-to-day, and recovering from the most
common problems. Read it once end-to-end before your first install;
after that it's a reference.

---

## 0. Terminology

Two roles matter for deployment:

- **Server PC** — one machine (per pantry) that runs `server.py` and
  owns the SQLite database. Everyone else talks to it over the LAN.
  Can also run the desktop UI locally.
- **Client PC** — every other machine that runs the desktop UI and
  talks to the server over `http://<server-ip>:5000`. Alternatively,
  a single-computer pantry can skip client-server mode entirely and
  run the app in `local` mode (default).

There are also two **user roles**:

- **Admin** — manages inventory items, users, settings, backups,
  archives, machine approvals.
- **Staff** — scans in/out, records pantry visits, updates client
  profiles, uses the shopping list.

And two **API tokens**, printed by the server on first launch:

- **Staff token** — everything staff need. Distribute freely to staff
  PCs.
- **Admin token** — everything the staff token grants **plus** user
  management, item add/edit/delete, settings, activity-log clear,
  machine approvals. Distribute only to admin PCs.

The API layer enforces role checks by which token a client presents,
so a staff-token client cannot escalate to admin operations even if
the operator tries.

---

## 1. First-time server setup

### 1a. Prerequisites

- Windows 10+ / macOS 12+ / any recent Linux.
- Python **only if running from source**. If you're shipping the
  packaged `.app` / `.exe`, Python is not required on the client
  machines.
- A local network that lets client PCs reach the server on TCP 5000.

### 1b. Install

**Packaged build (recommended for customers):**

Unzip `HarvestHero-<yyyymmdd>.zip` on the server PC and drag
`HarvestHero.app` into `/Applications` (macOS) or `HarvestHero.exe`
into `C:\Program Files\HarvestHero\` (Windows).

**From source (developer setup):**

```bash
git clone https://github.com/oclemons/HarvestHero.git
cd HarvestHero
python -m venv .venv && source .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 1c. First launch — capture the admin password

Launch `HarvestHero.app` (or `python main.py` from source). The app
notices there are no users yet and shows a dialog like:

```
A default 'admin' account has been created.
Password: 3f8Q_yk9wZK4
Please log in and reset this password immediately.
```

**Write this password down** — it's generated fresh per install with
`secrets.token_urlsafe(12)` and is not stored anywhere in plaintext.
Log in with:

- Username: `admin`
- Password: (the dialog value)

Change the password immediately: **Admin → Manage Users → Reset
Password** on the `admin` row. Use a passphrase that satisfies the
password policy (8 chars + 3 of 4 character classes).

### 1d. Start the server

Only needed if you want other PCs on the LAN to share the same
database. If this pantry only has one computer, skip this step and
keep the app in `local` mode.

**Packaged build:**

Run `HarvestHero-Server.app` (macOS) or `HarvestHero-Server.exe`
(Windows) alongside the main app. On first launch it prints:

```
============================================================
  Inventory Control Center — LAN Server
  Listening on  http://0.0.0.0:5000

  There are TWO tokens. Give each client PC exactly one, based
  on the role of the user who will sit in front of it.

  Staff token (scanning, transactions, view inventory):
    7xK9…_MIgKQAM

  Admin token (everything staff can do PLUS user management,
  add/edit/delete inventory, settings, client approvals):
    ybt…yq5pyTyx
============================================================
```

**From source:**

```bash
python server.py
```

**Record both tokens.** Keep the admin token off staff PCs.

Note the server's LAN IP address:

- macOS/Linux: `ifconfig` or `ip addr` — look for `inet 192.168.x.x`.
- Windows: `ipconfig` — look for `IPv4 Address`.

### 1e. Open the firewall

The server listens on TCP 5000. Allow inbound traffic on that port
from the LAN only. Do **not** expose it to the public internet.

- **macOS**: System Settings → Network → Firewall → allow the
  HarvestHero-Server executable.
- **Windows**: Windows Defender Firewall → Advanced Settings →
  Inbound Rules → New Rule → TCP 5000, "Domain / Private networks"
  only.
- **Router**: no port forwarding required.

### 1f. Backup schedule

Backups live in the persistent user-data directory:

- macOS: `~/Library/Application Support/HarvestHero/output/backups/`
- Windows: `%APPDATA%\HarvestHero\output\backups\`
- Linux: `~/.local/share/HarvestHero/output/backups/`

The Admin dashboard has a **"Back up now"** quick-action that writes
a timestamped `.db` copy with 0600 permissions.

**Recommended:** a nightly OS-level cron / Task Scheduler job that:

1. Runs the backup quick-action (or `sqlite3 inventory.db ".backup ..."`).
2. Copies the resulting file off-machine (USB, network share, cloud
   sync folder).
3. Rotates old backups after ~90 days.

The database contains password hashes, so treat those backup copies
like passwords — encrypted disk or restricted share only.

---

## 2. First-time client-PC setup

Skip this section for a single-computer pantry.

### 2a. Install the app

Same packaged bundle as the server. Drop it into `/Applications` or
`C:\Program Files\HarvestHero\`.

### 2b. Point it at the server

Run the setup wizard once per client PC:

**Packaged build:** launch `Setup Harvest Hero.command` (macOS) or
`setup_client.bat` (Windows) — both included in the release zip.

**From source:** `python setup_client.py`.

Answer:

- Server IP (e.g. `192.168.1.10`).
- Server port (Enter for the default 5000).
- The token appropriate to this PC's role — **staff** for a scanner
  station, **admin** for a manager's PC.

The wizard tests `http://<ip>:<port>/api/health` with the token you
just entered and saves it to
`~/Library/Application Support/HarvestHero/config.json` (mode 0600).

### 2c. Log in

Launch the app. On the login screen, sign in with an account you
created on the server. If LDAP is enabled (see section 3) a staff
account is auto-provisioned on first successful bind.

If the login fails with **"Too many failed attempts. Try again in 30
seconds"**, that's the brute-force lockout — wait it out. The lockout
counter is per-username and resets on the next successful login.

---

## 3. Optional: enable LDAP / Active Directory

On the admin PC: **Settings → LDAP / Active Directory
Authentication**. Fill in:

- Server URL (e.g. `ldaps://dc.company.com`).
- Port — 636 for LDAPS, 389 for plain LDAP or `use_tls`.
- DN format — for AD, typically `{username}@yourcompany.com`.
- Base DN + search attribute — for AD, base is
  `DC=company,DC=com` and search attr is `sAMAccountName`.
- Service DN and password — optional; used to look up display names.
- **Verify server certificate** — leave **on** unless you're testing
  against a self-signed lab server. When on, the client will refuse
  to bind if the LDAP server's cert doesn't chain to a trusted root.
- **Fall back to local account if LDAP fails** — recommended.

Save, then click **Test Connection**. The service password is
encrypted at rest with a Fernet key stored in
`data/.secret_key` (mode 0600, never checked in).

---

## 4. Optional: enable OpenAI-powered insights

The AI assistant ("Ava") uses OpenAI when a key is present, otherwise
it falls back to a rule-based summary.

Create `OpenAI.env` in the user-data directory:

- macOS: `~/Library/Application Support/HarvestHero/OpenAI.env`
- Windows: `%APPDATA%\HarvestHero\OpenAI.env`

Content:

```
OPENAI_API_KEY=sk-...
```

`chmod 600` the file on macOS/Linux. The frozen app only looks in that
directory (never in `/Applications`, never a parent of the exe, never
your home folder), so multiple installs on the same machine keep their
own keys.

---

## 5. Distributing app updates

See <ref_file file="/Users/octayviaclemons/CascadeProjects/inventory_tracker/UPDATES.md" /> for the full procedure. Summary:

1. Edit `version.py` (`__version__ = "1.1.0"`).
2. `./build_release.sh` (or `build_release.bat` on Windows).
3. `gh release create v1.1.0 dist/HarvestHero-*.zip --title "Harvest Hero 1.1.0"`.
4. Upload a `latest.json` manifest on the same release.
5. Every running client shows an **"↑ Update available: 1.1.0"**
   badge in the sidebar; clicking opens the download URL. Customer
   unzips + drops in the new bundle.

Nothing installs automatically. If you ever compromise your build
machine, no one gets pwned via an auto-updater.

---

## 6. Ongoing operations

### Adding a user

**Admin → Manage Users → Add User.** Choose a role, set a password
that meets the policy, hit save. The password is hashed with
PBKDF2-HMAC-SHA256 at 600k iterations and stored as
`600000$<hex>` alongside a per-user salt.

### Removing a user

Prefer **Archive** over **Delete** — it moves the row to
`archived_users` (auditable) instead of dropping it. Deactivating a
user via **Set Inactive** kicks their session within 30 seconds via
`AppWindow._check_session()`.

### Rotating an API token

**Admin → Settings → Regenerate Tokens** (if you build one; not shipped
yet). Manual path:

```bash
sqlite3 ~/Library/Application\ Support/HarvestHero/data/inventory.db
> DELETE FROM app_settings WHERE key IN ('api_token','admin_api_token');
```

Restart the server. It prints new tokens; re-run `setup_client.py` on
every client PC with the new token appropriate to its role.

### Reviewing activity

**Admin → Manage Users → Activity Log.** Shows every login, admin
action, and archive/restore. Auto-purged after 30 days
(`ACTIVITY_LOG_RETENTION_DAYS` in `main.py`).

---

## 7. Recovery scenarios

### "I lost the admin password"

There's no reset link — the hash is one-way and the key is per-install.

Two options:

1. **Boot in local mode and rehash from source:** stop the app,
   `sqlite3 inventory.db` and run
   `UPDATE users SET password_hash = '600000$<hex>', salt = '<hex>'
    WHERE username = 'admin';` after computing new values with
   `python -c "from auth import hash_password; print(hash_password('newpass'))"`.
2. **Deactivate and recreate:** delete the admin row entirely; on the
   next launch, `main.py` recreates a default admin with a new random
   password and shows it in a dialog.

Option 2 is faster but loses the audit trail associated with the old
account's user id.

### "A staff token was leaked"

Rotate both tokens (procedure in section 6). Re-run
`setup_client.py` on every trusted PC. Any leaked token stops working
the moment the server restarts.

### "The .secret_key file was leaked"

Any LDAP service password ever saved with that key is compromised.

1. Delete `data/.secret_key` — the app will create a new one on next
   launch.
2. Open **Settings → LDAP Configuration** and re-enter the service
   password. It will be re-encrypted with the new key when you save.

Nothing else in the app relies on that key today.

### "The server PC died"

Restore the most recent `.db` backup on a new machine:

```bash
mkdir -p ~/Library/Application\ Support/HarvestHero/data
cp inventory_backup_20260807_2200.db \
   ~/Library/Application\ Support/HarvestHero/data/inventory.db
chmod 600 ~/Library/Application\ Support/HarvestHero/data/inventory.db
```

Launch the server. It reuses the existing tokens stored inside the
DB, so clients keep working as long as the server IP is the same. If
the IP changed, re-run `setup_client.py` with the new IP.

### "I need to migrate an existing customer to client-server mode"

1. On the machine that currently holds the data, launch `server.py`
   and note both tokens.
2. On the same machine, edit `config.json`:

   ```json
   {"mode": "client", "server_url": "http://127.0.0.1:5000", "api_key": "<admin-token>"}
   ```

3. Restart the desktop UI. The app now talks to its own local server.
4. Repeat step 2 on every other PC with the correct IP and token.

---

## 8. Pre-ship checklist

Before you email a customer the zip, confirm:

- [ ] `version.py` bumped and matches the tag you're about to release.
- [ ] `./build_release.sh` finished cleanly and produced
      `dist/HarvestHero-<yyyymmdd>.zip`.
- [ ] The zip does **not** contain your `data/inventory.db`. The
      build scripts don't add it, but double-check by running
      `unzip -l dist/HarvestHero-*.zip | grep inventory.db` — expect
      no matches.
- [ ] `OpenAI.env` is **not** in the bundle. It shouldn't be — it
      lives in `USER_DIR` — but check.
- [ ] `latest.json` has been uploaded to the same GitHub release the
      zip is attached to (otherwise the in-app update badge points
      nowhere).
- [ ] The audit / defect fixes in `CHANGELOG.md` (if you keep one)
      match what's actually in the tag.

---

## 9. Long-term hardening (things to add before scale)

None of these are blocking today, but pencil them in as the customer
base grows:

1. **Signed auto-apply updates.** Turn on the `signature` field in
   `latest.json` and add Ed25519 verification in `updater.py`. See
   `UPDATES.md` §"When you're ready to enable auto-apply".
2. **Per-user API tokens.** The current model gives every PC one of
   two shared tokens. Once you have >5 PCs, mint one token per user
   at login and revoke on logout.
3. **Move off the Flask dev server.** For a LAN pantry this is fine,
   but if you ever WAN-expose it, front the API with Gunicorn +
   Nginx.
4. **Code signing.** Apple Developer ID for macOS and Authenticode
   for Windows. Removes Gatekeeper / SmartScreen warnings for
   customers.
5. **Structured logging.** Right now activity goes into the DB and
   nothing else. Adding a rotating file log in `USER_DIR/logs/`
   makes remote troubleshooting much easier.
