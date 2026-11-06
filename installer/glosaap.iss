; Instalador Glosaap — Inno Setup 6.
;
; Compilación oficial: desde la raíz del repo
;   python build.py --yes --skip-open --installer
; que invoca: ISCC /DMyAppVersion=x.y.z installer\glosaap.iss
;
; Decisiones anti-bugs (ver GUIA_ADMIN.md):
; - Per-usuario (PrivilegesRequired=lowest): no pide admin, instala en
;   %LOCALAPPDATA%\Glosaap. Evita Program Files bloqueado y UAC.
; - AppMutex: si Glosaap está corriendo, el instalador pide cerrarlo
;   en vez de pisar el .exe en uso. El nombre DEBE coincidir con
;   APP_MUTEX_NAME en main.py (tests/test_installer.py lo verifica).
; - AppId NUNCA cambia: es la identidad para upgrades/desinstalación.
;   Cambiarlo huérfana instalaciones previas.

#define MyAppName "Glosaap"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif
#define MyAppPublisher "La Concepción"
#define MyAppURL "https://github.com/Damdev80/Glosaap"

[Setup]
AppId={{B4E7A1C3-8F2D-4A6B-9E5C-1D3F7A9B2C4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\Glosaap
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=Glosaap_Setup_v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible
AppMutex=Local\GlosaapAppMutex
UninstallDisplayName={#MyAppName}
WizardStyle=modern

[Files]
Source: "..\dist\Glosaap.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\updater.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\Glosaap.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Glosaap.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el escritorio"; Flags: unchecked

[Run]
Filename: "{app}\Glosaap.exe"; Description: "Ejecutar Glosaap ahora"; Flags: nowait postinstall skipifsilent
