"""The SMTP email credential.

Notification-only credential: see ``_whatsapp.py`` for why
``get_chat_model_class`` raises instead of returning ``None``.
"""
from typing import Literal, Type, TYPE_CHECKING
from pydantic import ConfigDict, Field, SecretStr
from ._base import CredentialBase
if TYPE_CHECKING:
    from ..model import ChatModelBase


class SMTPCredential(CredentialBase):
    """The SMTP email credential model."""

    model_config = ConfigDict(title='SMTP Email')
    type: Literal['smtp_credential'] = 'smtp_credential'
    'The credential type.'
    host: str = Field(description='The SMTP server hostname.')
    'The SMTP server hostname.'
    port: int = Field(default=465, description='The SMTP server port (465 for SSL, 587 for STARTTLS).')
    'The SMTP server port.'
    username: str = Field(description='The SMTP login username.')
    'The SMTP login username.'
    password: SecretStr = Field(description='The SMTP login password or app-specific password.')
    'The SMTP login password.'
    from_addr: str = Field(default='', description='The sender address. Defaults to the username when empty.')
    'The sender address.'
    use_tls: bool = Field(default=True, description='Use implicit TLS (SMTP_SSL). When False, connect in plaintext and upgrade via STARTTLS.')
    'Whether to use implicit TLS.'
    default_to: str = Field(default='', description='The default recipient email address.')
    'The default recipient email address.'

    @classmethod
    def get_chat_model_class(cls) -> Type['ChatModelBase']:
        """SMTP is a notification channel, not a chat model provider, so
        there is no chat model class to return."""
        raise NotImplementedError(
            'SMTPCredential is a notification-only credential and does not provide a chat model. '
            "Do not use it as a chat model credential or query it via the /model endpoint."
        )
