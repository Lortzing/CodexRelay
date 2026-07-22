#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef SourceExe
  #error SourceExe is required
#endif
#ifndef TargetArch
  #error TargetArch is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef OutputBaseFilename
  #error OutputBaseFilename is required
#endif
#define AppName "CoderRelay"
#define AppPublisher "Lortzing"
#define AppURL "https://github.com/Lortzing/CoderRelay"
#define AppId "{{ACACB13A-63DD-4D5B-BD41-ED21B1C71062}"
#if TargetArch == "x86"
  #define AllowedArch "x86compatible"
#elif TargetArch == "x86_64"
  #define AllowedArch "x64compatible and not arm64"
  #define Install64Arch "x64compatible"
#elif TargetArch == "arm64"
  #define AllowedArch "arm64"
  #define Install64Arch "arm64"
#else
  #error Unsupported TargetArch
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases/latest
DefaultDirName={localappdata}\Programs\CoderRelay
DefaultGroupName=CoderRelay
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\cdy.exe
ChangesEnvironment=yes
ArchitecturesAllowed={#AllowedArch}
#if defined(Install64Arch)
ArchitecturesInstallIn64BitMode={#Install64Arch}
#endif
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=CoderRelay installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "cdy.exe"; Flags: ignoreversion

[Icons]
Name: "{group}\CoderRelay Documentation"; Filename: "{#AppURL}"
Name: "{group}\Uninstall CoderRelay"; Filename: "{uninstallexe}"

[Code]
function NormalizePathEntry(Value: String): String;
begin
  Value := Trim(Value);
  if (Length(Value) >= 2) and (Value[1] = '"') and (Value[Length(Value)] = '"') then
    Value := Copy(Value, 2, Length(Value) - 2);
  while (Length(Value) > 3) and (Value[Length(Value)] = '\') do Delete(Value, Length(Value), 1);
  Result := Lowercase(Value);
end;

function PathContains(PathValue, Entry: String): Boolean;
var Remaining, Current: String; Separator: Integer;
begin
  Result := False; Remaining := PathValue;
  while Remaining <> '' do begin
    Separator := Pos(';', Remaining);
    if Separator = 0 then begin Current := Remaining; Remaining := ''; end
    else begin Current := Copy(Remaining, 1, Separator - 1); Delete(Remaining, 1, Separator); end;
    if NormalizePathEntry(Current) = NormalizePathEntry(Entry) then begin Result := True; Exit; end;
  end;
end;

function RemovePathEntry(PathValue, Entry: String): String;
var Remaining, Current, ResultValue: String; Separator: Integer;
begin
  ResultValue := ''; Remaining := PathValue;
  while Remaining <> '' do begin
    Separator := Pos(';', Remaining);
    if Separator = 0 then begin Current := Remaining; Remaining := ''; end
    else begin Current := Copy(Remaining, 1, Separator - 1); Delete(Remaining, 1, Separator); end;
    Current := Trim(Current);
    if (Current <> '') and (NormalizePathEntry(Current) <> NormalizePathEntry(Entry)) then begin
      if ResultValue <> '' then ResultValue := ResultValue + ';';
      ResultValue := ResultValue + Current;
    end;
  end;
  Result := ResultValue;
end;

procedure AddToUserPath(Entry: String);
var CurrentPath: String;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', CurrentPath) then CurrentPath := '';
  if not PathContains(CurrentPath, Entry) then begin
    if CurrentPath = '' then CurrentPath := Entry else CurrentPath := CurrentPath + ';' + Entry;
    RegWriteExpandStringValue(HKCU, 'Environment', 'Path', CurrentPath);
  end;
end;

procedure RemoveFromUserPath(Entry: String);
var CurrentPath, UpdatedPath: String;
begin
  if RegQueryStringValue(HKCU, 'Environment', 'Path', CurrentPath) then begin
    UpdatedPath := RemovePathEntry(CurrentPath, Entry);
    if UpdatedPath <> CurrentPath then RegWriteExpandStringValue(HKCU, 'Environment', 'Path', UpdatedPath);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin if CurStep = ssPostInstall then AddToUserPath(ExpandConstant('{app}')); end;
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin if CurUninstallStep = usUninstall then RemoveFromUserPath(ExpandConstant('{app}')); end;
