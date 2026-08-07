"""Security sandbox for desktop node action execution.

Provides:
- Restricted code execution environment
- Application whitelist/blacklist enforcement
- Dangerous operation detection
- Resource usage limits
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Dangerous patterns ───────────────────────────────────────────────────

_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # (regex pattern, description)
    (r"os\.system\s*\(", "os.system() call"),
    (r"subprocess\.\w+\s*\(", "subprocess call"),
    (r"__import__\s*\(", "dynamic import"),
    (r"eval\s*\(", "eval() call"),
    (r"exec\s*\(", "exec() call"),
    (r"compile\s*\(", "compile() call"),
    (r"open\s*\(.*[rwa]\+?b?\s*\)", "file open with write"),
    (r"shutil\.rmtree\s*\(", "recursive directory removal"),
    (r"shutil\.(move|copytree)\s*\(", "file system manipulation"),
    (r"socket\.\w+\s*\(", "socket operation"),
    (r"requests\.\w+\s*\(", "HTTP request"),
    (r"urllib\.\w+\s*\(", "URL operation"),
    (r"ctypes\.\w+\s*\(", "ctypes call"),
    (r"winreg\.\w+\s*\(", "Windows registry access"),
    (r"win32api\.\w+\s*\(", "Win32 API call"),
    (r"win32com\.\w+\s*\(", "COM operation"),
    (r"pyautogui\.FAILSAFE\s*=\s*False", "disable pyautogui failsafe"),
    (r"keyboard\.\w+\s*\(", "keyboard hook"),
    (r"mouse\.\w+\s*\(", "mouse hook"),
]

# Whitelist of safe pyautogui functions
_SAFE_PYAUTOGUI_FUNCTIONS: set[str] = {
    "click", "doubleClick", "rightClick", "moveTo", "moveRel",
    "dragTo", "dragRel", "scroll", "hscroll", "vscroll",
    "typewrite", "write", "press", "keyDown", "keyUp",
    "hotkey", "screenshot", "locateOnScreen", "locateAllOnScreen",
    "locateCenterOnScreen", "position", "size", "onScreen",
    "FAILSAFE", "PAUSE",
}

# Safe builtins
_SAFE_BUILTINS: set[str] = {
    "abs", "all", "any", "bool", "bytes", "chr", "complex", "dict",
    "divmod", "enumerate", "filter", "float", "format", "frozenset",
    "getattr", "hasattr", "hash", "hex", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max", "min",
    "next", "oct", "ord", "pow", "print", "range", "repr",
    "reversed", "round", "set", "slice", "sorted", "str",
    "sum", "tuple", "type", "zip", "True", "False", "None",
    "Exception", "ValueError", "TypeError", "ImportError",
    "IndexError", "KeyError", "AttributeError", "StopIteration",
    "TimeoutError", "RuntimeError",
}


class SecurityError(Exception):
    """Raised when a security violation is detected."""


class AppSecurityError(SecurityError):
    """Raised when an application interaction is denied."""


class CodeSecurityError(SecurityError):
    """Raised when code contains dangerous operations."""


class ResourceLimitError(SecurityError):
    """Raised when resource limits are exceeded."""


class SecurityPolicy:
    """Security policy for desktop node operations.

    Usage:
        >>> policy = SecurityPolicy(
        ...     allowed_apps=["notepad.exe", "chrome.exe"],
        ...     denied_apps=["cmd.exe", "powershell.exe"],
        ...     max_code_length=5000,
        ... )
        >>> policy.check_app("notepad.exe")  # OK
        >>> policy.check_code("pyautogui.click(100, 200)")  # OK
        >>> policy.check_code("os.system('rm -rf /')")  # Raises SecurityError
    """

    def __init__(
        self,
        allowed_apps: list[str] | None = None,
        denied_apps: list[str] | None = None,
        allow_custom_code: bool = False,
        max_code_length: int = 10000,
        max_execution_time: float = 30.0,
        allow_network: bool = False,
    ) -> None:
        self._allowed_apps: set[str] = {a.lower() for a in (allowed_apps or [])}
        self._denied_apps: set[str] = {a.lower() for a in (denied_apps or [])}
        self._allow_custom_code = allow_custom_code
        self._max_code_length = max_code_length
        self._max_execution_time = max_execution_time
        self._allow_network = allow_network

    # ── App Checks ───────────────────────────────────────────────────────

    def check_app(self, app_name: str) -> None:
        """Check if an application is allowed to be interacted with.

        Raises:
            AppSecurityError: If the app is denied or not allowed.
        """
        app_lower = app_name.lower()

        if self._denied_apps and app_lower in self._denied_apps:
            raise AppSecurityError(
                f"Application '{app_name}' is explicitly denied."
            )

        if self._allowed_apps and app_lower not in self._allowed_apps:
            raise AppSecurityError(
                f"Application '{app_name}' is not in the allowed list."
            )

    def is_app_allowed(self, app_name: str) -> bool:
        """Check if an app is allowed without raising."""
        try:
            self.check_app(app_name)
            return True
        except AppSecurityError:
            return False

    # ── Code Checks ──────────────────────────────────────────────────────

    def check_code(self, code: str) -> None:
        """Validate code string for security violations.

        Args:
            code: Python code string to validate.

        Raises:
            CodeSecurityError: If dangerous patterns are detected.
        """
        # Length check
        if len(code) > self._max_code_length:
            raise CodeSecurityError(
                f"Code exceeds maximum length of {self._max_code_length} "
                f"characters (got {len(code)})."
            )

        # Check for dangerous patterns
        for pattern, description in _DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                raise CodeSecurityError(
                    f"Dangerous operation detected: {description}. "
                    f"Pattern: {pattern}"
                )

        # If custom code is not allowed, only allow pyautogui + time
        if not self._allow_custom_code:
            self._check_limited_imports(code)

    def _check_limited_imports(self, code: str) -> None:
        """Verify only pyautogui and time are imported."""
        import_pattern = re.compile(r"import\s+(\w+)")
        from_pattern = re.compile(r"from\s+(\w+)")

        for match in import_pattern.finditer(code):
            module = match.group(1)
            if module not in ("pyautogui", "time"):
                raise CodeSecurityError(
                    f"Import of '{module}' is not allowed. "
                    f"Only 'pyautogui' and 'time' are permitted."
                )

        for match in from_pattern.finditer(code):
            module = match.group(1)
            if module not in ("pyautogui", "time"):
                raise CodeSecurityError(
                    f"Import from '{module}' is not allowed. "
                    f"Only 'pyautogui' and 'time' are permitted."
                )

    def verify_pyautogui_code(self, code: str) -> None:
        """Verify that code only uses safe pyautogui functions."""
        # Find all pyautogui function calls
        func_pattern = re.compile(r"pyautogui\.(\w+)\s*\(")
        for match in func_pattern.finditer(code):
            func_name = match.group(1)
            if func_name not in _SAFE_PYAUTOGUI_FUNCTIONS:
                raise CodeSecurityError(
                    f"pyautogui.{func_name}() is not in the safe function list."
                )

    def sanitize_code(self, code: str) -> str:
        """Clean and validate code before execution.

        Returns:
            Sanitized code string.

        Raises:
            CodeSecurityError: If code contains dangerous patterns.
        """
        code = code.strip()
        self.check_code(code)
        return code

    # ── Resource Limits ──────────────────────────────────────────────────

    def check_resource_limits(
        self,
        execution_time: float,
        memory_used_mb: float = 0.0,
    ) -> None:
        """Check if resource usage is within limits.

        Raises:
            ResourceLimitError: If limits are exceeded.
        """
        if execution_time > self._max_execution_time:
            raise ResourceLimitError(
                f"Execution time {execution_time:.1f}s exceeds "
                f"maximum of {self._max_execution_time}s."
            )

    # ── Default Policy ───────────────────────────────────────────────────

    @classmethod
    def default(cls) -> "SecurityPolicy":
        """Create a default security policy (restrictive)."""
        return cls(
            allowed_apps=[],
            denied_apps=[
                "cmd.exe", "powershell.exe", "regedit.exe",
                "taskmgr.exe", "mmc.exe", "wscript.exe",
                "cscript.exe", "mshta.exe",
            ],
            allow_custom_code=False,
            max_code_length=10000,
            max_execution_time=30.0,
            allow_network=False,
        )

    @classmethod
    def permissive(cls) -> "SecurityPolicy":
        """Create a permissive policy for development/testing."""
        return cls(
            allowed_apps=[],
            denied_apps=[],
            allow_custom_code=True,
            max_code_length=50000,
            max_execution_time=120.0,
            allow_network=True,
        )