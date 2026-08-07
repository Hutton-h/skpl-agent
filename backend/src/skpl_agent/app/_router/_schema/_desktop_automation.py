"""Request/response schemas for desktop automation endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str


class SessionResponse(BaseModel):
    session_id: str
    status: str
    action_count: int
    created_at: str
    updated_at: str


class ExtractTreeRequest(BaseModel):
    show_all: bool = False


class TreeElementSchema(BaseModel):
    element_id: int
    role: str
    title: str
    text: str


class ExtractTreeResponse(BaseModel):
    tree_text: str
    elements: list[TreeElementSchema]
    element_count: int


class DispatchActionRequest(BaseModel):
    action_type: str = Field(
        ..., description="Action name: click, type, scroll, hotkey, open, etc."
    )
    params: dict = Field(
        default_factory=dict,
        description="Parameters for the action (e.g. {element_id: 3, text: 'hello'})",
    )


class DispatchActionResponse(BaseModel):
    action_type: str
    params: dict
    code: str
    timestamp: str


class AvailableActionSchema(BaseModel):
    name: str
    doc: str


class ActionHistoryResponse(BaseModel):
    session_id: str
    history: list[DispatchActionResponse]