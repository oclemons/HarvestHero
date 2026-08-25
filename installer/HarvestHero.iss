; Inno Setup script for Harvest Hero
;
; Build with:
;     iscc /DAppVersion=2.1.0 installer\HarvestHero.iss
;
; Design notes
; ------------
; * Per-user install (PrivilegesRequired=lowest) — no UAC prompt, so
;   pantry staff who aren't Windows admins can update the app.
; * Fixed AppId GUID so the installer recognises upgrades and offers
;   to close the running app rather than making a second install.
; * Never touches %APPDATA%\HarvestHero — that's where the user
;   database, config, and exports live. Deleting them here would defeat
;   the entire "data survives every install" contract.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName        "Harvest Hero"
#define AppExeName     "HarvestHero.exe"
#define AppPublisher   "Harvest Hero"
#define AppURL         "https://github.com/oclemons/HarvestHero"

[Setup]
; Identity — must stay constant across releases for upgrade detection.
AppId={{B4A8D7E3-2C15-4A5B-9F3D-8E7C6A1B2D5F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Inventory Tracker Setup

; Per-user install — no admin needed, appears under HKCU uninstall keys.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

DefaultDirName={autopf}\HarvestHero
DefaultGroupName=Harvest Hero
DisableProgramGroupPage=yes
DisableWelcomePage=no
DisableDirPage=auto
UsePreviousAppDir=yes
UsePreviousTasks=yes

; Kill / restart the running app when upgrading.
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=yes

; Cosmetics
WizardStyle=modern
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

; Output
OutputDir=..\dist\installer
OutputBaseFilename=HarvestHeroSetup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes

; Architecture — the workflow builds x64 wheels/PyInstaller output.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
    Description: "Create a &desktop shortcut"; \
    GroupDescription: "Additional shortcuts:"; \
    Flags: unchecked

[Files]
; Copy the entire PyInstaller onedir output into {app}.
; recursesubdirs picks up the _internal folder that holds the Python
; runtime and bundled data files.
Source: "..\dist\HarvestHero\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";        Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "Launch {#AppName}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Only files placed by this installer are removed. User data in
; %APPDATA%\HarvestHero is intentionally left alone.
Type: filesandordirs; Name: "{app}\_internal"
Type: files;          Name: "{app}\{#AppExeName}"
