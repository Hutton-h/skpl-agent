"""E2B-specific constants for :class:`E2BWorkspace`.

Path layout (venv, script, log, helper) is derived on the base class
from ``_gateway_home``. This module only carries defaults that cannot
be derived: template, timeouts, port, sandbox user, metadata key.
"""
DEFAULT_TEMPLATE = 'base'
DEFAULT_TIMEOUT = 300
DEFAULT_GATEWAY_PORT = 5600
SANDBOX_USER_HOME = '/home/user'
SANDBOX_WORKDIR = f'{SANDBOX_USER_HOME}/workspace'
GATEWAY_HOME = f'{SANDBOX_USER_HOME}/.agentscope'
METADATA_WORKSPACE_ID_KEY = 'skpl_agent.workspace.id'