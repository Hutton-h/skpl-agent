"""Notification service: WhatsApp Cloud API, SMTP email, and webhooks.

All methods are static, never raise, and return ``(ok, detail)`` tuples so
callers (agent tools, routers) can surface failures directly to the user.
``httpx`` is imported lazily inside each method so importing this module
never fails in environments where httpx is unavailable.
"""
import asyncio
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class NotificationService:
    """Static helper methods for outbound notifications."""

    @staticmethod
    async def send_whatsapp(phone_number_id: str, access_token: str, api_version: str, to: str, text: str) -> tuple[bool, str]:
        """Send a WhatsApp text message via the Meta Graph Cloud API.

        Args:
            phone_number_id (`str`):
                The WhatsApp Business phone number ID.
            access_token (`str`):
                The Meta permanent access token (plaintext).
            api_version (`str`):
                The Graph API version, e.g. ``'v21.0'``.
            to (`str`):
                Recipient phone number in international format.
            text (`str`):
                The message body.

        Returns:
            `tuple[bool, str]`: ``(ok, detail)`` — never raises.
        """
        try:
            import httpx
            url = f'https://graph.facebook.com/{api_version}/{phone_number_id}/messages'
            payload = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'text',
                'text': {'body': text},
            }
            headers = {'Authorization': f'Bearer {access_token}'}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
            if resp.is_success:
                return (True, f'WhatsApp message sent to {to} (HTTP {resp.status_code}).')
            return (False, f'WhatsApp API returned HTTP {resp.status_code}: {resp.text[:500]}')
        except Exception as e:
            return (False, str(e))

    @staticmethod
    async def send_email_smtp(host: str, port: int, username: str, password: str, from_addr: str, to: str, subject: str, body: str, use_tls: bool = True) -> tuple[bool, str]:
        """Send an email via SMTP.

        Prefers ``aiosmtplib`` when installed; otherwise falls back to the
        stdlib ``smtplib`` wrapped in :func:`asyncio.to_thread` so the
        event loop is not blocked. With ``use_tls=True`` an implicit-TLS
        connection (``SMTP_SSL``) is used; with ``use_tls=False`` a
        plaintext connection is upgraded via STARTTLS.

        Args:
            host (`str`): SMTP server hostname.
            port (`int`): SMTP server port.
            username (`str`): Login username.
            password (`str`): Login password (plaintext).
            from_addr (`str`): Sender address; falls back to ``username``.
            to (`str`): Recipient address.
            subject (`str`): Email subject.
            body (`str`): Plain-text body.
            use_tls (`bool`): Whether to use implicit TLS.

        Returns:
            `tuple[bool, str]`: ``(ok, detail)`` — never raises.
        """
        try:
            sender = from_addr or username
            try:
                import aiosmtplib
                message = EmailMessage()
                message['From'] = sender
                message['To'] = to
                message['Subject'] = subject
                message.set_content(body)
                await aiosmtplib.send(
                    message,
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    use_tls=use_tls,
                    start_tls=not use_tls,
                    timeout=15.0,
                )
                return (True, f'Email sent to {to} via {host}:{port} (aiosmtplib).')
            except ImportError:
                pass

            def _send_sync() -> None:
                import smtplib
                message = EmailMessage()
                message['From'] = sender
                message['To'] = to
                message['Subject'] = subject
                message.set_content(body)
                if use_tls:
                    with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                        server.login(username, password)
                        server.send_message(message)
                else:
                    with smtplib.SMTP(host, port, timeout=15) as server:
                        server.starttls()
                        server.login(username, password)
                        server.send_message(message)

            await asyncio.to_thread(_send_sync)
            return (True, f'Email sent to {to} via {host}:{port} (smtplib).')
        except Exception as e:
            return (False, str(e))

    @staticmethod
    async def send_webhook(url: str, payload: dict) -> tuple[bool, str]:
        """POST a JSON payload to a webhook URL.

        Args:
            url (`str`): The webhook URL.
            payload (`dict`): The JSON body to post.

        Returns:
            `tuple[bool, str]`: ``(ok, detail)`` — never raises.
        """
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
            if resp.is_success:
                return (True, f'Webhook POST to {url} succeeded (HTTP {resp.status_code}).')
            return (False, f'Webhook POST to {url} returned HTTP {resp.status_code}: {resp.text[:500]}')
        except Exception as e:
            return (False, str(e))
