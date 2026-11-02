; Inno Setup wrapper: turns a payload folder into one setup.exe for a role. The work is done by installers/windows/install.py; this only
; carries the payload and a Python, asks for administrator rights, and runs it. Built by installers/windows/build_setup.py, which runs:
;
;     iscc /DRole=worker /DPayload=out\falcon-worker /DBundle=falcon-client.json /DPython=out\python installers\windows\falcon.iss
;
; Roles: worker, admin. The bundle is the Engine's falcon-client.json (address and certificate, no key). The Python is python.org's full
; layout (its NuGet package), installed under the program and not unpacked to a temporary folder: the runtime is a venv made from it, and a
; venv needs the Python it was made from for as long as it lives.

#ifndef Role
  #define Role "worker"
#endif
#ifndef Payload
  #define Payload "out\falcon-" + Role
#endif
#ifndef Bundle
  #define Bundle "falcon-client.json"
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
Source: "{#Bundle}"; DestDir: "{tmp}\payload"; DestName: "falcon-client.json"; Flags: ignoreversion
; the Python the runtime is made from, kept with the program
Source: "{#Python}\*"; DestDir: "{app}\python"; Flags: recursesubdirs createallsubdirs ignoreversion

[Run]
Filename: "{app}\python\python.exe"; \
  Parameters: "-m installers.windows.install --role {#Role} --bundle ""{tmp}\payload\falcon-client.json"" --source ""{tmp}\payload"" --target ""{app}"" --python ""{app}\python\python.exe"" --code-file ""{tmp}\licence-code.txt"""; \
  WorkingDir: "{tmp}\payload"; StatusMsg: "Installing Falcon..."; Flags: waituntilterminated runhidden

[UninstallRun]
Filename: "{app}\runtime\Scripts\python.exe"; \
  Parameters: "-m installers.windows.install --role {#Role} --uninstall"; \
  WorkingDir: "{app}\app"; RunOnceId: "FalconUninstall"; Flags: runhidden

[Code]
{ The licence code (the user, 2 Nov 2026): an admin code for the admin installer, a worker code for the worker one. With it the machine joins
  the Engine at once and nobody has to confirm it; left empty, the machine asks and an IT Admin lets it in with the code shown on its screen.
  It reaches the installer in a file in Setup's own temporary folder, never on a command line, and the installer keeps it only in the
  machine's private settings until it is used. }
var
  CodePage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  CodePage := CreateInputQueryPage(wpSelectDir, 'Licence code',
    'The code from your Falcon licence',
    'Type the {#Role} code from the licence your organisation bought. The machine then joins on its own. ' +
    'Leave it empty to have an IT Admin let it in instead.');
  CodePage.Add('Licence code:', False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    SaveStringToFile(ExpandConstant('{tmp}\licence-code.txt'), Trim(CodePage.Values[0]), False);
end;
