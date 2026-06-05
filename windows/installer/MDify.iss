#ifndef AppVersion
#define AppVersion "0.1.0"
#endif

[Setup]
AppId={{C1AB7B2B-2B2D-44D8-8C2D-2DD9F2399DF0}
AppName=MDify
AppVersion={#AppVersion}
AppPublisher=MDify
DefaultDirName={localappdata}\Programs\MDify
DefaultGroupName=MDify
DisableProgramGroupPage=yes
OutputDir=..\..\dist\windows\installer
OutputBaseFilename=MDifySetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\MDify.Windows.exe

[Files]
Source: "..\..\dist\windows\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MDify"; Filename: "{app}\MDify.Windows.exe"
Name: "{autoprograms}\MDify"; Filename: "{app}\MDify.Windows.exe"

[Run]
Filename: "{app}\MDify.Windows.exe"; Description: "Launch MDify"; Flags: nowait postinstall skipifsilent
