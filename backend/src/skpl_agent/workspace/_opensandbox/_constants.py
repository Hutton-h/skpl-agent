"""Constants for :class:`OpenSandboxWorkspace`, mirroring the E2B and
K8s ``_constants`` modules.

Only defaults that cannot be derived on the base class live here:
image, timeouts, gateway port, sandbox metadata key, plus the two
sandbox-side anchors the workspace must set (``SANDBOX_WORKDIR`` and
``GATEWAY_HOME``). The bootstrap command sequence and every derived
path (venv, python, script, glob helper, log) live on the workspace /
base class, not here.
"""
DEFAULT_IMAGE = 'python:3.11-slim'
DEFAULT_TIMEOUT = 300
BOOTSTRAP_COMMAND_TIMEOUT = 600.0
DEFAULT_REQUEST_TIMEOUT = BOOTSTRAP_COMMAND_TIMEOUT
DEFAULT_GATEWAY_PORT = 5600
SANDBOX_WORKDIR = '/workspace'
GATEWAY_HOME = '/root/.agentscope'
METADATA_WORKSPACE_ID_KEY = 'skpl_agent.workspace.id'