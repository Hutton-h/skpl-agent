"""Common pagination schemas for SKPL API.

Cursor-based pagination consistent with AgentScope's conventions.
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Cursor-based pagination parameters."""
    cursor: str | None = Field(
        default=None,
        description="Opaque cursor returned by a previous response. "
        "Omit to request the first page.",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of items to return (1-500).",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based paginated response wrapper."""
    data: list[T] = Field(default_factory=list, description="Items in the current page.")
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for the next page. None when there are no more items.",
    )
    total: int | None = Field(
        default=None, description="Total count of items (when available)."
    )