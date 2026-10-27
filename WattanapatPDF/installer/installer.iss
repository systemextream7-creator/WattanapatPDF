; Inno Setup 6 script  ->  dist\installer\WattanapatPDF-Setup-<version>.exe
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "Wattanapat PDF"

[Setup]
AppId={{6B1F2C0E-5D3A-4C7B-9E1A-3F52A8D7C011}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Wattanapat
DefaultDirName={autopf}\Wattanapat PDF
DefaultGroupName=Wattanapat PDF
UninstallDisplayIcon={app}\WattanapatPDF.exe
SetupIconFile=..\assets\app.ico
WizardImageFile=..\assets\installer-side.bmp
WizardSmallImageFile=..\assets\installer-small.bmp
OutputDir=..\dist\installer
OutputBaseFilename=WattanapatPDF-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\WattanapatPDF\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Wattanapat PDF"; Filename: "{app}\WattanapatPDF.exe"
Name: "{autodesktop}\Wattanapat PDF"; Filename: "{app}\WattanapatPDF.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\WattanapatPDF.exe"; Description: "Launch Wattanapat PDF"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; scratch files only - user settings/presets in %APPDATA%\WattanapatPDF are kept
Type: filesandordirs; Name: "{localappdata}\WattanapatPDF\sandbox"
