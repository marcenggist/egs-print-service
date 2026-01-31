"""
EGS Print Service Handlers
==========================

Protocol handlers for different printer types.
"""

from .base import BaseHandler
from .evolis import EvolisHandler
from .zpl import ZPLHandler
from .escpos import ESCPOSHandler
from .sbpl import SBPLHandler
from .tspl import TSPLHandler

__all__ = ['BaseHandler', 'EvolisHandler', 'ZPLHandler', 'ESCPOSHandler', 'SBPLHandler', 'TSPLHandler']

# Handler registry
HANDLERS = {
    'evolis': EvolisHandler,
    'zpl': ZPLHandler,
    'escpos': ESCPOSHandler,
    'sbpl': SBPLHandler,
    'tspl': TSPLHandler,
}


def get_handler(handler_type: str) -> type:
    """Get handler class by type."""
    return HANDLERS.get(handler_type)
