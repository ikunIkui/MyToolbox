#define MyAppName "MyToolbox"
#define MyAppVersion "0.5.0"
#define MyAppPublisher "涛涛"
#define MyAppURL "https://github.com/ikunIkui/MyToolbox"
#define MyAppExeName "MyToolbox.exe"

[Setup]
AppId={{8E5F4B2A-1C3D-4F6E-9A7B-2D8C1E4F6A90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppComments=个人效率工具台 · 时间管理 · 笔记 · 待办
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=MyToolbox_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
;图标欢迎大家帮我想一下 后面暂定
;SetupIconFile=res\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
; 安装前关闭正在运行的程序
CloseApplications=yes
RestartApplications=no
; 最低系统要求
MinVersion=10.0

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked
Name: "autostart"; Description: "开机自动启动"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "dist\MyToolbox\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{userprograms}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#MyAppName}"; \
  ValueData: """{app}\{#MyAppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 只删程序目录，不碰 %APPDATA%
Type: filesandordirs; Name: "{app}"

[Code]
var
  ErrorCode: Integer;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{%APPDATA}\MyToolbox');
    if DirExists(DataDir) then
    begin
      if MsgBox('卸载完成。' + #13#10 + #13#10 +
                '您的数据（笔记、任务、配置）保留在：' + #13#10 +
                DataDir + #13#10 + #13#10 +
                '如需彻底删除，请手动删除此目录。' + #13#10 + #13#10 +
                '是否现在打开数据目录？',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        ShellExec('open', DataDir, '', '', SW_SHOW, ewNoWait, ErrorCode);
      end;
    end;
  end;
end;