# Windows Acceptance Test — What's Verified on Every Release

Every time a `v*.*.*` tag is pushed, the **Windows Release** workflow runs three jobs on GitHub's `windows-latest` runners. The **acceptance** job actually installs, upgrades, uninstalls, and inspects the resulting Windows Explorer / registry state on a fresh Windows Server 2022 machine that has never seen Harvest Hero before. If any test fails, no release is published.

This is a description of what that suite proves, and — equally important — what it can't prove and still needs eyes on the machine.

The current v2.1.0 release passed every check below on run [`32899885548`](https://github.com/oclemons/HarvestHero/actions/runs/32899885548).

---

## What the automated tests prove

The runner starts from a stock `windows-latest` image (no Python, no Git, no PyInstaller, no development tools of any kind — matches your target scenario exactly). The only thing it ever downloads is the same `HarvestHeroSetup-<version>.exe` that ends up on the GitHub Release.

| Test | What it exercises | What passes proves |
|---|---|---|
| **T1** — installer sha-256 matches sidecar | recomputes SHA-256 of the installer and compares against `HarvestHeroSetup-<ver>.exe.sha256` | the integrity check the app itself performs before every auto-update will succeed against this release |
| **T2** — silent fresh install | runs `HarvestHeroSetup-*.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS=desktopicon` on a machine with no prior install | exit code 0 (installer completes without a UAC prompt because it's per-user); pre-populated `%APPDATA%\HarvestHero\` from T2a is untouched |
| **T3** — install directory + exe | `%LOCALAPPDATA%\Programs\HarvestHero\HarvestHero.exe` exists on disk | files were laid down where the installer script promised |
| **T4** — Start-menu shortcut | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Harvest Hero\Harvest Hero.lnk` exists | user can launch the app from the Start menu |
| **T5** — Desktop shortcut | `%USERPROFILE%\Desktop\Harvest Hero.lnk` (or `%PUBLIC%\Desktop\...`) exists | user can launch the app from the desktop (installer creates this when `/TASKS=desktopicon` is selected) |
| **T6** — Uninstall registration | `HKCU:\...\Uninstall\{B4A8...}_is1` exists with correct DisplayName and DisplayVersion, and its UninstallString points at a real `unins000.exe` | the app appears in Settings → Apps, and Windows knows how to remove it |
| **T7** — user data preserved by install | the signature file and non-empty `inventory.db` seeded into `%APPDATA%\HarvestHero\` in T2a are still there after T2b | the installer's exclusion of `%APPDATA%\HarvestHero` from its file list actually works, no matter what junk PyInstaller drags along |
| **T8** — app launches without crashing | starts `HarvestHero.exe`, waits up to 12 seconds for `%APPDATA%\HarvestHero\data\inventory.db` to appear, then kills the process | the exe loads Python, tkinter, customtkinter, sqlite, and all imports (`main.py` reaches the `Database()` constructor); no fatal import/DLL-load crash |
| **T9** — upgrade (re-run installer) | runs the same installer a second time silently | Inno Setup's `AppId` detection kicks in and performs an upgrade in place; user signature + inventory.db still present afterwards |
| **T10** — uninstall preserves user data | invokes the registered `UninstallString /VERYSILENT /SUPPRESSMSGBOXES /NORESTART` | install dir and registry entry are gone, but `%APPDATA%\HarvestHero\test_signature.txt` and `data\inventory.db` are **still there** — Windows Add/Remove Programs cannot delete user data |

If T8 fails, the workflow uploads `install.log`, `upgrade.log`, and `uninstall.log` as an artifact so we can diff Inno Setup's file-copy trace against expectations.

---

## What the automated tests explicitly *cannot* prove

Some things fundamentally require a human on a real Windows machine, because they involve OS UI or vendor infrastructure the runner does not represent.

### 1. First-run SmartScreen warning

The installer is unsigned. On a client's real Windows 10 or 11 machine, the first time they double-click `HarvestHeroSetup-2.1.0.exe`, they will see:

> **Windows protected your PC** — Microsoft Defender SmartScreen prevented an unrecognized app from starting…
>
> [More info] [Don't run]

They must click **More info → Run anyway**. On the CI runner SmartScreen is disabled by policy, so this warning was not present. After code-signing (see `SIGNING.md`) and enough downloads to build reputation with Microsoft, the warning goes away permanently.

**Manual action per client, once per machine:** click through the SmartScreen prompt on first install.

### 2. Antivirus / Windows Defender full-scan latency

Some antivirus products (Bitdefender, McAfee corporate agents, etc.) will scan a freshly downloaded, unsigned installer for 5–90 seconds before letting it execute. The CI runner does not have these products installed. Symptom on a client: double-clicking the installer produces "nothing happens" for a minute, then it runs.

**Manual action per client:** wait for the AV pre-scan to finish. Nothing to fix in code.

### 3. Non-default user-data directory

The acceptance suite verifies `%APPDATA%\HarvestHero`. If a client has redirected `%APPDATA%` to a network share via Folder Redirection group policy (some corporate/government IT setups), that scenario is not exercised here. `paths.py` still uses `%APPDATA%`, so it should follow the redirection automatically, but I have not proven that on hardware.

**Manual action if you have a client on a corporate laptop:** verify their first-run `%APPDATA%\HarvestHero\data\inventory.db` actually lands in a place they can back up.

### 4. Auto-update round trip against a *real* GitHub Release

The acceptance job runs before the release is published, so it can only test the installer against a pre-seeded file system. The complete "app running on 2.0.x sees 2.1.0 on GitHub, downloads, verifies, restarts" round trip needs a client actually on the older version to observe it.

The offline unit tests in `tests/test_update_manager.py` prove the asset-picking, version-comparison, and SHA-256 verification logic in isolation, and they all pass. But the first true production proof of the end-to-end auto-update flow will happen when you cut v2.1.1 and watch a real 2.1.0 client pick it up.

**Manual action, one time:** after cutting v2.1.1 (whenever that lands), verify on any test Windows machine that the running 2.1.0 install shows the Update dialog, installs, and comes back on 2.1.1 with data intact.

### 5. Screen-reader / accessibility behaviour

The launched exe was killed after 12 seconds — enough to prove it didn't crash, not enough to prove NVDA reads the login screen correctly. Nothing in the acceptance suite touches accessibility.

**Manual action if a client uses assistive tech:** verify manually.

### 6. Multi-language / non-ASCII usernames

The runner is en-US and its user profile lives at `C:\Users\runneradmin`. The exe path is ASCII. If a client Windows login is `Åsa` or `李明`, `%APPDATA%` will contain those characters. The code should be fine (Python handles Unicode paths), but this is not exercised in CI.

**Manual action:** if any user has a non-ASCII Windows username, do one manual test install.

### 7. Windows 10 vs Windows 11 vs Server variants

`windows-latest` today is Windows Server 2022. Actual client machines will be Windows 10 or 11. Behaviour should be identical because the installer uses only per-user features, and the exe is a plain WinAPI/tkinter app. But it is untested on those exact OS versions.

**Manual action:** the first client's first install is the true test. Because rollback is trivial (uninstall preserves data), the blast radius of "install went wrong on Windows 10" is: they re-download and try again.

---

## Reproducing the acceptance test locally

You need a Windows machine (or VM) to reproduce it. On that machine:

```powershell
# 1. Grab the installer from the release
$ver = "2.1.0"
$url = "https://github.com/oclemons/HarvestHero/releases/download/v$ver/HarvestHeroSetup-$ver.exe"
Invoke-WebRequest -Uri $url -OutFile "$env:TEMP\HH.exe"

# 2. Seed some fake user data
$userDir = "$env:APPDATA\HarvestHero"
New-Item -ItemType Directory -Force -Path "$userDir\data" | Out-Null
"my-inventory-signature" | Out-File "$userDir\test.txt"

# 3. Install silently
Start-Process "$env:TEMP\HH.exe" -ArgumentList "/VERYSILENT" -Wait

# 4. Verify install
Test-Path "$env:LOCALAPPDATA\Programs\HarvestHero\HarvestHero.exe"   # should be True
Test-Path "$userDir\test.txt"                                        # should still be True

# 5. Launch
& "$env:LOCALAPPDATA\Programs\HarvestHero\HarvestHero.exe"
```

The CI suite runs a strict superset of this.

---

## What still ought to be added

- **Code-signing.** Removes SmartScreen for every client. See `SIGNING.md` — it's the single most impactful UX improvement left.
- **Post-publish smoke test.** A follow-up workflow, triggered `workflow_run: workflows: [Windows Release]`, that installs the just-published release from GitHub and re-runs T2–T10 against the *public* asset URL. Would catch the case where the CI produces a good installer but GitHub's CDN serves a bad one (never actually observed, but a real theoretical gap).
- **First-launch smoke.** Automated login as `admin` / `admin123` and click through the intake screen, to prove the customtkinter widgets actually render. Non-trivial to automate against a customtkinter GUI; skipped for now.
