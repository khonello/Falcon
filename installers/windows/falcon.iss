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
  Parameters: "-m installers.windows.install --role {#Role} --bundle ""{tmp}\payload\falcon-client.json"" --source ""{tmp}\payload"" --target ""{app}"" --python ""{app}\python\python.exe"""; \
  WorkingDir: "{tmp}\payload"; StatusMsg: "Installing Falcon..."; Flags: waituntilterminated runhidden

[UninstallRun]
Filename: "{app}\runtime\Scripts\python.exe"; \
  Parameters: "-m installers.windows.install --role {#Role} --uninstall"; \
  WorkingDir: "{app}\app"; RunOnceId: "FalconUninstall"; Flags: runhidden
