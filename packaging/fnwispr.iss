; Inno Setup script for fnwispr
; Builds a Windows installer from the PyInstaller output directory.
;
; Usage:
;   iscc packaging/fnwispr.iss
;
; Expects PyInstaller output in: dist/fnwispr/

#define MyAppName "fnwispr"
#define MyAppPublisher "fnrhombus"
#define MyAppURL "https://github.com/fnrhombus/fnwispr"
#define MyAppExeName "fnwispr.exe"

; Version is passed via /DMyAppVersion=x.y.z on the iscc command line.
; Defaults to 0.0.0 for local builds.
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
; Unique AppId — DO NOT change this after first release, or upgrades will break.
AppId={{E7A3F8B2-4C1D-4E6F-9A8B-2D5C7E0F1A3B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=fnwispr-{#MyAppVersion}-setup
SetupIconFile=..\client\icons\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Require 64-bit Windows
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Minimum Windows 10
MinVersion=10.0
; Allow non-admin install (per-user by default)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Uninstall info
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start {#MyAppName} when Windows starts"; GroupDescription: "Startup:"

[Files]
; Include the entire PyInstaller output directory
Source: "..\dist\fnwispr\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Auto-start at login (per-user)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
