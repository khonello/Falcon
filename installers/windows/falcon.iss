; Inno Setup wrapper (not compiled yet): turns a payload folder into one setup.exe for a role. The work is done by installers/windows/install.py;
; this only carries the payload, asks for administrator rights, and runs it. Compile later with:
;
;     iscc /DRole=worker /DPayload=out\falcon-worker /DBundle=falcon-client.json installers\windows\falcon.iss
;
; Roles: worker, admin, superuser. The bundle is the Engine's falcon-client.json (address and certificate, no key).

#ifndef Role
  #define Role "worker"
#endif
#ifndef Payload
  #define Payload "out\falcon-" + Role
#endif
#ifndef Bundle
  #define Bundle "falcon-client.json"
#endif

[Setup]
AppName=Falcon ({#Role})
AppVersion=0.0.1
DefaultDirName={autopf}\Falcon
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputBaseFilename=falcon-{#Role}-setup
Compression=lzma2
SolidCompression=yes
; a signed installer: SignTool=... (final packaging)

[Files]
Source: "{#Payload}\*"; DestDir: "{tmp}\payload"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "{#Bundle}"; DestDir: "{tmp}\payload"; Flags: ignoreversion
; a Python the installer can make the runtime from (bundled interpreter: final packaging)
Source: "python\*"; DestDir: "{tmp}\python"; Flags: recursesubdirs createallsubdirs ignoreversion skipifsourcedoesntexist

[Run]
Filename: "{tmp}\python\python.exe"; \
  Parameters: "-m installers.windows.install --role {#Role} --bundle ""{tmp}\payload\falcon-client.json"" --source ""{tmp}\payload"" --python ""{tmp}\python\python.exe"""; \
  WorkingDirectory: "{tmp}\payload"; StatusMsg: "Installing Falcon..."; Flags: waituntilterminated runhidden

[UninstallRun]
Filename: "{app}\runtime\Scripts\python.exe"; \
  Parameters: "-m installers.windows.install --role {#Role} --uninstall"; \
  WorkingDirectory: "{app}\app"; Flags: runhidden
