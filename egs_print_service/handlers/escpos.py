"""
ESC/POS Handler
===============

Handler for ESC/POS thermal printers (Star, Epson).
Uses python-escpos library or direct socket communication.
"""

import socket
from io import BytesIO
from typing import Dict, Any, Optional

from .base import BaseHandler
from ..models import Printer
from ..config import DEFAULT_TIMEOUT


class ESCPOSHandler(BaseHandler):
    """Handler for ESC/POS printers (Star, Epson)."""

    # ESC/POS commands
    ESC = b'\x1b'
    GS = b'\x1d'
    INIT = b'\x1b\x40'  # Initialize printer
    CUT = b'\x1d\x56\x00'  # Full cut
    PARTIAL_CUT = b'\x1d\x56\x01'  # Partial cut
    FEED = b'\x1b\x64'  # Feed lines

    # Text formatting
    BOLD_ON = b'\x1b\x45\x01'
    BOLD_OFF = b'\x1b\x45\x00'
    UNDERLINE_ON = b'\x1b\x2d\x01'
    UNDERLINE_OFF = b'\x1b\x2d\x00'
    DOUBLE_HEIGHT = b'\x1b\x21\x10'
    DOUBLE_WIDTH = b'\x1b\x21\x20'
    NORMAL = b'\x1b\x21\x00'

    # Alignment
    ALIGN_LEFT = b'\x1b\x61\x00'
    ALIGN_CENTER = b'\x1b\x61\x01'
    ALIGN_RIGHT = b'\x1b\x61\x02'

    def __init__(self, printer: Printer):
        super().__init__(printer)
        self._escpos_printer = None

    def _get_connection(self) -> tuple:
        """Get host and port for network connection."""
        host = self.printer.host
        port = self.printer.port or 9100
        return host, port

    def _get_escpos_printer(self):
        """Get python-escpos printer instance."""
        if self._escpos_printer:
            return self._escpos_printer

        try:
            from escpos.printer import Network

            host, port = self._get_connection()
            if host:
                self._escpos_printer = Network(host, port=port)
                return self._escpos_printer

        except ImportError:
            pass

        return None

    def _send_raw(self, data: bytes, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Send raw bytes to printer via socket."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(data)
            sock.close()

            return {
                'success': True,
                'host': host,
                'port': port,
                'bytes_sent': len(data)
            }

        except socket.timeout:
            return {'success': False, 'error': f'Connection timeout to {host}:{port}'}
        except ConnectionRefusedError:
            return {'success': False, 'error': f'Connection refused by {host}:{port}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def print_image(self, image_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        Print an image.

        Args:
            image_data: Raw image bytes (PNG/JPEG)
            width: Max width in pixels (optional)

        Returns:
            Dict with success status
        """
        # Try python-escpos first
        printer = self._get_escpos_printer()
        if printer:
            try:
                from PIL import Image

                img = Image.open(BytesIO(image_data))

                # Resize if needed (typical thermal width: 384 or 576 dots)
                max_width = kwargs.get('width', 384)
                if img.width > max_width:
                    ratio = max_width / img.width
                    img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

                # Print using escpos
                printer.image(img)

                if kwargs.get('cut', True):
                    printer.cut()

                return {
                    'success': True,
                    'method': 'escpos',
                    'size': f'{img.width}x{img.height}'
                }

            except Exception as e:
                return {'success': False, 'error': str(e)}

        # Fallback: Manual ESC/POS image command
        try:
            from PIL import Image

            img = Image.open(BytesIO(image_data))
            img = img.convert('1')  # Convert to 1-bit

            max_width = kwargs.get('width', 384)
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

            # Build ESC/POS raster image command
            data = bytearray()
            data.extend(self.INIT)  # Initialize
            data.extend(self._image_to_escpos(img))

            if kwargs.get('cut', True):
                data.extend(self.FEED + b'\x03')  # Feed 3 lines
                data.extend(self.CUT)

            return self._send_raw(bytes(data))

        except ImportError:
            return {'success': False, 'error': 'PIL/Pillow required for image printing'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _image_to_escpos(self, img) -> bytes:
        """Convert PIL Image to ESC/POS raster format."""
        width, height = img.size
        bytes_per_row = (width + 7) // 8

        # GS v 0 command for raster bit image
        data = bytearray()
        data.extend(b'\x1d\x76\x30\x00')  # GS v 0 m
        data.append(bytes_per_row & 0xff)  # xL
        data.append((bytes_per_row >> 8) & 0xff)  # xH
        data.append(height & 0xff)  # yL
        data.append((height >> 8) & 0xff)  # yH

        # Image data
        for y in range(height):
            for x_byte in range(bytes_per_row):
                byte = 0
                for bit in range(8):
                    x = x_byte * 8 + bit
                    if x < width:
                        pixel = img.getpixel((x, y))
                        if pixel == 0:  # Black pixel
                            byte |= (1 << (7 - bit))
                data.append(byte)

        return bytes(data)

    def print_text(self, text: str, bold: bool = False, size: str = 'normal',
                   align: str = 'left', cut: bool = False) -> Dict[str, Any]:
        """
        Print text.

        Args:
            text: Text to print
            bold: Enable bold
            size: 'normal', 'double_height', 'double_width', 'double'
            align: 'left', 'center', 'right'
            cut: Cut paper after printing

        Returns:
            Dict with success status
        """
        data = bytearray()
        data.extend(self.INIT)

        # Alignment
        if align == 'center':
            data.extend(self.ALIGN_CENTER)
        elif align == 'right':
            data.extend(self.ALIGN_RIGHT)
        else:
            data.extend(self.ALIGN_LEFT)

        # Size
        if size == 'double_height':
            data.extend(self.DOUBLE_HEIGHT)
        elif size == 'double_width':
            data.extend(self.DOUBLE_WIDTH)
        elif size == 'double':
            data.extend(b'\x1b\x21\x30')  # Both
        else:
            data.extend(self.NORMAL)

        # Bold
        if bold:
            data.extend(self.BOLD_ON)

        # Text
        data.extend(text.encode('utf-8', errors='replace'))
        data.extend(b'\n')

        # Reset
        data.extend(self.NORMAL)
        data.extend(self.BOLD_OFF)

        if cut:
            data.extend(self.FEED + b'\x03')
            data.extend(self.CUT)

        return self._send_raw(bytes(data))

    def cut(self, partial: bool = False) -> Dict[str, Any]:
        """Cut paper."""
        if partial:
            return self._send_raw(self.PARTIAL_CUT)
        return self._send_raw(self.CUT)

    def feed(self, lines: int = 3) -> Dict[str, Any]:
        """Feed paper."""
        return self._send_raw(self.FEED + bytes([lines]))

    def get_status(self) -> Dict[str, Any]:
        """Get printer status."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(DEFAULT_TIMEOUT)
            sock.connect((host, port))

            # Request status (DLE EOT n)
            sock.send(b'\x10\x04\x01')  # Paper status
            response = sock.recv(1)

            sock.close()

            if response:
                status_byte = response[0]
                paper_ok = not (status_byte & 0x0c)  # Bits 2,3 indicate paper status

                return {
                    'success': True,
                    'host': host,
                    'port': port,
                    'status': 'ready' if paper_ok else 'paper_low',
                    'paper_ok': paper_ok,
                    'raw_status': status_byte
                }

            return {
                'success': True,
                'status': 'unknown',
                'message': 'No status response'
            }

        except socket.timeout:
            return {'success': False, 'error': 'Status query timeout', 'status': 'offline'}
        except Exception as e:
            return {'success': False, 'error': str(e), 'status': 'error'}

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to printer."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.close()

            return {
                'success': True,
                'host': host,
                'port': port,
                'message': 'TCP connection successful'
            }

        except socket.timeout:
            return {'success': False, 'error': f'Connection timeout to {host}:{port}'}
        except ConnectionRefusedError:
            return {'success': False, 'error': f'Connection refused by {host}:{port}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def open_cash_drawer(self) -> Dict[str, Any]:
        """Open connected cash drawer."""
        # ESC p m t1 t2 - Generate pulse
        return self._send_raw(b'\x1b\x70\x00\x19\xfa')
