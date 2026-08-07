"""Host-side helpers shared by workspace implementations.

Constants for the standard workspace layout, plus pure functions for
detecting the local ``agentscope`` version and reading scripts bundled
with the package. No Docker / E2B SDK dependency lives here.

This module is internal to ``agentscope.workspace``. Public-sounding
constants are shared within the package, not exported as user-facing
API.
"""
import importlib.resources as _res
DEFAULT_WORKSPACE_INSTRUCTIONS = '<workspace>You have access to a {backend} workspace at {workdir} with the following structure:\n\n```\n{workdir}\n├── data/        # offloaded multimodal files (images, etc.) — system-managed\n├── skills/      # reusable skills, each in its own subdirectory\n└── sessions/    # offloaded session context and tool results — system-managed\n```\n\nThis workspace is your personal working environment. You are responsible for keeping it clean, structured, and easy to navigate over time.\n\n### Project Directory\n- Create a dedicated subdirectory for each task or project under the workspace root.\n- Name each project subdirectory concisely and descriptively, prefixed with its absolute creation date, e.g. `20240315_web-scraper`, so it stays identifiable long after creation.\n- Always create a `README.md` at the project root documenting:\n  - What the project is about\n  - Its absolute creation date\n  - Key decisions or context that would help you resume work later\n\n### Working Across Sessions\n- The same project may be worked on from more than one session at a time. There is no live lock that tells you another session is editing a file — avoid conflicts by isolation, not by hoping:\n  - Prefer `git worktree` with a session-specific name so parallel work happens on separate trees and never shares the same files.\n  - Encode ownership in names (creation date, session identifier) so it is clear which session created what.\n- Be conservative about deletion: do not delete anything you did not create in the current session, prefer archiving over deleting, and rely on git so any change can be rolled back. Confirm before destructive cleanup.\n\n### Scratch / Temporary Files\n- Put one-off experiments, intermediate data, and anything you would otherwise drop in `/tmp` under a `scratch/` directory (created on first use), not inside project directories — this keeps projects and their git history clean.\n- Treat `scratch/` as disposable: exclude it from git, and assume nothing in it is guaranteed to persist. Nothing clears it automatically (it lives inside your persistent workspace, not the OS temp dir), so delete your own scratch files when you are done with them.\n\n### Version Control\n- Prefer initializing a `git` repository in each project directory to track changes and allow rollbacks.\n- If you use git, create a `.gitignore` before the first commit to exclude unwanted files (e.g. virtual environments, cache, `scratch/`, secrets).\n- Never hard-code secrets into project files or commit them — this is a personal environment, but treat credentials as if they could leak.\n\n### Python Environment\n- `uv` is recommended for managing and isolating Python environments per project:\n```shell\nuv venv && uv pip install ...\n- Never install packages into a shared or global environment — each project must manage its own dependencies to avoid conflicts.</workspace>'
DEFAULT_DATA_DIR = 'data'
DEFAULT_SKILLS_DIR = 'skills'
DEFAULT_SESSIONS_DIR = 'sessions'
DEFAULT_MCP_FILE = '.mcp'
DEFAULT_GATEWAY_VENV = '.venv'
DEFAULT_GATEWAY_LOG = 'gateway.log'
DEFAULT_GATEWAY_SCRIPT = '_mcp_gateway_app.py'
DEFAULT_GLOB_HELPER_SCRIPT = '_glob_helper.py'
_GATEWAY_BASE_REQUIREMENTS: tuple[str, ...] = ('mcp', 'uvicorn', 'fastapi')

def _read_gateway_script_bytes() -> bytes:
    """Read the standalone gateway script as bytes via ``importlib.resources``.

    The script ships at
    ``agentscope/workspace/_mcp_gateway/_mcp_gateway_app.py``. Both
    backends copy it to a fixed in-container / in-sandbox path so the
    launch command can invoke it directly, avoiding ``python -m`` and
    the heavy ``agentscope.workspace.__init__`` import graph.
    """
    return _res.files('skpl_agent.workspace._mcp_gateway').joinpath('_mcp_gateway_app.py').read_bytes()

def _read_glob_helper_bytes() -> bytes:
    """Read the standalone glob helper script as bytes.

    The script ships at
    ``agentscope/tool/_builtin/_scripts/_glob_helper.py``. Both Docker
    and E2B backends copy it into the workspace so the :class:`Glob`
    tool can invoke it uniformly via ``exec_shell``.

    Returns:
        `bytes`:
            The raw contents of the ``_glob_helper.py`` script.
    """
    return _res.files('skpl_agent.tool._builtin._scripts').joinpath('_glob_helper.py').read_bytes()