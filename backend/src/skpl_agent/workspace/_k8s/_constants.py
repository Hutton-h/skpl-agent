"""K8s-specific constants for :class:`K8sWorkspace`.

Path layout (venv, script, log, helper) is derived on the base class
from ``_gateway_home``. This module only carries defaults that cannot
be derived: image, port, apt deps, workdir/gateway_home, and the
K8s-name sanitiser.
"""
import re
DEFAULT_IMAGE = 'python:3.11-slim'
DEFAULT_GATEWAY_PORT = 5600
SYSTEM_DEPS = ('curl', 'ca-certificates', 'ripgrep')
POD_WORKDIR = '/workspace'
GATEWAY_HOME = '/root/.agentscope'
_K8S_UNSAFE_RE = re.compile('[^a-z0-9-]')

def _k8s_safe_name(workspace_id: str, prefix: str='as-ws-') -> str:
    """Produce an RFC-1123 compliant K8s resource name.

    Rules: lowercase alphanumeric + hyphens, max 63 characters,
    must not end with a hyphen.
    """
    name = prefix + _K8S_UNSAFE_RE.sub('-', workspace_id.lower())
    return name[:63].rstrip('-')