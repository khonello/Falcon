"""Custom Action validation lives in `common.custom_actions` so the Operator Client (pre-send)
and Worker Client (on arrival) run exactly the same rules the Engine does."""

from common.custom_actions import (  # noqa: F401
    WINDOWS_NATIVE_PS,
    WINDOWS_NATIVE_PY,
    ValidationResult,
    validate,
    validate_powershell,
    validate_python,
)
