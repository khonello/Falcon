"""Custom Action validation (spec 7.3): standard library + Windows-native only, no sandboxing.

Validated twice with the same rules -- by the Operator Client's bundled interpreter before
sending, and by the Worker Client's bundled interpreter on arrival (tampering in transit). This
module is the shared implementation both bundle; the Engine also runs it on `action_create`
so a bad script is refused at the source of truth as well.

Python: `compile()` (py_compile equivalent) plus an AST walk of imports against the stdlib
list. PowerShell: module allow-list on `Import-Module` / `using module`; syntax is checked by
the Worker Client's own PowerShell at execution time.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field

# Python 3.10 has sys.stdlib_module_names; keep a fallback so validation never silently passes.
_STDLIB: frozenset[str] = getattr(sys, "stdlib_module_names", frozenset())

# Windows-native modules that ship with the embeddable runtime but aren't in stdlib_module_names.
WINDOWS_NATIVE_PY = frozenset({"winreg", "msvcrt", "winsound", "_winapi"})

# PowerShell modules present on a stock Windows install.
WINDOWS_NATIVE_PS = frozenset({
    "Microsoft.PowerShell.Management", "Microsoft.PowerShell.Utility",
    "Microsoft.PowerShell.Security", "Microsoft.PowerShell.Diagnostics", "CimCmdlets",
    "NetAdapter", "NetTCPIP", "Storage", "ScheduledTasks", "Defender", "BitsTransfer",
})


@dataclass
class ValidationResult:
    ok: bool
    problems: list[str] = field(default_factory=list)


def validate(language: str, source: str) -> ValidationResult:
    if language == "python":
        return validate_python(source)
    if language == "powershell":
        return validate_powershell(source)
    return ValidationResult(False, [f"unsupported language {language!r}"])


def validate_python(source: str) -> ValidationResult:
    problems: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ValidationResult(False, [f"syntax error: {exc}"])
    allowed = _STDLIB | WINDOWS_NATIVE_PY
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for name in names:
            top = name.split(".")[0]
            if top not in allowed:
                problems.append(f"import of non-standard module {name!r}")
    if not _STDLIB:
        problems.append("stdlib module list unavailable on this interpreter; cannot validate")
    return ValidationResult(not problems, problems)


_PS_IMPORT = re.compile(r"^\s*(?:Import-Module|using\s+module)\s+([\w.\-]+)", re.IGNORECASE | re.MULTILINE)


def validate_powershell(source: str) -> ValidationResult:
    problems = [f"Import-Module of non-native module {m!r}"
                for m in _PS_IMPORT.findall(source) if m not in WINDOWS_NATIVE_PS]
    return ValidationResult(not problems, problems)
