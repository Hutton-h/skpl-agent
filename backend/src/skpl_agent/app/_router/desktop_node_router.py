"""Desktop Node REST API — exposes registered desktop nodes to the frontend.

Provides endpoints for:
- Listing connected desktop nodes (from NodeRegistry)
- Node status and health information
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from skpl_agent.app.deps import get_current_user_id
from skpl_agent.app._router._schema._desktop_node import (
    DesktopNodeListResponse,
    DesktopNodeResponse,
)
from skpl_agent.app._service import get_node_registry

router = APIRouter(prefix="/api/desktop", tags=["Desktop Nodes"])

# Rename for consistent export
desktop_node_router = router


@router.get("/nodes", response_model=DesktopNodeListResponse)
async def list_nodes(
    user_id: str = Depends(get_current_user_id),
) -> DesktopNodeListResponse:
    """List all registered desktop nodes with their status."""
    registry = get_node_registry()
    nodes = registry.list_all()
    online_count = registry.count_online()

    node_responses = [
        DesktopNodeResponse(
            node_id=n.node_id,
            node_name=n.node_name,
            status=n.status,
            os_name=n.os_name,
            os_version=n.os_version,
            python_version=n.python_version,
            screen_width=n.screen_width,
            screen_height=n.screen_height,
            cpu_count=n.cpu_count,
            total_memory_mb=n.total_memory_mb,
            capabilities=n.capabilities,
            cpu_percent=n.cpu_percent,
            memory_percent=n.memory_percent,
            active_actions=n.active_actions,
            registered_at=n.registered_at.isoformat(),
            last_seen=n.last_seen.isoformat(),
            is_available=n.is_available,
        )
        for n in nodes
    ]

    return DesktopNodeListResponse(
        nodes=node_responses,
        total=len(nodes),
        online_count=online_count,
    )


@router.get("/nodes/stats")
async def get_node_stats(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Get node registry statistics."""
    registry = get_node_registry()
    return await registry.get_stats()