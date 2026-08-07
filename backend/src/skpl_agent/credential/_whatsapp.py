"""The WhatsApp Cloud API credential.

Notification-only credential: it does not provide a chat model. The
``get_chat_model_class`` override raises a clear error instead of the
generic base-class ``NotImplementedError`` so misconfigured call sites
(e.g. pointing a ``ChatModelConfig`` at a WhatsApp credential, or querying
``/model`` with ``provider='whatsapp_credential'``) fail with an
actionable message. Raising is deliberate — returning ``None`` would
produce a confusing ``AttributeError: 'NoneType'`` at the two existing
call sites (``app/_router/_model.py`` and ``app/_service/_model.py``),
which both dereference the returned class immediately.
"""
from typing import Literal, Type, TYPE_CHECKING
from pydantic import ConfigDict, Field, SecretStr
from ._base import CredentialBase
if TYPE_CHECKING:
    from ..model import ChatModelBase


class WhatsAppCloudCredential(CredentialBase):
    """The WhatsApp Cloud API credential model."""

    model_config = ConfigDict(title='WhatsApp Cloud API')
    type: Literal['whatsapp_credential'] = 'whatsapp_credential'
    'The credential type.'
    phone_number_id: str = Field(description='The WhatsApp Business phone number ID.')
    'The WhatsApp Business phone number ID.'
    access_token: SecretStr = Field(description='The Meta permanent access token.')
    'The Meta permanent access token.'
    default_recipient: str = Field(default='', description="Default recipient phone number in international format, e.g. '8613800138000'.")
    'The default recipient phone number (international format).'
    api_version: str = Field(default='v21.0', description='The Meta Graph API version.')
    'The Meta Graph API version.'

    @classmethod
    def get_chat_model_class(cls) -> Type['ChatModelBase']:
        """WhatsApp Cloud API is a notification channel, not a chat model
        provider, so there is no chat model class to return."""
        raise NotImplementedError(
            'WhatsAppCloudCredential is a notification-only credential and does not provide a chat model. '
            "Do not use it as a chat model credential or query it via the /model endpoint."
        )
