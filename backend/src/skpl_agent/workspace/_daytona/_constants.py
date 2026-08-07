"""Constants for :class:`DaytonaWorkspace`, mirroring the E2B and K8s
``_constants`` modules.

Only defaults that cannot be derived on the shared sandbox base live
here: SDK operation timeout, gateway port, sweeper interval, the
sandbox label key used for reattachment, and the gateway home anchor
name. Every derived path (venv, python, script, glob helper, log) and
the bootstrap command sequence live on the workspace / base class, not
here.
"""
DEFAULT_TIMEOUT = 300
DEFAULT_GATEWAY_PORT = 5600
DEFAULT_SWEEP_INTERVAL = 300.0
METADATA_WORKSPACE_ID_KEY = 'skpl_agent.workspace.id'
GATEWAY_HOME_NAME = '.agentscope'