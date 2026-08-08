# Code signing setup

Without code signing, every customer sees a scary warning on first
launch:

- **macOS**: *"HarvestHero cannot be opened because Apple cannot check
  it for malicious software."* The customer has to right-click → Open
  or dig into System Settings → Privacy & Security. Every install.
- **Windows**: *"Windows protected your PC"* SmartScreen red screen.
  The customer has to click **More info → Run anyway**. Every install.

Non-technical staff at a food pantry often give up here.

The build scripts (`build_release.sh`, `build_release.bat`) already
have optional signing built in — they read a few environment variables
and, if present, sign + notarize the output. This document walks you
through the one-time setup on each side.

---

## macOS — Apple Developer ID

### 1. Enroll in the Apple Developer Program

- Sign up at <https://developer.apple.com/programs/> — $99/year.
- Enrollment takes a few days for a personal account, longer for a
  business one. Start early.

### 2. Create a Developer ID Application certificate

1. Open Xcode → Settings → Accounts → your Apple ID → Manage
   Certificates → **+ Developer ID Application**.
2. Xcode creates the cert and installs it into your **login**
   keychain along with the private key.
3. Confirm it's installed:

   ```bash
   security find-identity -v -p codesigning
   ```

   You should see a line like:

   ```
   1) A1B2C3... "Developer ID Application: Your Name (TEAM1234)"
   ```

   Copy that full quoted string — that's what goes into
   `APPLE_DEVELOPER_ID`.

### 3. Set up notarytool credentials

Notarization requires an app-specific password (not your Apple ID
password). Create one at <https://appleid.apple.com/account/manage>
→ App-Specific Passwords → Generate.

Save it into your keychain so `notarytool` can use it without
prompting on every build:

```bash
xcrun notarytool store-credentials "HARVESTHERO_NOTARY" \
    --apple-id  "you@example.com" \
    --team-id   "TEAM1234" \
    --password  "<app-specific-password>"
```

The name (`HARVESTHERO_NOTARY`) is what goes into
`APPLE_NOTARY_PROFILE`.

### 4. Build

```bash
export APPLE_DEVELOPER_ID="Developer ID Application: Your Name (TEAM1234)"
export APPLE_NOTARY_PROFILE="HARVESTHERO_NOTARY"
./build_release.sh
```

The script will:

1. PyInstaller-build `HarvestHero.app` (unchanged).
2. `codesign --deep --options runtime --timestamp --sign …` the app.
3. Zip the app and submit it to Apple's notary service.
4. Wait for a verdict (usually 1-3 minutes).
5. `stapler staple` the notarization ticket back onto the `.app`.
6. Zip the release folder.

The resulting zip opens on any Mac with a clean double-click, no
right-click-and-Open workaround.

### Troubleshooting

- **`No signing certificate found`** → the certificate isn't in the
  keychain the build shell can see. Rerun step 2 or log in as the
  same user that owns the cert.
- **Notarization stays "In Progress" forever** → check
  `xcrun notarytool history --keychain-profile HARVESTHERO_NOTARY`
  and inspect the last failed submission with `notarytool log <id>`.
  Most rejections are about missing `--options runtime` or missing
  entitlements — the script already sets `--options runtime`.
- **`spctl -a -vv HarvestHero.app` says "rejected"** → the staple
  step didn't run. Rerun `xcrun stapler staple dist/HarvestHero.app`.

---

## Windows — Authenticode

### Which cert to buy?

| Type | Price/yr | SmartScreen behavior |
|---|---|---|
| **Standard / OV** ("Organization Validated") | $150-300 | Removes "unknown publisher". SmartScreen still warns for the first ~few thousand users until your certificate builds reputation. |
| **EV** ("Extended Validation") | $300-500, ships on a hardware USB token (YubiKey / Safenet). | SmartScreen trusts the binary immediately. This is what commercial software ships with. |

Recommended vendors: **Sectigo** (cheapest), **DigiCert**, **SSL.com**,
**Certera**. Turnaround is 1-3 business days for OV, up to a week for
EV (they mail the USB token).

### Setup after you receive the cert

**If you have an OV cert (a .pfx / .p12 file):**

```
setx WINDOWS_SIGNING_CERT "C:\certs\harvesthero.pfx"
setx WINDOWS_SIGNING_PASSWORD "the-password-you-set-when-buying"
```

**If you have an EV cert (hardware token):**

Insert the USB token. Windows prompts you to install the
manufacturer's PKCS#11 driver — do that once. Then find the cert's
thumbprint:

```
certutil -store My
```

Copy the **Cert Hash(sha1)** value and set:

```
setx WINDOWS_SIGNING_CERT "<40-char-thumbprint-no-spaces>"
```

Do NOT set `WINDOWS_SIGNING_PASSWORD` — the hardware token prompts
for its PIN when `signtool` needs to use the key.

### Install signtool

`signtool.exe` ships with the Windows 10 SDK. Free download from
<https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/>.
Only the "Signing Tools for Desktop Apps" component is required.

After install, `where signtool` should find it. If it's on a
non-standard path, set `SIGNTOOL_EXE` explicitly:

```
setx SIGNTOOL_EXE "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
```

### Build

Open a fresh cmd (so `setx` values are visible) and run:

```
build_release.bat
```

The script will:

1. PyInstaller-build `HarvestHero.exe`.
2. `signtool sign /tr …/td sha256 /fd sha256 HarvestHero.exe`.
3. `signtool verify /pa HarvestHero.exe`.
4. Zip the release.

### Troubleshooting

- **`SignTool Error: No file digest algorithm specified`** → old
  syntax. The script uses `/fd sha256`; if you invoke signtool
  manually, include it.
- **`SignTool Error: The specified timestamp server either could not
  be reached...`** → transient network issue with DigiCert. Retry, or
  override with `set WINDOWS_TIMESTAMP_URL=http://timestamp.sectigo.com`.
- **SmartScreen still warns on a signed build** → your OV cert hasn't
  built reputation yet. Either wait until enough customers run the
  binary, or upgrade to an EV cert.

---

## Not signing yet? Interim workaround

Point customers at the download page's **"macOS: how to open"**
tooltip, which walks them through the right-click → Open flow. Windows
users need to click **More info → Run anyway** on the SmartScreen
prompt.

Both prompts are one-time per user account. The customer sees them
once, clicks through, and the app opens normally forever after.

This isn't great for professional polish, but it lets you ship today
while the paperwork for a Developer ID enrollment goes through.
