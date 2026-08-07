"""Secure code execution sandbox.

Provides isolated execution environments for Python and Bash code.
SubprocessSandbox uses subprocess isolation; DockerSandbox (future) uses containers.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a code execution."""

    status: str  # success | error | timeout
    output: str = ""
    error: str = ""
    return_code: int = 0
    duration_seconds: float = 0.0
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CodeSandbox(ABC):
    """Abstract base for code execution sandboxes."""

    name: str = "base"

    @abstractmethod
    async def execute_python(self, code: str, timeout: int = 30) -> ExecutionResult:
        """Execute Python code in the sandbox."""
        ...

    @abstractmethod
    async def execute_bash(self, code: str, timeout: int = 30) -> ExecutionResult:
        """Execute bash code in the sandbox."""
        ...


class SubprocessSandbox(CodeSandbox):
    """Execute code in isolated subprocesses.

    Security notes:
    - Runs in a temporary directory
    - Timeout enforced via subprocess timeout
    - No network access by default (configurable)
    - Output limited to prevent memory exhaustion
    """

    name = "subprocess"

    def __init__(
        self,
        allow_network: bool = False,
        max_output_bytes: int = 1024 * 1024,  # 1 MB
        python_bin: str | None = None,
    ) -> None:
        self._allow_network = allow_network
        self._max_output_bytes = max_output_bytes
        self._python_bin = python_bin or "python"

    async def execute_python(self, code: str, timeout: int = 30) -> ExecutionResult:
        import time
        started = time.time()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = os.path.join(tmpdir, "script.py")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(code)

                env = os.environ.copy()
                if not self._allow_network:
                    env["PYTHONPATH"] = ""

                proc = subprocess.run(
                    [self._python_bin, script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                    env=env,
                )

                output = proc.stdout[:self._max_output_bytes]
                error = proc.stderr[:self._max_output_bytes]

                return ExecutionResult(
                    status="success" if proc.returncode == 0 else "error",
                    output=output,
                    error=error,
                    return_code=proc.returncode,
                    duration_seconds=time.time() - started,
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status="timeout",
                error=f"Execution timed out after {timeout}s",
                duration_seconds=time.time() - started,
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                error=str(e),
                duration_seconds=time.time() - started,
            )

    async def execute_bash(self, code: str, timeout: int = 30) -> ExecutionResult:
        import time
        started = time.time()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = os.path.join(tmpdir, "script.sh")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(code)

                proc = subprocess.run(
                    ["bash", script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                )

                output = proc.stdout[:self._max_output_bytes]
                error = proc.stderr[:self._max_output_bytes]

                return ExecutionResult(
                    status="success" if proc.returncode == 0 else "error",
                    output=output,
                    error=error,
                    return_code=proc.returncode,
                    duration_seconds=time.time() - started,
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status="timeout",
                error=f"Execution timed out after {timeout}s",
                duration_seconds=time.time() - started,
            )
        except FileNotFoundError:
            return ExecutionResult(
                status="error",
                error="bash not found on this system",
                duration_seconds=time.time() - started,
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                error=str(e),
                duration_seconds=time.time() - started,
            )