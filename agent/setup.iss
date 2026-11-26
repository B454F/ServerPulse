
#define MyAppName "ServerPulse Agent"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "ServerPulse"
#define MyAppExeName "ServerPulse.exe"

[Setup]
AppId=ServerPulse.Agent
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={localappdata}\Programs\ServerPulse
DefaultGroupName=ServerPulse

PrivilegesRequired=lowest
DisableProgramGroupPage=yes

OutputDir=installer
OutputBaseFilename=ServerPulseSetup

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

UninstallDisplayName=ServerPulse Agent
UninstallDisplayIcon={app}\{#MyAppExeName}

CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional options:"
Name: "startup"; Description: "Start ServerPulse when I sign in to Windows"; GroupDescription: "Additional options:"; Flags: unchecked

[Files]
Source: "dist\ServerPulse\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ServerPulse"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ServerPulse"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\ServerPulse"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch ServerPulse Agent"; Flags: nowait postinstall skipifsilent
