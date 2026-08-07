"""Request/response schemas for desktop node endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class DesktopNodeResponse(BaseModel):
    """A registered desktop node visible to the frontend."""
    node_id: str
    node_name: str
    status: str  # connecting | online | idle | busy | offline
    os_name: str
    os_version: str
    python_version: str
    screen_width: int
    screen_height: int
    cpu_count: int
    total_memory_mb: int
    capabilities: list[str]
    cpu_percent: float
    memory_percent: float
    active_actions: int
    registered_at: str
    last_seen: str
    is_available: bool


class DesktopNodeListResponse(BaseModel):
    nodes: list[DesktopNodeResponse]
    total: int
    online_count: int