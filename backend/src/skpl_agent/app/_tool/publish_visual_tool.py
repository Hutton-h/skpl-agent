"""Publish-visual tool — lets an agent push visual content to the user interface.

The tool publishes a ``CustomEvent(name='visual')`` onto the current
session's event stream via the message bus, so a front-end subscribed to
``GET /sessions/{sid}/stream`` receives it over the same SSE connection
it already uses — the same delivery mechanism used by
:class:`StateChangeMiddleware` for ``state_updated`` / ``team_updated``
notifications and by :class:`SessionProjection` for cross-session cards.

The tool is constructed per chat turn in :func:`get_toolkit` with the
app-level ``message_bus`` and the request-scoped ``session_id``. All
failures are returned as error tool results; the tool never raises.
"""
from typing import Any, Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from skpl_agent.event import CustomEvent
from skpl_agent.message import TextBlock, ToolResultState
from skpl_agent.permission import PermissionBehavior, PermissionContext, PermissionDecision
from skpl_agent.tool import ToolBase, ToolChunk

from .._bus_ops import publish_session_event

if TYPE_CHECKING:
    from ..message_bus import MessageBus


class _PublishVisualParams(BaseModel):
    """The params for the publish-visual tool."""

    title: str = Field(description='Short title of the visual, shown as the card header in the UI.')
    visual_type: Literal['chart', 'table', 'comparison', 'dashboard', 'timeline', 'action'] = Field(
        description="Visual kind: 'chart' (single chart), 'table' (data table), 'comparison' (side-by-side comparison), 'dashboard' (multi-metric overview), 'timeline' (chronological steps/events), or 'action' (call-to-action card).",
    )
    html: str = Field(
        default='',
        description='Self-contained HTML fragment that renders the visual. Use inline styles only (no external CSS/JS/assets) and width: 100% so it fits the chat column. Optional when `data` is provided — the frontend will render structured data with its own components.',
    )
    summary: str = Field(default='', description='One-sentence plain-text summary of the visual, used by clients that cannot render HTML.')
    data: dict[str, Any] | None = Field(
        default=None,
        description='Optional structured JSON data for the visual. When provided, the frontend renders it with a dedicated component instead of (or in addition to) the raw HTML. The shape depends on visual_type: comparison expects {headers, rows}, dashboard expects {metrics}, timeline expects {items}, action expects {actions, risk_level}.',
    )


class PublishVisual(ToolBase):
    """Push a visual (chart / table / comparison / ...) to the user interface."""

    name: str = 'publish_visual'
    description: str = (
        'Push visual content to the user interface. Use this to present charts, data tables, '
        'side-by-side comparisons, dashboards, timelines, or action cards instead of describing '
        "them in plain text. The `html` argument is a self-contained HTML fragment with "
        'inline styles and width 100% (optional when `data` is provided). '
        'For structured visuals (comparison, dashboard, timeline, action), prefer providing '
        '`data` as a JSON object — the frontend will render it with a dedicated component '
        'that supports user interaction. Always provide at least one of `html` or `data`.'
    )
    input_schema: dict[str, Any] = _PublishVisualParams.model_json_schema()
    is_concurrency_safe: bool = True
    is_read_only: bool = False
    is_state_injected: bool = False
    is_external_tool: bool = False
    is_mcp: bool = False
    mcp_name: str | None = None

    def __init__(self, message_bus: 'MessageBus', session_id: str) -> None:
        """Initialize the publish-visual tool.

        Args:
            message_bus (`MessageBus`):
                The application message bus, used to publish the visual
                event onto the session's event stream (replay log +
                live pub/sub).
            session_id (`str`):
                The session whose SSE stream receives the visual event.
        """
        super().__init__()
        self._bus = message_bus
        self._session_id = session_id

    async def check_permissions(self, tool_input: dict[str, Any], context: PermissionContext) -> PermissionDecision:
        """Always allow — pushing a visual onto the caller's own session
        stream is a low-risk UI operation."""
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message=f'{self.name} is always allowed to be called.',
        )

    async def call(
        self,
        title: str,
        visual_type: Literal['chart', 'table', 'comparison', 'dashboard', 'timeline', 'action'],
        html: str = '',
        summary: str = '',
        data: dict[str, Any] | None = None,
    ) -> ToolChunk:
        """Publish a visual to the session's event stream.

        Args:
            title (`str`):
                Card title shown in the UI.
            visual_type (`Literal[...]`):
                The visual kind.
            html (`str`, optional):
                Self-contained HTML fragment (inline styles, width 100%).
                Optional when ``data`` is provided.
            summary (`str`, optional):
                Plain-text fallback summary.
            data (`dict[str, Any] | None`, optional):
                Structured JSON data for the visual. The frontend will
                render it with a dedicated component for the given
                visual_type. Shape depends on type:
                - comparison: ``{headers: [...], rows: [[...], ...]}``
                - dashboard: ``{metrics: [{label, value, change?}, ...]}``
                - timeline: ``{items: [{time, title, description?}, ...]}``
                - action: ``{actions: [{label, value, style?}, ...], risk_level?: str}``

        Returns:
            `ToolChunk`: Success or error result with a detail message.
        """
        if not html and not data:
            return self._error('At least one of `html` or `data` must be provided.')
        try:
            event = CustomEvent(
                name='visual',
                value={
                    'title': title,
                    'visual_type': visual_type,
                    'html': html,
                    'summary': summary,
                    'data': data,
                },
            )
            await publish_session_event(self._bus, self._session_id, event.model_dump(mode='json'))
        except Exception as e:
            return self._error(f'Failed to publish visual: {e}')
        return ToolChunk(content=[TextBlock(text=f"Visual '{title}' ({visual_type}) published to the user interface.")], state=ToolResultState.SUCCESS)

    def _error(self, message: str) -> ToolChunk:
        """Build an error tool result."""
        return ToolChunk(content=[TextBlock(text=message)], state=ToolResultState.ERROR)