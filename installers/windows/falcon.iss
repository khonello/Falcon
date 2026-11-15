; Inno Setup wrapper: turns a payload folder into one setup.exe for a role. The work is done by installers/windows/install.py; this only
; carries the payload and a Python, asks for administrator rights, and runs it. Built by installers/windows/build_setup.py, which runs:
;
;     iscc /DRole=worker /DPayload=out\falcon-worker /DPython=out\python installers\windows\falcon.iss
;     iscc /DRole=admin /DStore=https://<store> ...
;
; Roles: worker, admin. Neither names an Engine: one setup serves every customer (docs/SEATS-AND-SETUP.md). A Worker's is told where its
; Engine is by the store-signed company file beside it; an Admin's signs in to the store and learns it there. The Python is python.org's full
; layout (its NuGet package), installed under the program and not unpacked to a temporary folder: the runtime is a venv made from it, and a
; venv needs the Python it was made from for as long as it lives.

#ifndef Role
  #define Role "worker"
#endif
#ifndef Payload
  #define Payload "out\falcon-" + Role
#endif
#if Role == "admin"
  #ifndef Store
    #error the Admin setup signs in to the store: build it with /DStore=https://...
  #endif
#endif
#ifndef Python
  #define Python "python"
#endif
#ifndef Version
  #define Version "0.0.1"
#endif

[Setup]
AppName=Falcon ({#Role})
AppVersion={#Version}
DefaultDirName={autopf}\Falcon
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=falcon-{#Role}-setup
Compression=lzma2
SolidCompression=yes
; a signed installer: SignTool=... (final packaging)

[Files]
Source: "{#Payload}\*"; DestDir: "{tmp}\payload"; Flags: recursesubdirs createallsubdirs ignoreversion
; the Python the runtime is made from, kept with the program
Source: "{#Python}\*"; DestDir: "{app}\python"; Flags: recursesubdirs createallsubdirs ignoreversion

; The installer itself (installers/windows/install.py) runs from [Code] below, not from a [Run] entry: a [Run] entry's exit code is not looked
; at, so a failed install still said "Installation process succeeded" (found installing for real, 13 Nov 2026).

[UninstallRun]
; with the Python Setup installed, from the program's folder and not from inside what it removes (from {app}\app with the runtime's Python,
; it could not delete either: found 13 Nov 2026). Setup then removes its Python and itself.
Filename: "{app}\python\python.exe"; \
  Parameters: """{app}\app\installers\windows\install.py"" --role {#Role} --uninstall --target ""{app}"""; \
  WorkingDir: "{app}"; RunOnceId: "FalconUninstall"; Flags: runhidden waituntilterminated

; Running Setup's Python leaves files it did not install (compiled __pycache__): its folder goes whole, and the program's folder once empty.
[UninstallDelete]
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\install-log.txt"
Type: dirifempty; Name: "{app}"

[Code]
{ The licence code (the user, 2 Nov 2026): an admin code for the admin installer, a worker code for the worker one. With it the machine joins
  the Engine at once and nobody has to confirm it; left empty, the machine asks and an IT Admin lets it in with the code shown on its screen.
  It reaches the installer in a file in Setup's own temporary folder, never on a command line, and the installer keeps it only in the
  machine's private settings until it is used. }
var
  CodePage: TInputQueryWizardPage;
#if Role == "admin"
  FirstAdminPage: TInputFileWizardPage;
#endif
  InstallFailed: Boolean;

procedure InitializeWizard;
begin
  CodePage := CreateInputQueryPage(wpSelectDir, 'Licence code',
    'The code from your Falcon licence',
    'Type the {#Role} code from the licence your organisation bought. The machine then joins on its own. ' +
    'Leave it empty to have an IT Admin let it in instead.');
  CodePage.Add('Licence code:', False);
#if Role == "admin"
  // The first IT Admin's PC cannot join by a code: nobody is there yet to confirm it. It is given the Engine's first-admin.txt instead.
  FirstAdminPage := CreateInputFilePage(CodePage.ID, 'The first IT Admin',
    'Only for the very first IT Admin''s PC',
    'If this is the first IT Admin''s PC, choose the first-admin.txt the Engine''s installer left in C:\ProgramData\Falcon Engine on the ' +
    'Engine''s machine (copy it here first). Leave it empty for any other Admin: that PC joins with the code it shows.');
  FirstAdminPage.Add('first-admin.txt:', 'Text files|*.txt|All files|*.*', '.txt');
#endif
end;

// Where the Engine is. A Worker: the store-signed company file beside this setup (or /COMPANY=), the same setup for every customer.
// An Admin: it signs in to the store in the browser and learns it there (docs/SEATS-AND-SETUP.md section 5; internet required).
function PlaceArg: String;
var
  Given: String;
  Found: TFindRec;
begin
#if Role == "admin"
  Result := '--store "{#Store}"';
#else
  Given := ExpandConstant('{param:COMPANY|}');
  if (Given = '') and FindFirst(ExpandConstant('{src}\*.falcon'), Found) then
  begin
    Given := ExpandConstant('{src}\') + Found.Name;
    FindClose(Found);
  end;
  Result := '--company "' + Given + '"';
#endif
end;

function FirstAdminArg: String;
var
  Path: String;
begin
  Result := '';
  Path := ExpandConstant('{param:FIRSTADMIN|}');
#if Role == "admin"
  if Path = '' then
    Path := Trim(FirstAdminPage.Values[0]);
#endif
  if Path <> '' then
    Result := ' --first-admin-file "' + Path + '"';
end;

// The installer, with what it says kept in the program folder's install-log.txt. If it fails, the person is shown the end of that log (or, installing
// silently, the exit code is 10), never "succeeded".
procedure RunInstaller;
var
  Py, Log, Args, Said: String;
  Text: AnsiString;
  Code: Integer;
begin
  Py := ExpandConstant('{app}\python\python.exe');
  Log := ExpandConstant('{app}\install-log.txt');
  Args := '-m installers.windows.install --role {#Role} ' + PlaceArg + ' --source "' +
          ExpandConstant('{tmp}\payload') + '" --target "' + ExpandConstant('{app}') + '" --python "' + Py + '" --code-file "' +
          ExpandConstant('{tmp}\licence-code.txt') + '"' + FirstAdminArg;
  WizardForm.StatusLabel.Caption := 'Installing Falcon...';
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
    SuppressibleMsgBox('Falcon could not finish installing (exit ' + IntToStr(Code) + '). What it said:' + #13#10#13#10 + Said + #13#10#13#10 +
                       'The whole account is in ' + Log + '. Fix what it says and run this setup again: every step checks what is already done.',
                       mbCriticalError, MB_OK, IDOK);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    SaveStringToFile(ExpandConstant('{tmp}\licence-code.txt'), Trim(CodePage.Values[0]), False);
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
