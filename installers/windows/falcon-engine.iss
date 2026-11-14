; Inno Setup wrapper for the Engine on Windows: carries the Engine's payload and a Python, asks what only a person knows, and runs
; installers/windows/engine_install.py. Built by installers/windows/build_setup.py (role engine):
;
;     iscc /DPayload=out\falcon-engine /DPython=out\python /DVersion=0.0.1 installers\windows\falcon-engine.iss
;
; PostgreSQL is installed first (postgresql.org's installer). Its superuser password is asked once, to make the Engine's own role with a
; password made here; it goes to the installer in a file in Setup's temporary folder, never on a command line, and is not kept.
; Silent install: falcon-engine-setup.exe /VERYSILENT /ANSWERS=answers.json   (the same keys as below: names, hostname, port,
; pg_password, download_model, or database_url for a role and database that exist).

#ifndef Payload
  #define Payload "out\falcon-engine"
#endif
#ifndef Python
  #define Python "python"
#endif
#ifndef Version
  #define Version "0.0.1"
#endif

[Setup]
AppName=Falcon Engine
AppVersion={#Version}
DefaultDirName={autopf}\Falcon Engine
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=falcon-engine-setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "{#Payload}\*"; DestDir: "{tmp}\payload"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#Python}\*"; DestDir: "{app}\python"; Flags: recursesubdirs createallsubdirs ignoreversion

[UninstallRun]
; with the Python Setup installed, from the program's folder: nothing it removes is in use (see falcon.iss)
Filename: "{app}\python\python.exe"; \
  Parameters: """{app}\app\installers\windows\engine_install.py"" --uninstall --target ""{app}"""; \
  WorkingDir: "{app}"; RunOnceId: "FalconEngineUninstall"; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\install-log.txt"
Type: dirifempty; Name: "{app}"

[Code]
var
  NamesPage: TInputQueryWizardPage;
  DbPage: TInputQueryWizardPage;
  ModelPage: TInputOptionWizardPage;
  InstallFailed: Boolean;

function JsonStr(S: String): String;
var
  I: Integer;
  C: String;
begin
  Result := '"';
  for I := 1 to Length(S) do
  begin
    C := Copy(S, I, 1);
    if (C = '"') or (C = '\') then
      Result := Result + '\' + C
    else
      Result := Result + C;
  end;
  Result := Result + '"';
end;

procedure InitializeWizard;
begin
  NamesPage := CreateInputQueryPage(wpSelectDir, 'This Engine on the network',
    'How the PCs will reach this machine, and who the first IT Admin is',
    'Every name or address the PCs will use to reach this Engine, separated by commas (the first is the one every PC is given). ' +
    'Use a name such as falcon.internal: then moving to another network changes one line on each PC, never the certificate.');
  NamesPage.Add('Names and addresses:', False);
  NamesPage.Add('The first IT Admin''s PC name:', False);
  NamesPage.Add('Port:', False);
  NamesPage.Values[0] := 'falcon.internal,' + GetComputerNameString;
  NamesPage.Values[1] := 'IT-01';
  NamesPage.Values[2] := '7400';
  DbPage := CreateInputQueryPage(NamesPage.ID, 'PostgreSQL',
    'The database the Engine keeps everything in',
    'PostgreSQL must already be installed on this machine. Its superuser password is used once, to make the Engine''s own login with a ' +
    'password of its own; it is not kept.');
  DbPage.Add('Superuser name:', False);
  DbPage.Add('Superuser password:', True);
  DbPage.Values[0] := 'postgres';
  ModelPage := CreateInputOptionPage(DbPage.ID, 'The local language model',
    'Tasks are read by a model that runs on this machine: nothing leaves it',
    'It is about 1.8 GB and is downloaded once. Without it, Tasks still work, with less help in reading what is asked.', False, False);
  ModelPage.Add('Download the model now (needs the internet)');
  ModelPage.Values[0] := True;
end;

procedure WriteAnswers(Path: String);
var
  Given: String;
begin
  Given := ExpandConstant('{param:ANSWERS|}');
  if Given <> '' then
  begin
    FileCopy(Given, Path, False);
    exit;
  end;
  SaveStringToFile(Path, '{"names": ' + JsonStr(Trim(NamesPage.Values[0])) + ', "hostname": ' + JsonStr(Trim(NamesPage.Values[1])) +
    ', "port": ' + JsonStr(Trim(NamesPage.Values[2])) + ', "pg_user": ' + JsonStr(Trim(DbPage.Values[0])) +
    ', "pg_password": ' + JsonStr(DbPage.Values[1]) + ', "download_model": ' + IntToStr(Ord(ModelPage.Values[0])) + '}', False);
end;

// The installer, its account kept in the program folder's install-log.txt; a failure shows its end (exit code 10 when silent).
procedure RunInstaller;
var
  Py, Log, Answers, Args, Said: String;
  Text: AnsiString;
  Code: Integer;
begin
  Py := ExpandConstant('{app}\python\python.exe');
  Log := ExpandConstant('{app}\install-log.txt');
  Answers := ExpandConstant('{tmp}\answers.json');
  WriteAnswers(Answers);
  Args := '-m installers.windows.engine_install --source "' + ExpandConstant('{tmp}\payload') + '" --target "' + ExpandConstant('{app}') +
          '" --python "' + Py + '" --answers "' + Answers + '"';
  WizardForm.StatusLabel.Caption := 'Installing the Falcon Engine (this takes a few minutes)...';
  if not Exec(ExpandConstant('{cmd}'), '/C ""' + Py + '" ' + Args + ' > "' + Log + '" 2>&1"', ExpandConstant('{tmp}\payload'), SW_HIDE,
              ewWaitUntilTerminated, Code) or (Code <> 0) then
  begin
    InstallFailed := True;
    Said := '';
    if LoadStringFromFile(Log, Text) then
    begin
      Said := String(Text);
      if Length(Said) > 900 then
        Said := '...' + Copy(Said, Length(Said) - 900, 900);
    end;
    SuppressibleMsgBox('The Falcon Engine could not finish installing (exit ' + IntToStr(Code) + '). What it said:' + #13#10#13#10 + Said + #13#10#13#10 +
                       'The whole account is in ' + Log + '. Fix what it says and run this setup again: every step checks what is already done.',
                       mbCriticalError, MB_OK, IDOK);
  end;
  DeleteFile(Answers);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunInstaller;
end;

function GetCustomSetupExitCode: Integer;
begin
  if InstallFailed then
    Result := 10
  else
    Result := 0;
end;
