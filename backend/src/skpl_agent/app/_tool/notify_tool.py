"""Send-notification tool — lets an agent push messages to the user.

Supports three channels:

- ``whatsapp``: WhatsApp Cloud API, using the caller's
  :class:`WhatsAppCloudCredential`.
- ``email``: SMTP email, using the caller's :class:`SMTPCredential`.
- ``webhook``: Raw JSON POST to a caller-supplied URL (no credential
  needed — the ``recipient`` argument is the webhook URL).

The tool is constructed per chat turn in :func:`get_toolkit` with the
request-scoped ``user_id`` and the app-level ``storage`` reference, the
same injection pattern used by the schedule tools. Credentials are read
fresh from storage on every call so newly-added credentials take effect
immediately. All failures are returned as error tool results; the tool
never raises.
"""
from typing import Any, Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from skpl_agent.message import TextBlock, ToolResultState
from skpl_agent.permission import PermissionBehavior, PermissionContext, PermissionDecision
from skpl_agent.tool import ToolBase, ToolChunk

from .._service._notification import NotificationService

if TYPE_CHECKING:
    from ..storage import StorageBase
    from ...credential import CredentialBase


class _SendNotificationParams(BaseModel):
    """The params for the send-notification tool."""

    channel: Literal['whatsapp', 'email', 'webhook'] = Field(
        description="Notification channel: 'whatsapp' (WhatsApp Cloud API), 'email' (SMTP), or 'webhook' (JSON POST to a URL).",
    )
    message: str = Field(description='The message body to send.')
    recipient: str = Field(
        default='',
        description="Recipient override. Empty uses the credential's default recipient. For 'webhook' this is REQUIRED and must be the webhook URL.",
    )
    subject: str = Field(default='SKPL Agent 通知', description="Email subject (only used for the 'email' channel).")


class SendNotification(ToolBase):
    """Send a notification to the user via WhatsApp, email, or webhook."""

    name: str = 'SendNotification'
    description: str = (
        "Send a notification message to the user through an external channel. "
        "Channels: 'whatsapp' (WhatsApp Cloud API, requires a configured WhatsApp credential), "
        "'email' (SMTP, requires a configured SMTP credential), or "
        "'webhook' (POST JSON to a URL you provide as `recipient`). "
        "When `recipient` is empty, the default recipient stored on the credential is used. "
        "Use this when the user asks to be notified on WhatsApp / by email, or when a long-running "
        "or scheduled task should report its result proactively."
    )
    input_schema: dict[str, Any] = _SendNotificationParams.model_json_schema()
    is_concurrency_safe: bool = True
    is_read_only: bool = False
    is_state_injected: bool = False
    is_external_tool: bool = False
    is_mcp: bool = False
    mcp_name: str | None = None

    def __init__(self, storage: 'StorageBase', user_id: str) -> None:
        """Initialize the send-notification tool.

        Args:
            storage (`StorageBase`):
                The storage backend used to resolve the caller's
                notification credentials at call time.
            user_id (`str`):
                The authenticated user who owns the credentials.
        """
        super().__init__()
        self._storage = storage
        self._user_id = user_id

    async def check_permissions(self, tool_input: dict[str, Any], context: PermissionContext) -> PermissionDecision:
        """Always allow — sending a notification is a low-risk outbound
        operation gated by credential availability."""
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message=f'{self.name} is always allowed to be called.',
        )

    async def _find_credential(self, cred_type: str) -> 'CredentialBase | None':
        """Return the caller's first credential of the given type, or None.

        Args:
            cred_type (`str`):
                The credential ``type`` discriminator value, e.g.
                ``'whatsapp_credential'``.

        Returns:
            `CredentialBase | None`:
                The typed credential instance, or ``None`` when the user
                has no (parseable) credential of that type.
        """
        from ...credential import CredentialFactory
        records = await self._storage.list_credentials(self._user_id)
        for record in records:
            data = getattr(record, 'data', None) or {}
            if data.get('type') != cred_type:
                continue
            try:
                return CredentialFactory.from_dict(data)
            except Exception:
                continue
        return None

    async def call(self, channel: Literal['whatsapp', 'email', 'webhook'], message: str, recipient: str = '', subject: str = 'SKPL Agent 通知') -> ToolChunk:
        """Send a notification.

        Args:
            channel (`Literal['whatsapp', 'email', 'webhook']`):
                The delivery channel.
            message (`str`):
                The message body.
            recipient (`str`, optional):
                Recipient override; defaults to the credential's default
                recipient. Required for ``webhook`` (the URL).
            subject (`str`, optional):
                Email subject line.

        Returns:
            `ToolChunk`: Success or error result with a detail message.
        """
        try:
            if channel == 'whatsapp':
                cred = await self._find_credential('whatsapp_credential')
                if cred is None:
                    return self._error("No WhatsApp credential configured. Ask the user to add a 'WhatsApp Cloud API' credential first.")
                to = recipient or cred.default_recipient
                if not to:
                    return self._error('No recipient given and the WhatsApp credential has no default_recipient.')
                ok, detail = await NotificationService.send_whatsapp(
                    phone_number_id=cred.phone_number_id,
                    access_token=cred.access_token.get_secret_value(),
                    api_version=cred.api_version,
                    to=to,
                    text=message,
                )
            elif channel == 'email':
                cred = await self._find_credential('smtp_credential')
                if cred is None:
                    return self._error("No SMTP credential configured. Ask the user to add an 'SMTP Email' credential first.")
                to = recipient or cred.default_to
                if not to:
                    return self._error('No recipient given and the SMTP credential has no default_to.')
                ok, detail = await NotificationService.send_email_smtp(
                    host=cred.host,
                    port=cred.port,
                    username=cred.username,
                    password=cred.password.get_secret_value(),
                    from_addr=cred.from_addr,
                    to=to,
                    subject=subject,
                    body=message,
                    use_tls=cred.use_tls,
                )
            else:  # webhook
                url = recipient
                if not url:
                    return self._error("The 'webhook' channel requires `recipient` to be the webhook URL.")
                ok, detail = await NotificationService.send_webhook(
                    url,
                    {'subject': subject, 'text': message, 'source': 'skpl-agent'},
                )
        except Exception as e:
            return self._error(f'{channel} notification failed: {e}')
        if ok:
            return ToolChunk(content=[TextBlock(text=f'Notification sent via {channel}: {detail}')], state=ToolResultState.SUCCESS)
        return self._error(f'{channel} notification failed: {detail}')

    def _error(self, message: str) -> ToolChunk:
        """Build an error tool result."""
        return ToolChunk(content=[TextBlock(text=message)], state=ToolResultState.ERROR)
