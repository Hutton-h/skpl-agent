"""Update router — re-exports the update management API router.

The update management functionality is implemented in
skpl_agent.updates.router. This module provides a thin
re-export for the expected location under app/_router/.
"""

from skpl_agent.updates.router import router as update_router, get_update_service, set_update_service

__all__ = ["update_router", "get_update_service", "set_update_service"]