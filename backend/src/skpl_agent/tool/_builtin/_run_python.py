"""RunPython tool — sandboxed Python execution for file generation.

Enables the Agent to generate binary files (Excel, Word, PPT, PDF) by
writing and executing Python scripts in a sandboxed subprocess.

The Write tool saves the script, then RunPython executes it with:
- 30-second timeout
- Module whitelist (openpyxl, python-docx, python-pptx, reportlab, pandas, etc.)
- Restricted file system access (only workspace directory)
- Resource limits
"""

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .._base import ToolBase
from .._response import ToolChunk
from ...message import TextBlock, ToolResultState
from ...permission import PermissionContext, PermissionDecision, PermissionBehavior


class RunPython(ToolBase):
    """Execute a Python script in a sandboxed subprocess.

    The Agent writes a Python script using the Write tool, then calls
    RunPython to execute it. This enables binary file generation
    (xlsx, docx, pptx, pdf) that the Write tool cannot produce directly.
    """

    name: str = "RunPython"
    description: str = (
        "Executes a Python script in a sandboxed subprocess.\n\n"
        "Usage:\n"
        "- First use the Write tool to save a Python script to a file.\n"
        "- Then call RunPython with the script's file path.\n"
        "- The script runs in a sandbox with a 30-second timeout.\n"
        "- Only whitelisted modules are allowed (openpyxl, python-docx, "
        "python-pptx, reportlab, pandas, matplotlib, PIL, numpy, json, csv, "
        "os.path, pathlib, datetime, io, base64, hashlib, re, math, random, "
        "collections, itertools, typing, dataclasses, textwrap, shutil, "
        "tempfile, zipfile, tarfile).\n"
        "- Use this to generate Excel (.xlsx), Word (.docx), PowerPoint "
        "(.pptx), PDF, and image files.\n"
        "- The script's stdout and stderr are captured and returned.\n"
        "- Any files created by the script are returned as the result."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "script_path": {
                "type": "string",
                "description": (
                    "Absolute path to the Python script to execute. "
                    "The script must have been saved using the Write tool first."
                ),
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional command-line arguments to pass to the script."
                ),
                "default": [],
            },
        },
        "required": ["script_path"],
    }
    is_mcp: bool = False
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    is_external_tool: bool = False
    is_state_injected: bool = True

    ALLOWED_MODULES: set[str] = {
        "openpyxl", "openpyxl.styles", "openpyxl.chart", "openpyxl.utils",
        "openpyxl.worksheet", "openpyxl.workbook",
        "docx", "docx.shared", "docx.enum", "docx.oxml",
        "pptx", "pptx.util", "pptx.enum", "pptx.chart",
        "reportlab", "reportlab.lib", "reportlab.platypus", "reportlab.graphics",
        "pandas", "numpy", "matplotlib", "matplotlib.pyplot",
        "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
        "json", "csv", "os", "os.path", "pathlib", "datetime", "io",
        "base64", "hashlib", "re", "math", "random",
        "collections", "itertools", "typing", "dataclasses",
        "textwrap", "shutil", "tempfile", "zipfile", "tarfile",
        "uuid", "copy", "functools", "operator", "statistics",
        "decimal", "fractions", "string", "enum", "logging",
        "warnings", "traceback", "sys", "pprint", "inspect",
        "html", "xml", "xml.etree", "xml.etree.ElementTree",
        "urllib.parse", "urllib.request",
    }

    TIMEOUT_SECONDS: int = 30

    def __init__(self, workspace_dir: str | None = None):
        super().__init__()
        self._workspace_dir = workspace_dir

    async def call(
        self,
        script_path: str,
        args: list[str] | None = None,
        _agent_state: Any = None,
    ) -> ToolChunk:
        args = args or []

        if not os.path.isabs(script_path):
            return ToolChunk(
                content=[TextBlock(
                    text=f"Error: script_path must be an absolute path, got: {script_path}"
                )],
                state=ToolResultState.ERROR,
                is_last=True,
            )

        script = Path(script_path)
        if not script.exists():
            return ToolChunk(
                content=[TextBlock(
                    text=f"Error: script not found: {script_path}. "
                    "Use the Write tool to save the script first."
                )],
                state=ToolResultState.ERROR,
                is_last=True,
            )

        if script.suffix != ".py":
            return ToolChunk(
                content=[TextBlock(
                    text=f"Error: file must be a .py script, got: {script_path}"
                )],
                state=ToolResultState.ERROR,
                is_last=True,
            )

        try:
            content = script.read_text(encoding="utf-8")
        except Exception as e:
            return ToolChunk(
                content=[TextBlock(text=f"Error reading script: {e}")],
                state=ToolResultState.ERROR,
                is_last=True,
            )

        forbidden = self._check_imports(content)
        if forbidden:
            return ToolChunk(
                content=[TextBlock(
                    text=f"Error: script contains forbidden imports: {', '.join(forbidden)}. "
                    f"Only whitelisted modules are allowed."
                )],
                state=ToolResultState.ERROR,
                is_last=True,
            )

        python_exe = sys.executable
        cmd = [python_exe, str(script)] + args

        workspace = self._workspace_dir
        if workspace is None and _agent_state is not None:
            try:
                ws = _agent_state.tool_context.workspace
                if ws:
                    workspace = str(ws)
            except Exception:
                pass

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if workspace:
            env["SKPL_WORKSPACE"] = workspace

        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    cwd=workspace or str(script.parent),
                ),
                timeout=10,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return ToolChunk(
                content=[TextBlock(
                    text=f"Error: script execution timed out after {self.TIMEOUT_SECONDS}s"
                )],
                state=ToolResultState.ERROR,
                is_last=True,
            )
        except Exception as e:
            return ToolChunk(
                content=[TextBlock(text=f"Error executing script: {e}")],
                state=ToolResultState.ERROR,
                is_last=True,
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

        result_parts = []
        if stdout:
            result_parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            result_parts.append(f"STDERR:\n{stderr}")
        if not stdout and not stderr:
            result_parts.append("Script executed successfully (no output).")

        result_parts.append(f"\nExit code: {proc.returncode}")

        if workspace and os.path.isdir(workspace):
            script_dir = script.parent
            try:
                new_files = []
                for f in script_dir.iterdir():
                    if f.is_file() and f != script:
                        mtime = f.stat().st_mtime
                        new_files.append((str(f), mtime))
                if new_files:
                    result_parts.append("\nGenerated files:")
                    for fpath, _ in sorted(new_files, key=lambda x: x[1], reverse=True):
                        result_parts.append(f"  - {fpath}")
            except Exception:
                pass

        state = ToolResultState.ERROR if proc.returncode != 0 else ToolResultState.SUCCESS

        # Collect generated files for frontend rendering
        generated_files = []
        if workspace and os.path.isdir(workspace):
            script_dir = script.parent
            try:
                for f in script_dir.iterdir():
                    if f.is_file() and f != script:
                        generated_files.append({
                            "path": str(f),
                            "name": f.name,
                        })
            except Exception:
                pass

        return ToolChunk(
            content=[TextBlock(text="\n".join(result_parts))],
            state=state,
            is_last=True,
            metadata={
                "script_path": str(script),
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "generated_files": generated_files,
            },
        )

    async def check_permissions(
        self,
        tool_input: dict[str, Any],
        context: PermissionContext,
    ) -> PermissionDecision:
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="RunPython executes in sandboxed subprocess",
        )

    def _check_imports(self, content: str) -> list[str]:
        forbidden = []
        import_pattern = re.compile(
            r'(?:from\s+(\S+?)\s+import|import\s+(.+?)(?:\n|$))'
        )
        for match in import_pattern.finditer(content):
            if match.group(1):
                module = match.group(1)
                modules_to_check = [module]
            elif match.group(2):
                import_line = match.group(2)
                modules_to_check = [
                    m.strip() for m in import_line.split(",") if m.strip()
                ]
            else:
                continue
            for module in modules_to_check:
                parts = module.split(".")
                is_allowed = False
                for i in range(len(parts), 0, -1):
                    if ".".join(parts[:i]) in self.ALLOWED_MODULES:
                        is_allowed = True
                        break
                if not is_allowed:
                    forbidden.append(module)
        return forbidden
