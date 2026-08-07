"""Agent Template Router — browse, inspect, and create agents from templates.

Templates are stored in data/agent-templates.json and provide
pre-configured agent profiles for common use cases.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from ...agent import ContextConfig, ReActConfig
from ..deps import get_current_user_id, get_storage
from ..storage import AgentData, AgentRecord, StorageBase

logger = logging.getLogger(__name__)

template_router = APIRouter(prefix="/api/agent-templates", tags=["agent-templates"])

# Resolve the templates JSON file
_TEMPLATES_PATH = Path(__file__).resolve().parents[4] / "data" / "agent-templates.json"


def _load_templates() -> dict[str, Any]:
    """Load template definitions from the JSON file."""
    if not _TEMPLATES_PATH.exists():
        logger.warning("Agent templates file not found at %s", _TEMPLATES_PATH)
        return {"templates": [], "categories": {}}
    with open(_TEMPLATES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@template_router.get("")
async def list_templates(category: str | None = None):
    """List all available agent templates, optionally filtered by category."""
    data = _load_templates()
    templates = data.get("templates", [])
    if category:
        templates = [t for t in templates if t.get("category") == category]
    return {
        "templates": templates,
        "categories": data.get("categories", {}),
        "total": len(templates),
    }


@template_router.get("/categories")
async def list_categories():
    """List all template categories."""
    data = _load_templates()
    return {"categories": data.get("categories", {})}


@template_router.get("/{template_id}")
async def get_template(template_id: str):
    """Get a single template by ID."""
    data = _load_templates()
    for t in data.get("templates", []):
        if t.get("id") == template_id:
            return t
    raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")


@template_router.post("/{template_id}/create", status_code=status.HTTP_201_CREATED)
async def create_agent_from_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    storage: StorageBase = Depends(get_storage),
):
    """Create a new agent from a template.

    The template's system_prompt, tools, and permission_mode are used to
    initialise the agent. The agent name is set to the template name.
    """
    data = _load_templates()
    template = None
    for t in data.get("templates", []):
        if t.get("id") == template_id:
            template = t
            break

    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    try:
        agent_data = AgentData(
            name=template["name"],
            system_prompt=template.get("system_prompt", ""),
            context_config=ContextConfig(),
            react_config=ReActConfig(),
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    record = AgentRecord(user_id=user_id, data=agent_data)
    agent_id = await storage.upsert_agent(user_id, record)

    logger.info(
        "Created agent '%s' (id=%s) from template '%s' for user %s",
        template["name"], agent_id, template_id, user_id,
    )

    return {
        "agent_id": agent_id,
        "name": template["name"],
        "template_id": template_id,
        "tools": template.get("tools", []),
        "permission_mode": template.get("permission_mode", "accept_edits"),
    }
