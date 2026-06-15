#ifndef AppVersion
#define AppVersion "0.1.0"
#endif

[Setup]
AppId={{C72F1849-D1F2-46A1-B41B-99804099AE3B}
AppName=MDify OCR
AppVersion={#AppVersion}
AppPublisher=MDify
DefaultDirName={localappdata}\Programs\MDify OCR
DefaultGroupName=MDify OCR
DisableProgramGroupPage=yes
OutputDir=..\..\dist\windows\installer
OutputBaseFilename=MDify-Windows-OCR-Setup
MinVersion=10.0.17763
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\MDify.Windows.exe

[Files]
Source: "..\..\dist\windows\ocr\app\*"; DestDir: "{app}"; Excludes: "Workers\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\windows\ocr\app\Workers\mdify-worker-ocr\*"; DestDir: "{app}\Workers\mdify-worker-ocr"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MDify OCR"; Filename: "{app}\MDify.Windows.exe"
Name: "{autoprograms}\MDify OCR"; Filename: "{app}\MDify.Windows.exe"

[Run]
Filename: "{app}\MDify.Windows.exe"; Description: "Launch MDify OCR"; Flags: nowait postinstall skipifsilent
