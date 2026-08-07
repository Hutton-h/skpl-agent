"""ORM models for quota-related tables.

Re-exports from the central _tables.py for modular access.
"""

from skpl_agent.app.storage._sql._tables import (
    ResourceUsageRow,
    TenantQuotaRow,
)

__all__ = [
    "ResourceUsageRow",
    "TenantQuotaRow",
]