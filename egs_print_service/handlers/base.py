"""
Base Handler
============

Abstract base class for printer handlers.

Defines the standard feature set that all printer handlers can implement.
Each handler declares its capabilities via `get_capabilities()`, and the
API layer uses this to route requests and show available features in the UI.

Standard features (handler returns not-supported by default — override to enable):
  - print_raw       — send raw command string (ZPL, TSPL, ESC/POS, SBPL)
  - print_image     — send image data (PNG/JPEG → converted to printer format)
  - get_status      — query printer status (ready, paper out, head open, etc.)
  - test_connection  — verify printer is reachable
  - get_info        — firmware version, memory, mileage
  - list_files      — list files in printer flash (fonts, images, forms)
  - delete_file     — delete a file from printer flash
  - upload_font     — upload TTF font to printer flash
  - selftest        — print self-test page
  - calibrate       — auto-detect gap/label size
  - feed            — feed labels
  - set_label_size  — configure label dimensions
  - power management — sleep, wake, reboot (Evolis)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..models import Printer


class BaseHandler(ABC):
    """Abstract base class for printer handlers.

    Subclasses override methods to enable features. The default implementation
    returns {'success': False, 'error': '... not supported'} for optional features.
    """

    def __init__(self, printer: Printer):
        """Initialize handler with printer configuration."""
        self.printer = printer

    # =========================================================================
    # Capabilities — override to declare what this handler supports
    # =========================================================================

    def get_capabilities(self) -> Dict[str, bool]:
        """
        Return a dict of feature_name → supported (bool).

        The API layer calls this to discover what a printer can do.
        Default: only print_image, get_status, test_connection are required.
        """
        return {
            'print_raw': hasattr(self, '_send_raw') or hasattr(self, '_send_zpl'),
            'print_image': True,  # abstract — must be implemented
            'get_status': True,   # abstract — must be implemented
            'test_connection': True,  # abstract — must be implemented
            'get_info': self._has_override('get_info'),
            'list_files': self._has_override('list_files'),
            'delete_file': self._has_override('delete_file'),
            'upload_font': self._has_override('download_font'),
            'selftest': self._has_override('selftest'),
            'calibrate': self._has_override('calibrate'),
            'feed': self._has_override('feed'),
            'set_label_size': self._has_override('set_label_size'),
            'power_management': self.supports_power_management(),
        }

    def _has_override(self, method_name: str) -> bool:
        """Check if a method is overridden from BaseHandler's default."""
        if not hasattr(self, method_name):
            return False
        own_method = getattr(type(self), method_name, None)
        base_method = getattr(BaseHandler, method_name, None)
        return own_method is not base_method

    # =========================================================================
    # Required features (abstract — every handler must implement)
    # =========================================================================

    @abstractmethod
    def print_image(self, image_data: bytes, **kwargs) -> Dict[str, Any]:
        """Print an image (PNG/JPEG → converted to printer format)."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get printer status (ready, paper_out, head_open, etc.)."""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to printer (USB, TCP, or BLE)."""
        pass

    # =========================================================================
    # Optional features — override in handlers that support them
    # =========================================================================

    def get_info(self) -> Dict[str, Any]:
        """Get printer info: firmware version, memory, mileage."""
        return {'success': False, 'error': 'Not supported for this printer type'}

    def list_files(self) -> Dict[str, Any]:
        """List files in printer flash memory (fonts, images, forms)."""
        return {'success': False, 'error': 'Not supported for this printer type'}

    def delete_file(self, filename: str) -> Dict[str, Any]:
        """Delete a file from printer flash memory."""
        return {'success': False, 'error': 'Not supported for this printer type'}

    def download_font(self, font_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload/download a TTF font to printer flash memory."""
        return {'success': False, 'error': 'Not supported for this printer type'}

    def selftest(self) -> Dict[str, Any]:
        """Print a self-test page showing all printer settings."""
        return {'success': False, 'error': 'Not supported for this printer type'}

    def calibrate(self) -> Dict[str, Any]:
        """Run automatic label calibration (feeds labels to detect gap)."""
        return {'success': False, 'error': 'Not supported for this printer type'}

    def feed(self, count: int = 1) -> Dict[str, Any]:
        """Feed one or more labels."""
        return {'success': False, 'error': 'Not supported for this printer type'}

    def set_label_size(self, width_mm: int, height_mm: int, gap_mm: int = 2) -> Dict[str, Any]:
        """Configure label dimensions."""
        return {'success': False, 'error': 'Not supported for this printer type'}

    # =========================================================================
    # Power management — override in handlers that support it (e.g. Evolis)
    # =========================================================================

    def supports_power_management(self) -> bool:
        """Check if handler supports power management."""
        return False

    def set_sleep_timeout(self, minutes: int) -> Dict[str, Any]:
        """Set sleep timeout."""
        return {'success': False, 'error': 'Power management not supported'}

    def wake(self) -> Dict[str, Any]:
        """Wake printer from sleep."""
        return {'success': False, 'error': 'Power management not supported'}

    def reboot(self) -> Dict[str, Any]:
        """Reboot printer."""
        return {'success': False, 'error': 'Power management not supported'}

    def flash_led(self, duration: int = 5) -> Dict[str, Any]:
        """Flash LED for identification."""
        return {'success': False, 'error': 'LED flash not supported'}
