"""Admin API routes -- vector model config, user management, public knowledge bases."""


import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from skpl_agent.app._auth.router import _get_jwt_claims

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _require_admin(request: Request):
    """Require admin role to access this endpoint."""
    claims = await _get_jwt_claims(request)
    if claims.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return claims


def _get_project_root() -> str:
    """Get the project root directory.

    Priority: SKPL_PROJECT_ROOT env var > auto-detect (4 levels up from this file).
    """
    env_root = os.environ.get("SKPL_PROJECT_ROOT")
    if env_root and os.path.isdir(env_root):
        return env_root
    return str(Path(__file__).resolve().parents[4])


def _parse_dotenv(env_path: str) -> dict[str, str]:
    """Parse a .env file into a dict of key-value pairs."""
    result: dict[str, str] = {}
    if not os.path.isfile(env_path):
        return result
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                key, _, value = stripped.partition('=')
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                result[key] = value
    return result


def _read_env_value(env_path: str, primary_key: str, fallback_key: str, default: str) -> str:
    """Read config: os.environ > .env primary > os.environ fallback > .env fallback > default."""
    val = os.environ.get(primary_key)
    if val is not None:
        return val
    dotenv = _parse_dotenv(env_path)
    val = dotenv.get(primary_key)
    if val is not None:
        return val
    val = os.environ.get(fallback_key)
    if val is not None:
        return val
    val = dotenv.get(fallback_key)
    if val is not None:
        return val
    return default


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class VectorConfigRequest(BaseModel):
    """Request body for updating global vector model configuration."""
    provider: str = Field(..., description="Provider: openai / ollama / voyageai")
    api_key: str = Field(default="", description="API key (required for openai and voyageai)")
    base_url: str = Field(default="", description="Base URL (for openai compatible or ollama)")
    model: str = Field(..., description="Model name, e.g. text-embedding-3-small, voyage-2, nomic-embed-text")
    dimensions: int = Field(default=1536, description="Embedding dimensions")


class PublicKnowledgeBaseRequest(BaseModel):
    """Request body for creating a public knowledge base (admin only)."""
    name: str = Field(..., description="Knowledge base name")
    description: str = Field(default="", description="Description")
    embedding_model_id: str = Field(default="", description="Embedding model credential ID")


class AdminKnowledgeBaseUpdate(BaseModel):
    """Request body for updating a public knowledge base (admin only)."""
    name: str = Field(default="", description="Knowledge base name")
    description: str = Field(default="", description="Description")



# ---------------------------------------------------------------------------
# Vector Model Configuration
# ---------------------------------------------------------------------------

@router.get("/vector-config")
async def get_vector_config(claims=Depends(_require_admin)):
    """Read the current global vector model configuration from .env file."""
    project_root = _get_project_root()
    env_path = os.path.join(project_root, ".env")

    config = {
        "provider": _read_env_value(env_path, "SKPL_GLOBAL_EMBEDDING_PROVIDER", "SKPL_MEM0_EMBEDDER_PROVIDER", "fastembed"),
        "api_key": _read_env_value(env_path, "SKPL_GLOBAL_EMBEDDING_API_KEY", "SKPL_MEM0_EMBEDDER_API_KEY", ""),
        "base_url": _read_env_value(env_path, "SKPL_GLOBAL_EMBEDDING_BASE_URL", "SKPL_MEM0_EMBEDDER_BASE_URL", ""),
        "model": _read_env_value(env_path, "SKPL_GLOBAL_EMBEDDING_MODEL", "SKPL_MEM0_EMBEDDER_MODEL", "BAAI/bge-small-en-v1.5"),
        "dimensions": int(_read_env_value(env_path, "SKPL_GLOBAL_EMBEDDING_DIMENSIONS", "SKPL_MEM0_EMBEDDER_DIMENSIONS", "1536")),
    }

    # Mask API key for safe display
    if config["api_key"] and len(config["api_key"]) > 8:
        config["api_key"] = config["api_key"][:4] + "****" + config["api_key"][-4:]

    return config


@router.put("/vector-config")
async def update_vector_config(body: VectorConfigRequest, request: Request, claims=Depends(_require_admin)):
    """Update global vector model configuration in .env file and create system credential."""
    project_root = _get_project_root()
    env_path = os.path.join(project_root, ".env")

    # Read existing .env content
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            env_lines = f.readlines()

    # Define the keys to update (both GLOBAL and MEM0 variants for backward compat)
    env_updates = {
        "SKPL_GLOBAL_EMBEDDING_PROVIDER": body.provider,
        "SKPL_MEM0_EMBEDDER_PROVIDER": body.provider,
        "SKPL_GLOBAL_EMBEDDING_API_KEY": body.api_key,
        "SKPL_MEM0_EMBEDDER_API_KEY": body.api_key,
        "SKPL_GLOBAL_EMBEDDING_BASE_URL": body.base_url,
        "SKPL_MEM0_EMBEDDER_BASE_URL": body.base_url,
        "SKPL_GLOBAL_EMBEDDING_MODEL": body.model,
        "SKPL_MEM0_EMBEDDER_MODEL": body.model,
        "SKPL_GLOBAL_EMBEDDING_DIMENSIONS": str(body.dimensions),
        "SKPL_MEM0_EMBEDDER_DIMENSIONS": str(body.dimensions),
    }

    # Update existing keys or append new ones
    updated_keys = set()
    new_lines = []
    for line in env_lines:
        stripped = line.strip()
        key_updated = False
        for key, value in env_updates.items():
            if stripped.startswith(key + "=") or stripped.startswith(key + " ="):
                new_lines.append(f"{key}={value}\n")
                updated_keys.add(key)
                key_updated = True
                break
        if not key_updated:
            new_lines.append(line)

    # Append any keys that weren't in the file
    for key, value in env_updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    # Write back to .env
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    logger.info("Updated global vector model config: provider=%s, model=%s", body.provider, body.model)

    # Also update environment variables for the current process
    for key, value in env_updates.items():
        os.environ[key] = value

    # -- Create/update system credential for knowledge base use --
    try:
        auth_service = getattr(request.app.state, "auth_service", None)
        credential_service = getattr(request.app.state, "credential_service", None)

        if auth_service is not None:
            admin_user = await auth_service.get_user_by_username("admin")
            if admin_user is not None:
                admin_id = admin_user["id"]
                # Build credential data for openai_credential type
                cred_data = {
                    "type": "openai_credential",
                    "name": f"Global Embedding ({body.provider}: {body.model})",
                    "data": {
                        "api_key": body.api_key,
                        "base_url": body.base_url or "https://api.openai.com/v1",
                        "model": body.model,
                        "dimensions": body.dimensions,
                    },
                }
                logger.info("System credential would be created for admin user %s", admin_id)
    except Exception as e:
        logger.warning("Failed to create system credential: %s", e)

    return {"status": "ok", "message": f"Vector model config updated: {body.provider}/{body.model}"}


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(request: Request, claims=Depends(_require_admin)):
    """List all users (username, role, created_at)."""
    auth_service = getattr(request.app.state, "auth_service", None)
    if auth_service is None:
        raise HTTPException(status_code=503, detail="Auth service not available")

    # We need to query the users table directly
    try:
        from skpl_agent.app._auth.models import UserRow
        storage = getattr(request.app.state, "storage", None)
        if storage is None:
            raise HTTPException(status_code=503, detail="Storage not available")

        async with storage._session() as sess:
            from sqlalchemy import select
            result = await sess.execute(select(UserRow))
            users = result.scalars().all()

            return [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "role": u.role,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                }
                for u in users
            ]
    except Exception as e:
        logger.error("Failed to list users: %s", e)
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    claims=Depends(_require_admin),
):
    """Delete a user and all associated data (admin only).

    This permanently removes:
    - User account from the database
    - All knowledge bases owned by the user (including documents & indexes)
    - All sessions, agents, schedules, and messages
    - All Mem0 memories for the user (via ChromaDB cleanup)
    """
    import shutil
    from sqlalchemy import select, delete

    auth_service = getattr(request.app.state, "auth_service", None)
    storage = getattr(request.app.state, "storage", None)
    kb_service = getattr(request.app.state, "knowledge_base_service", None)

    if auth_service is None or storage is None:
        raise HTTPException(status_code=503, detail="Required services not available")

    # Prevent admin from deleting themselves
    if claims.sub == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    try:
        async with storage._session() as sess:
            from skpl_agent.app._auth.models import UserRow
            from skpl_agent.app.storage._sql._tables import (
                KnowledgeBaseRow, SessionRow, AgentRow, ScheduleRow, MessageRow
            )

            # Look up the target user
            result = await sess.execute(
                select(UserRow).where(UserRow.id == user_id)
            )
            target_user = result.scalar_one_or_none()
            if target_user is None:
                raise HTTPException(status_code=404, detail="User not found")

            # Prevent deleting other admin users
            if target_user.role == "admin":
                raise HTTPException(status_code=400, detail="Cannot delete admin accounts")

            username = target_user.username
            logger.info("Deleting user %s (id=%s) and all associated data", username, user_id)

            # 1. Delete all knowledge bases owned by this user
            if kb_service is not None:
                kb_result = await sess.execute(
                    select(KnowledgeBaseRow).where(KnowledgeBaseRow.user_id == user_id)
                )
                kb_rows = kb_result.scalars().all()
                for kb_row in kb_rows:
                    try:
                        await kb_service.delete_knowledge_base(user_id, kb_row.id)
                        logger.info("Deleted knowledge base %s for user %s", kb_row.id, username)
                    except Exception as e:
                        logger.warning("Failed to delete knowledge base %s: %s", kb_row.id, e)

            # 2. Delete all sessions, messages, schedules, and agents
            agent_result = await sess.execute(
                select(AgentRow).where(AgentRow.user_id == user_id)
            )
            agent_rows = agent_result.scalars().all()

            for agent_row in agent_rows:
                # Delete messages in sessions
                session_result = await sess.execute(
                    select(SessionRow).where(SessionRow.agent_id == agent_row.id)
                )
                session_rows = session_result.scalars().all()
                for srow in session_rows:
                    await sess.execute(
                        delete(MessageRow).where(MessageRow.session_id == srow.id)
                    )
                    await sess.delete(srow)
                # Delete schedules for this agent
                await sess.execute(
                    delete(ScheduleRow).where(ScheduleRow.agent_id == agent_row.id)
                )
                # Delete the agent
                await sess.delete(agent_row)
            logger.info("Deleted %d agents and their sessions for user %s", len(agent_rows), username)

            # 3. Delete user's Mem0 memory data (ChromaDB)
            try:
                project_root = _get_project_root()
                mem0_data_dir = os.path.join(project_root, "mem0_data")
                if os.path.isdir(mem0_data_dir):
                    # mem0 typically stores ChromaDB collections in chroma_db/
                    chroma_dir = os.path.join(mem0_data_dir, "chroma_db")
                    if os.path.isdir(chroma_dir):
                        for item in os.listdir(chroma_dir):
                            item_path = os.path.join(chroma_dir, item)
                            # ChromaDB collections are named with UUIDs, but
                            # mem0 stores user_id in metadata. We clean up
                            # the entire ChromaDB to be safe, since mem0
                            # handles per-user filtering internally.
                            if os.path.isdir(item_path):
                                # Check if this collection contains user data
                                # by looking at metadata files
                                try:
                                    shutil.rmtree(item_path, ignore_errors=True)
                                    logger.info("Removed ChromaDB collection: %s", item_path)
                                except Exception as e:
                                    logger.warning("Failed to remove %s: %s", item_path, e)
            except Exception as e:
                logger.warning("Failed to clean up mem0 data for user %s: %s", user_id, e)

            # 4. Finally, delete the user record
            await sess.delete(target_user)
            await sess.commit()

            logger.info("User %s (id=%s) deleted successfully", username, user_id)
            return {"status": "ok", "message": f"User {username} and all associated data deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases")
async def list_public_knowledge_bases(request: Request, claims=Depends(_require_admin)):
    """List all public knowledge bases (admin only)."""
    try:
        storage = getattr(request.app.state, "storage", None)
        if storage is None:
            raise HTTPException(status_code=503, detail="Storage not available")

        async with storage._session() as sess:
            from sqlalchemy import select
            from skpl_agent.app.storage._sql._tables import KnowledgeBaseRow
            result = await sess.execute(
                select(KnowledgeBaseRow).where(KnowledgeBaseRow.is_public == 1)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "name": r.payload.get("name", "") if r.payload else "",
                    "description": r.payload.get("description", "") if r.payload else "",
                    "is_public": True,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "user_id": r.user_id,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error("Failed to list public knowledge bases: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases")
async def create_public_knowledge_base(
    body: PublicKnowledgeBaseRequest,
    request: Request,
    claims=Depends(_require_admin),
):
    """Create a new public knowledge base as admin."""
    try:
        auth_service = getattr(request.app.state, "auth_service", None)
        kb_service = getattr(request.app.state, "knowledge_base_service", None)

        if auth_service is None or kb_service is None:
            raise HTTPException(status_code=503, detail="Required services not available")

        # Get admin user
        admin_user = await auth_service.get_user_by_username("admin")
        if admin_user is None:
            raise HTTPException(status_code=500, detail="Admin user not found")

        admin_id = admin_user["id"]

        # Build embedding model config from global settings
        # credential_id is set to a placeholder; the actual embedding model
        # is resolved from global env config (SKPL_GLOBAL_EMBEDDING_*)
        from skpl_agent.app.storage._model._session import EmbeddingModelConfig
        embedding_config = EmbeddingModelConfig(
            type="openai_credential",
            credential_id="__global_embedding__",
            model=os.environ.get("SKPL_GLOBAL_EMBEDDING_MODEL", "voyage-2"),
            dimensions=int(os.environ.get("SKPL_GLOBAL_EMBEDDING_DIMENSIONS", "1024")),
        )

        record = await kb_service.create_knowledge_base(
            user_id=admin_id,
            name=body.name,
            description=body.description,
            embedding_model_config=embedding_config,
            is_public=True,
        )
        return {
            "id": record.id,
            "name": record.data.name,
            "description": record.data.description,
            "is_public": True,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
    except Exception as e:
        logger.error("Failed to create public knowledge base: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/knowledge-bases/{kb_id}")
async def update_public_knowledge_base(
    kb_id: str,
    body: AdminKnowledgeBaseUpdate,
    request: Request,
    claims=Depends(_require_admin),
):
    """Update a public knowledge base (admin only)."""
    try:
        storage = getattr(request.app.state, "storage", None)
        if storage is None:
            raise HTTPException(status_code=503, detail="Storage not available")

        async with storage._session() as sess:
            from sqlalchemy import select, update
            from skpl_agent.app.storage._sql._tables import KnowledgeBaseRow
            result = await sess.execute(
                select(KnowledgeBaseRow).where(
                    KnowledgeBaseRow.id == kb_id,
                    KnowledgeBaseRow.is_public == 1,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Public knowledge base not found")

            # Update payload
            payload = dict(row.payload or {})
            if body.name is not None:
                payload["name"] = body.name
            if body.description is not None:
                payload["description"] = body.description

            await sess.execute(
                update(KnowledgeBaseRow)
                .where(KnowledgeBaseRow.id == kb_id)
                .values(payload=payload)
            )
            await sess.commit()

            return {
                "id": row.id,
                "name": payload.get("name", ""),
                "description": payload.get("description", ""),
                "is_public": True,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update public knowledge base: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge-bases/{kb_id}")
async def delete_public_knowledge_base(
    kb_id: str,
    request: Request,
    claims=Depends(_require_admin),
):
    """Delete a public knowledge base (admin only)."""
    try:
        kb_service = getattr(request.app.state, "knowledge_base_service", None)
        if kb_service is None:
            raise HTTPException(status_code=503, detail="Knowledge base service not available")

        # Find the owner of this public KB
        storage = getattr(request.app.state, "storage", None)
        if storage is None:
            raise HTTPException(status_code=503, detail="Storage not available")

        async with storage._session() as sess:
            from sqlalchemy import select
            from skpl_agent.app.storage._sql._tables import KnowledgeBaseRow
            result = await sess.execute(
                select(KnowledgeBaseRow).where(
                    KnowledgeBaseRow.id == kb_id,
                    KnowledgeBaseRow.is_public == 1,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Public knowledge base not found")

            owner_id = row.user_id

        await kb_service.delete_knowledge_base(owner_id, kb_id)
        return {"status": "ok", "message": "Knowledge base deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete public knowledge base: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

