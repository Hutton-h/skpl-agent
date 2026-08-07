"""SKPL Organization System — Team collaboration and knowledge sharing.

Provides:
- Organization model (OrganizationRow, OrgMemberRow)
- OrgService (CRUD, membership management)
- Org routes (create, list, manage members)
"""

from skpl_agent.app._organization.models import OrganizationRow, OrgMemberRow
from skpl_agent.app._organization.service import OrgService
from skpl_agent.app._organization.router import router as org_router

__all__ = [
    "OrganizationRow",
    "OrgMemberRow",
    "OrgService",
    "org_router",
]