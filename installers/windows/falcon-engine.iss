; Inno Setup wrapper for the Engine on Windows: carries the Engine's payload, a Python and Falcon's own PostgreSQL, asks what only a person
; knows, and runs installers/windows/engine_install.py. Built by installers/windows/build_setup.py (role engine):
;
;     iscc /DPayload=out\falcon-engine /DPython=out\python /DPgSql=out\pgsql /DStore=https://<store> /DVersion=0.0.1 installers\windows\falcon-engine.iss
;
; No PostgreSQL is installed first and none is asked for: the Engine has its own, private to Falcon (docs/SEATS-AND-SETUP.md section 4). The
; person signs in to the company's account in the browser while it installs (internet required). No Admin is made: the first IT Admin runs
; the Admin setup on their own PC. Silent install: falcon-engine-setup.exe /VERYSILENT /ANSWERS=answers.json (names, port, company_name,
; download_model; or database_url for an IT department's own server).

#ifndef Payload
  #define Payload "out\falcon-engine"
#endif
#ifndef Python
  #define Python "python"
#endif
#ifndef Version
  #define Version "0.0.1"
#endif
#ifndef PgSql
  #error Falcon's PostgreSQL is needed: build with /DPgSql=<trimmed pgsql folder> (build_setup.py does)
#endif
#ifndef Store
  #error the Engine setup registers with the store: build it with /DStore=https://...
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
; Falcon's own PostgreSQL, kept with the program and never put on PATH
Source: "{#PgSql}\*"; DestDir: "{app}\pgsql"; Flags: recursesubdirs createallsubdirs ignoreversion

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
    'How the PCs will reach this machine, and whose it is',
    'Every name or address the PCs will use to reach this Engine, separated by commas (the first is the one every PC is given). ' +
    'Use a name such as falcon.internal: then moving to another network changes one line on each PC, never the certificate.');
  NamesPage.Add('Names and addresses:', False);
  NamesPage.Add('Port:', False);
  NamesPage.Add('Company name (only if your Falcon account has none yet):', False);
  NamesPage.Values[0] := 'falcon.internal,' + GetComputerNameString;
  NamesPage.Values[1] := '7400';
  ModelPage := CreateInputOptionPage(NamesPage.ID, 'The local language model',
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
  SaveStringToFile(Path, '{"names": ' + JsonStr(Trim(NamesPage.Values[0])) + ', "port": ' + JsonStr(Trim(NamesPage.Values[1])) +
    ', "company_name": ' + JsonStr(Trim(NamesPage.Values[2])) + ', "download_model": ' + IntToStr(Ord(ModelPage.Values[0])) + '}', False);
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
          '" --python "' + Py + '" --store "{#Store}" --answers "' + Answers + '"';
  WizardForm.StatusLabel.Caption := 'Installing the Falcon Engine (a few minutes). Sign in to your Falcon account in the browser when it opens.';
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
