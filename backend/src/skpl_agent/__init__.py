"""The skpl_agent package."""
import warnings
from ._logging import logger, setup_logger
from ._utils._common import set_id_factory
from ._version import __version__
warnings.filterwarnings('once', category=DeprecationWarning)
__all__ = ['logger', 'setup_logger', 'set_id_factory', '__version__']