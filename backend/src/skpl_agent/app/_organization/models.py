"""Organization models for SKPL team collaboration.

Tables:
- ``organizations``: Team/organization records.
- ``org_members``: Membership records linking users to orgs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from skpl_agent.app.storage._sql._tables import _Base

_ID_LEN = 255


class OrganizationRow(_Base):
    """Organization / team record.

    Each organization has a unique name, an owner, and a set of members.
    Organizations are the unit of knowledge base sharing and team
    collaboration.
    """

    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(String(2000), nullable=True)
    owner_id = Column(String(36), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_org_owner", "owner_id"),
        Index("idx_org_active", "is_active"),
    )


class OrgMemberRow(_Base):
    """Membership record linking a user to an organization.

    Roles:
    - ``owner``: Can manage members, delete org, change settings.
    - ``admin``: Can manage members, change settings.
    - ``member``: Can access shared resources.
    """

    __tablename__ = "org_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="member")
    joined_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_org_member_org", "org_id"),
        Index("idx_org_member_user", "user_id"),
        Index("idx_org_member_unique", "org_id", "user_id", unique=True),
    )