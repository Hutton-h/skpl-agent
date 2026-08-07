"""OrgService — organization CRUD and membership management."""

from __future__ import annotations

import logging

from sqlalchemy import select, delete

logger = logging.getLogger(__name__)


class OrgService:
    """Service for managing organizations and their members.

    Usage:
        >>> org_svc = OrgService(storage)
        >>> org = await org_svc.create_org("My Team", owner_id="user-1")
        >>> await org_svc.add_member(org["id"], "user-2", role="member")
    """

    def __init__(self, storage):
        """Initialize the organization service.

        Args:
            storage: AsyncSQLAlchemyStorage instance.
        """
        self._storage = storage

    # ------------------------------------------------------------------
    # Organization CRUD
    # ------------------------------------------------------------------

    async def create_org(
        self,
        name: str,
        owner_id: str,
        description: str | None = None,
    ) -> dict:
        """Create a new organization and add the owner as a member.

        Args:
            name: Unique organization name.
            owner_id: User ID of the organization owner.
            description: Optional description.

        Returns:
            dict with organization data.

        Raises:
            ValueError: If the name already exists.
        """
        from .models import OrganizationRow, OrgMemberRow

        async with self._storage._session() as sess:
            # Check for duplicate name
            result = await sess.execute(
                select(OrganizationRow).where(OrganizationRow.name == name)
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"Organization '{name}' already exists")

            # Create org
            org = OrganizationRow(
                name=name,
                description=description,
                owner_id=owner_id,
            )
            sess.add(org)

            # Add owner as member
            member = OrgMemberRow(
                org_id=org.id,
                user_id=owner_id,
                role="owner",
            )
            sess.add(member)
            await sess.commit()

            logger.info("Organization created: %s (id=%s, owner=%s)", name, org.id, owner_id)

            return {
                "id": org.id,
                "name": org.name,
                "description": org.description,
                "owner_id": org.owner_id,
                "is_active": org.is_active,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "updated_at": org.updated_at.isoformat() if org.updated_at else None,
            }

    async def get_org(self, org_id: str) -> dict | None:
        """Get organization by ID.

        Args:
            org_id: Organization UUID.

        Returns:
            Organization dict, or None.
        """
        from .models import OrganizationRow

        async with self._storage._session() as sess:
            org = await sess.get(OrganizationRow, org_id)
            if org is None:
                return None

            return {
                "id": org.id,
                "name": org.name,
                "description": org.description,
                "owner_id": org.owner_id,
                "is_active": org.is_active,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "updated_at": org.updated_at.isoformat() if org.updated_at else None,
            }

    async def list_user_orgs(self, user_id: str) -> list[dict]:
        """List all organizations a user belongs to.

        Args:
            user_id: User UUID.

        Returns:
            List of org dicts with member role.
        """
        from .models import OrgMemberRow, OrganizationRow

        async with self._storage._session() as sess:
            # Find all memberships for this user
            result = await sess.execute(
                select(OrgMemberRow).where(OrgMemberRow.user_id == user_id)
            )
            members = result.scalars().all()
            if not members:
                return []

            orgs = []
            for member in members:
                org = await sess.get(OrganizationRow, member.org_id)
                if org is not None:
                    orgs.append({
                        "id": org.id,
                        "name": org.name,
                        "description": org.description,
                        "owner_id": org.owner_id,
                        "is_active": org.is_active,
                        "role": member.role,
                        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                        "created_at": org.created_at.isoformat() if org.created_at else None,
                        "updated_at": org.updated_at.isoformat() if org.updated_at else None,
                    })

            return orgs

    async def update_org(
        self,
        org_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> dict | None:
        """Update organization name or description.

        Args:
            org_id: Organization UUID.
            name: New name (optional).
            description: New description (optional).

        Returns:
            Updated org dict, or None if not found.
        """
        from .models import OrganizationRow

        async with self._storage._session() as sess:
            org = await sess.get(OrganizationRow, org_id)
            if org is None:
                return None

            if name is not None:
                org.name = name
            if description is not None:
                org.description = description

            await sess.commit()

            return {
                "id": org.id,
                "name": org.name,
                "description": org.description,
                "owner_id": org.owner_id,
                "is_active": org.is_active,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "updated_at": org.updated_at.isoformat() if org.updated_at else None,
            }

    async def delete_org(self, org_id: str) -> bool:
        """Delete an organization (soft-delete: deactivate).

        Args:
            org_id: Organization UUID.

        Returns:
            True if deleted, False if not found.
        """
        from .models import OrganizationRow

        async with self._storage._session() as sess:
            org = await sess.get(OrganizationRow, org_id)
            if org is None:
                return False

            org.is_active = False
            await sess.commit()
            logger.info("Organization deactivated: %s", org_id)
            return True

    # ------------------------------------------------------------------
    # Membership management
    # ------------------------------------------------------------------

    async def add_member(
        self,
        org_id: str,
        user_id: str,
        role: str = "member",
    ) -> dict:
        """Add a user to an organization.

        Args:
            org_id: Organization UUID.
            user_id: User UUID.
            role: Role (owner, admin, member).

        Returns:
            Membership dict.

        Raises:
            ValueError: If user is already a member or org not found.
        """
        from .models import OrgMemberRow, OrganizationRow

        async with self._storage._session() as sess:
            # Verify org exists
            org = await sess.get(OrganizationRow, org_id)
            if org is None:
                raise ValueError(f"Organization '{org_id}' not found")

            # Check for duplicate membership
            result = await sess.execute(
                select(OrgMemberRow).where(
                    OrgMemberRow.org_id == org_id,
                    OrgMemberRow.user_id == user_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"User '{user_id}' is already a member of org '{org_id}'")

            member = OrgMemberRow(
                org_id=org_id,
                user_id=user_id,
                role=role,
            )
            sess.add(member)
            await sess.commit()

            logger.info("Member added: user=%s org=%s role=%s", user_id, org_id, role)

            return {
                "id": member.id,
                "org_id": member.org_id,
                "user_id": member.user_id,
                "role": member.role,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            }

    async def remove_member(self, org_id: str, user_id: str) -> bool:
        """Remove a user from an organization.

        Cannot remove the owner.

        Args:
            org_id: Organization UUID.
            user_id: User UUID.

        Returns:
            True if removed, False if not found.

        Raises:
            ValueError: If trying to remove the owner.
        """
        from .models import OrgMemberRow, OrganizationRow

        async with self._storage._session() as sess:
            org = await sess.get(OrganizationRow, org_id)
            if org is None:
                return False

            if user_id == org.owner_id:
                raise ValueError("Cannot remove the organization owner")

            result = await sess.execute(
                select(OrgMemberRow).where(
                    OrgMemberRow.org_id == org_id,
                    OrgMemberRow.user_id == user_id,
                )
            )
            member = result.scalar_one_or_none()
            if member is None:
                return False

            await sess.delete(member)
            await sess.commit()
            logger.info("Member removed: user=%s org=%s", user_id, org_id)
            return True

    async def update_member_role(
        self,
        org_id: str,
        user_id: str,
        role: str,
    ) -> dict | None:
        """Update a member's role.

        Args:
            org_id: Organization UUID.
            user_id: User UUID.
            role: New role.

        Returns:
            Updated membership dict, or None if not found.
        """
        from .models import OrgMemberRow

        async with self._storage._session() as sess:
            result = await sess.execute(
                select(OrgMemberRow).where(
                    OrgMemberRow.org_id == org_id,
                    OrgMemberRow.user_id == user_id,
                )
            )
            member = result.scalar_one_or_none()
            if member is None:
                return None

            member.role = role
            await sess.commit()

            return {
                "id": member.id,
                "org_id": member.org_id,
                "user_id": member.user_id,
                "role": member.role,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            }

    async def list_members(self, org_id: str) -> list[dict]:
        """List all members of an organization.

        Args:
            org_id: Organization UUID.

        Returns:
            List of membership dicts with user info.
        """
        from .models import OrgMemberRow
        from skpl_agent.app._auth.models import UserRow

        async with self._storage._session() as sess:
            result = await sess.execute(
                select(OrgMemberRow).where(OrgMemberRow.org_id == org_id)
            )
            members = result.scalars().all()
            if not members:
                return []

            result_list = []
            for member in members:
                # Try to look up user info
                username = None
                email = None
                try:
                    user = await sess.get(UserRow, member.user_id)
                    if user is not None:
                        username = user.username
                        email = user.email
                except Exception:
                    pass

                result_list.append({
                    "id": member.id,
                    "org_id": member.org_id,
                    "user_id": member.user_id,
                    "username": username,
                    "email": email,
                    "role": member.role,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                })

            return result_list

    async def get_member_role(self, org_id: str, user_id: str) -> str | None:
        """Get a user's role in an organization.

        Args:
            org_id: Organization UUID.
            user_id: User UUID.

        Returns:
            Role string, or None if not a member.
        """
        from .models import OrgMemberRow

        async with self._storage._session() as sess:
            result = await sess.execute(
                select(OrgMemberRow).where(
                    OrgMemberRow.org_id == org_id,
                    OrgMemberRow.user_id == user_id,
                )
            )
            member = result.scalar_one_or_none()
            return member.role if member is not None else None