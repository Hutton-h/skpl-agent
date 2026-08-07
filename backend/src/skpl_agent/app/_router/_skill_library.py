"""Skill library router — browse and install optional skills.

SKPL's two-tier skill system:

- ``skills/`` (project root): default skills, auto-seeded into every
  workspace on creation (see ``app/_app.py::_create_dev_app``).
- ``skills-library/`` (project root): optional business skills, never
  seeded automatically; users install them into a session workspace
  through the endpoints below.

The skills-library uses a category-based layout::

    skills-library/
      coding/
        code-review/SKILL.md
        dependency-check/SKILL.md
      research/
        competitor-analysis/SKILL.md
        ...
"""
import asyncio
import os
from pathlib import Path

import frontmatter
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..deps import get_current_user_id, get_storage, get_workspace_manager
from ..storage import StorageBase
from ..workspace_manager import WorkspaceManagerBase
from ._workspace import _resolve_workspace

router = APIRouter(prefix='/skill-library', tags=['skill-library'])


class SkillLibraryItem(BaseModel):
    """A single optional skill in the skills-library."""

    name: str = Field(description="The skill's agent-facing name from SKILL.md frontmatter.")
    description: str = Field(default='', description='The skill description from SKILL.md frontmatter.')
    version: str = Field(default='', description='The skill version from SKILL.md frontmatter.')
    category: str = Field(default='', description='The skill category from SKILL.md frontmatter.')
    when_to_use: str = Field(default='', description='Trigger conditions from SKILL.md frontmatter.')
    dir_name: str = Field(description='The relative path inside skills-library/ (e.g. coding/code-review).')
    installed: bool = Field(default=False, description="True when a skill with the same agent-facing name already exists in the session's workspace.")


class SkillActionRequest(BaseModel):
    """The request body for install/uninstall."""

    name: str = Field(description='The library skill name (frontmatter name or directory name).')
    agent_id: str = Field(description='The agent that owns the session.')
    session_id: str = Field(description='The session whose workspace receives the skill.')


class InstallSkillResponse(BaseModel):
    """The install result."""

    ok: bool = Field(description='Whether the skill is present in the workspace after the call.')
    already: bool = Field(description='True when the skill was already installed before the call.')


def _library_dir() -> str:
    """Return the absolute path of the skills-library directory.

    Mirrors the project-root resolution in ``app/_app.py``; this module
    lives one level deeper (``app/_router/``), hence ``parents[5]``.
    """
    project_root = os.environ.get('SKPL_PROJECT_ROOT') or str(Path(__file__).resolve().parents[5])
    return os.path.join(project_root, 'skills-library')


def _scan_library() -> list[dict]:
    """Scan the skills-library directory (category-based) and parse each skill's SKILL.md.

    Layout: ``skills-library/{category}/{skill_name}/SKILL.md``

    Returns:
        `list[dict]`: One dict per skill with the frontmatter fields
        plus ``dir_name`` (e.g. ``coding/code-review``) and the absolute
        ``path``. Directories without a readable SKILL.md are skipped.
        Returns an empty list when the library directory does not exist.
    """
    library_dir = _library_dir()
    if not os.path.isdir(library_dir):
        return []
    items: list[dict] = []
    for cat_name in sorted(os.listdir(library_dir)):
        cat_dir = os.path.join(library_dir, cat_name)
        if not os.path.isdir(cat_dir):
            continue
        for skill_name in sorted(os.listdir(cat_dir)):
            skill_dir = os.path.join(cat_dir, skill_name)
            if not os.path.isdir(skill_dir):
                continue
            skill_md = os.path.join(skill_dir, 'SKILL.md')
            if not os.path.isfile(skill_md):
                continue
            try:
                with open(skill_md, encoding='utf-8') as f:
                    meta = frontmatter.loads(f.read())
            except Exception:
                continue
            items.append({
                'name': str(meta.get('name') or skill_name),
                'description': str(meta.get('description') or ''),
                'version': str(meta.get('version') or ''),
                'category': str(meta.get('category') or cat_name),
                'when_to_use': str(meta.get('when_to_use') or ''),
                'dir_name': f'{cat_name}/{skill_name}',
                'path': skill_dir,
            })
    return items


@router.get('/')
async def list_library_skills(agent_id: str = Query(...), session_id: str = Query(...), user_id: str = Depends(get_current_user_id), storage: StorageBase = Depends(get_storage), workspace_manager: WorkspaceManagerBase = Depends(get_workspace_manager)) -> list[SkillLibraryItem]:
    """List all optional skills in the library, marking installed ones."""
    workspace = await _resolve_workspace(user_id, agent_id, session_id, storage, workspace_manager)
    installed = {s.name for s in await workspace.list_skills()}
    items = await asyncio.to_thread(_scan_library)
    return [SkillLibraryItem(installed=item['name'] in installed, **{k: v for k, v in item.items() if k != 'path'}) for item in items]


@router.get('/categories')
async def list_library_categories(user_id: str = Depends(get_current_user_id)) -> list[str]:
    """Return the deduplicated list of categories across the library."""
    items = await asyncio.to_thread(_scan_library)
    return sorted({item['category'] for item in items if item['category']})


@router.post('/install')
async def install_library_skill(body: SkillActionRequest, user_id: str = Depends(get_current_user_id), storage: StorageBase = Depends(get_storage), workspace_manager: WorkspaceManagerBase = Depends(get_workspace_manager)) -> InstallSkillResponse:
    """Install a library skill into the session's workspace."""
    items = await asyncio.to_thread(_scan_library)
    target = next((item for item in items if item['name'] == body.name or item['dir_name'] == body.name or item['dir_name'].endswith(f'/{body.name}')), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill {body.name!r} not found in the skill library.")
    workspace = await _resolve_workspace(user_id, body.agent_id, body.session_id, storage, workspace_manager)
    installed = {s.name for s in await workspace.list_skills()}
    if target['name'] in installed:
        return InstallSkillResponse(ok=True, already=True)
    try:
        await workspace.add_skill(os.path.abspath(target['path']))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return InstallSkillResponse(ok=True, already=False)


@router.post('/uninstall', status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_library_skill(body: SkillActionRequest, user_id: str = Depends(get_current_user_id), storage: StorageBase = Depends(get_storage), workspace_manager: WorkspaceManagerBase = Depends(get_workspace_manager)) -> None:
    """Remove a skill from the session's workspace by its agent-facing name."""
    workspace = await _resolve_workspace(user_id, body.agent_id, body.session_id, storage, workspace_manager)
    await workspace.remove_skill(body.name)