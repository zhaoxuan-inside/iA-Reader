; Inno Setup Script for AI Reader (Windows .exe Installer)
; Generates: output/AI_Reader_Setup_v2.0.0.exe

#define MyAppName "AI Reader"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "AI Reader Team"
#define MyAppURL "https://github.com/ai-reader/ai-reader"
#define MyAppExeName "ai_reader.exe"

[Setup]
AppId={{D37E84B1-A42F-4E90-B861-591DF8AE7120}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\output\windows
OutputBaseFilename=AI_Reader_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associateepub"; Description: "将 .epub 关联至 AI Reader"; GroupDescription: "文件关联:"; Flags: checkedonce
Name: "associatemd"; Description: "将 .md / .markdown 关联至 AI Reader"; GroupDescription: "文件关联:"; Flags: checkedonce
Name: "associatepdf"; Description: "将 .pdf 关联至 AI Reader"; GroupDescription: "文件关联:"; Flags: unchecked

[Files]
; Flutter Release executable and data
Source: "..\..\frontend\build\windows\x64\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Rust Core Engine dynamic library
Source: "..\..\backend\target\release\reader_core.dll"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; File associations for .epub
Root: HKA; Subkey: "Software\Classes\.epub\OpenWithProgids"; ValueType: string; ValueName: "AIReader.epub"; Flags: uninsdeletevalue; Tasks: associateepub
Root: HKA; Subkey: "Software\Classes\AIReader.epub"; ValueType: string; ValueName: ""; ValueData: "EPUB Document"; Flags: uninsdeletekey; Tasks: associateepub
Root: HKA; Subkey: "Software\Classes\AIReader.epub\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletevalue; Tasks: associateepub

; File associations for .md
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "AIReader.md"; Flags: uninsdeletevalue; Tasks: associatemd
Root: HKA; Subkey: "Software\Classes\AIReader.md"; ValueType: string; ValueName: ""; ValueData: "Markdown Document"; Flags: uninsdeletekey; Tasks: associatemd
Root: HKA; Subkey: "Software\Classes\AIReader.md\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletevalue; Tasks: associatemd

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
