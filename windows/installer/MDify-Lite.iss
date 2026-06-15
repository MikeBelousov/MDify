#ifndef AppVersion
#define AppVersion "0.1.0"
#endif

[Setup]
AppId={{A4068A99-7778-4A33-8A76-1FEC7692F47A}
AppName=MDify Lite
AppVersion={#AppVersion}
AppPublisher=MDify
DefaultDirName={localappdata}\Programs\MDify Lite
DefaultGroupName=MDify Lite
DisableProgramGroupPage=yes
OutputDir=..\..\dist\windows\installer
OutputBaseFilename=MDify-Windows-Lite-Setup
MinVersion=10.0.26200
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\MDify.Windows.exe

[Files]
Source: "..\..\dist\windows\lite\app\*"; DestDir: "{app}"; Excludes: "Workers\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\windows\lite\app\Workers\mdify-worker-lite\*"; DestDir: "{app}\Workers\mdify-worker-lite"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MDify Lite"; Filename: "{app}\MDify.Windows.exe"
Name: "{autoprograms}\MDify Lite"; Filename: "{app}\MDify.Windows.exe"

[Run]
Filename: "{app}\MDify.Windows.exe"; Description: "Launch MDify Lite"; Flags: nowait postinstall skipifsilent
