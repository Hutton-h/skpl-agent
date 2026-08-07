"""Notification router — channel discovery and test-send endpoints."""
import logging
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..deps import get_current_user_id, get_storage
from ..storage import StorageBase
from .._service._notification import NotificationService
from ...credential import CredentialFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/notification', tags=['notification'], responses={404: {'description': 'Not found'}})


class NotificationChannelsResponse(BaseModel):
    """Which notification channels the current user has configured."""

    whatsapp: bool = Field(description='True when the user has at least one WhatsApp Cloud API credential.')
    email: bool = Field(description='True when the user has at least one SMTP credential.')


class TestNotificationRequest(BaseModel):
    """The test-notification request body."""

    channel: Literal['whatsapp', 'email', 'webhook'] = Field(description='The channel to send the test message through.')
    recipient: str = Field(default='', description="Recipient override; empty uses the credential's default. Required for 'webhook' (the URL).")
    message: str = Field(default='SKPL Agent 测试通知', description='The test message body.')


class TestNotificationResponse(BaseModel):
    """The test-notification result."""

    ok: bool = Field(description='Whether the message was sent successfully.')
    detail: str = Field(description='Human-readable success or error detail.')


async def _user_credential_types(storage: StorageBase, user_id: str) -> set[str]:
    """Return the set of credential ``type`` values the user has stored."""
    types: set[str] = set()
    for record in await storage.list_credentials(user_id):
        data = getattr(record, 'data', None) or {}
        cred_type = data.get('type')
        if isinstance(cred_type, str):
            types.add(cred_type)
    return types


async def _find_credential(storage: StorageBase, user_id: str, cred_type: str):
    """Return the user's first credential of the given type, or None."""
    for record in await storage.list_credentials(user_id):
        data = getattr(record, 'data', None) or {}
        if data.get('type') != cred_type:
            continue
        try:
            return CredentialFactory.from_dict(data)
        except Exception:
            logger.warning('Skipping unparseable %s credential %s', cred_type, getattr(record, 'id', '?'))
            continue
    return None


@router.get('/channels', response_model=NotificationChannelsResponse, summary='List configured notification channels')
async def list_channels(user_id: str = Depends(get_current_user_id), storage: StorageBase = Depends(get_storage)) -> NotificationChannelsResponse:
    """Return which notification channels the current user has configured,
    based on the presence of the corresponding credential types.

    Args:
        user_id (`str`): Injected authenticated user ID.
        storage (`StorageBase`): Injected storage backend.

    Returns:
        `NotificationChannelsResponse`: Channel availability flags.
    """
    types = await _user_credential_types(storage, user_id)
    return NotificationChannelsResponse(
        whatsapp='whatsapp_credential' in types,
        email='smtp_credential' in types,
    )


@router.post('/test', response_model=TestNotificationResponse, summary='Send a test notification')
async def send_test(body: TestNotificationRequest, user_id: str = Depends(get_current_user_id), storage: StorageBase = Depends(get_storage)) -> TestNotificationResponse:
    """Send a test message through the given channel using the current
    user's stored credential.

    Args:
        body (`TestNotificationRequest`): Channel, recipient, and message.
        user_id (`str`): Injected authenticated user ID.
        storage (`StorageBase`): Injected storage backend.

    Returns:
        `TestNotificationResponse`: ``ok`` plus a detail message. Delivery
            failures are reported in the body rather than as HTTP errors so
            the frontend can display them directly.
    """
    ok: bool
    detail: str
    if body.channel == 'whatsapp':
        cred = await _find_credential(storage, user_id, 'whatsapp_credential')
        if cred is None:
            return TestNotificationResponse(ok=False, detail="No WhatsApp credential configured. Add a 'WhatsApp Cloud API' credential first.")
        to = body.recipient or cred.default_recipient
        if not to:
            return TestNotificationResponse(ok=False, detail='No recipient given and the WhatsApp credential has no default_recipient.')
        ok, detail = await NotificationService.send_whatsapp(
            phone_number_id=cred.phone_number_id,
            access_token=cred.access_token.get_secret_value(),
            api_version=cred.api_version,
            to=to,
            text=body.message,
        )
    elif body.channel == 'email':
        cred = await _find_credential(storage, user_id, 'smtp_credential')
        if cred is None:
            return TestNotificationResponse(ok=False, detail="No SMTP credential configured. Add an 'SMTP Email' credential first.")
        to = body.recipient or cred.default_to
        if not to:
            return TestNotificationResponse(ok=False, detail='No recipient given and the SMTP credential has no default_to.')
        ok, detail = await NotificationService.send_email_smtp(
            host=cred.host,
            port=cred.port,
            username=cred.username,
            password=cred.password.get_secret_value(),
            from_addr=cred.from_addr,
            to=to,
            subject='SKPL Agent 通知',
            body=body.message,
            use_tls=cred.use_tls,
        )
    else:  # webhook
        if not body.recipient:
            return TestNotificationResponse(ok=False, detail="The 'webhook' channel requires `recipient` to be the webhook URL.")
        ok, detail = await NotificationService.send_webhook(
            body.recipient,
            {'subject': 'SKPL Agent 通知', 'text': body.message, 'source': 'skpl-agent'},
        )
    return TestNotificationResponse(ok=ok, detail=detail)
