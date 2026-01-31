"""
Base Handler
============

Abstract base class for printer handlers.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..models import Printer


class BaseHandler(ABC):
    """Abstract base class for printer handlers."""

    def __init__(self, printer: Printer):
        """Initialize handler with printer configuration."""
        self.printer = printer

    @abstractmethod
    def print_image(self, image_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        Print an image.

        Args:
            image_data: Raw image bytes (PNG or JPEG)
            **kwargs: Handler-specific options

        Returns:
            Dict with success status and details
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get printer status.

        Returns:
            Dict with status information
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to printer.

        Returns:
            Dict with connection test results
        """
        pass

    def supports_power_management(self) -> bool:
        """Check if handler supports power management."""
        return False

    def set_sleep_timeout(self, minutes: int) -> Dict[str, Any]:
        """Set sleep timeout (override in handlers that support it)."""
        return {'success': False, 'error': 'Power management not supported'}

    def wake(self) -> Dict[str, Any]:
        """Wake printer from sleep (override in handlers that support it)."""
        return {'success': False, 'error': 'Power management not supported'}

    def reboot(self) -> Dict[str, Any]:
        """Reboot printer (override in handlers that support it)."""
        return {'success': False, 'error': 'Power management not supported'}

    def flash_led(self, duration: int = 5) -> Dict[str, Any]:
        """Flash LED (override in handlers that support it)."""
        return {'success': False, 'error': 'LED flash not supported'}
