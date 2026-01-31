"""
ZPL Handler
===========

Handler for ZPL (Zebra Programming Language) printers.
Works with Zebra, CAB (in ZPL emulation mode), and PrepSafe printers.
"""

import socket
from io import BytesIO
from typing import Dict, Any

from .base import BaseHandler
from ..models import Printer
from ..config import ZPL_PORT, DEFAULT_TIMEOUT


class ZPLHandler(BaseHandler):
    """Handler for ZPL-compatible printers (Zebra, CAB, PrepSafe)."""

    def __init__(self, printer: Printer):
        super().__init__(printer)

    def _get_connection(self) -> tuple:
        """Get host and port for connection."""
        host = self.printer.host
        port = self.printer.port or ZPL_PORT
        return host, port

    def _send_zpl(self, zpl_code: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Send ZPL code to printer."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(zpl_code.encode('utf-8'))
            sock.close()

            return {
                'success': True,
                'host': host,
                'port': port,
                'bytes_sent': len(zpl_code)
            }

        except socket.timeout:
            return {'success': False, 'error': f'Connection timeout to {host}:{port}'}
        except ConnectionRefusedError:
            return {'success': False, 'error': f'Connection refused by {host}:{port}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _image_to_zpl(self, image_data: bytes, width: int = None, height: int = None) -> str:
        """
        Convert image to ZPL GRF format.

        Args:
            image_data: Raw image bytes (PNG/JPEG)
            width: Target width in dots (optional)
            height: Target height in dots (optional)

        Returns:
            ZPL code string
        """
        try:
            from PIL import Image

            # Load and convert to monochrome
            img = Image.open(BytesIO(image_data))

            # Resize if specified
            if width and height:
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            elif width:
                ratio = width / img.width
                img = img.resize((width, int(img.height * ratio)), Image.Resampling.LANCZOS)

            # Convert to 1-bit
            img = img.convert('1')

            # Get dimensions
            w, h = img.size
            bytes_per_row = (w + 7) // 8

            # Convert to hex
            hex_data = []
            for y in range(h):
                row_bytes = []
                for x_byte in range(bytes_per_row):
                    byte = 0
                    for bit in range(8):
                        x = x_byte * 8 + bit
                        if x < w:
                            pixel = img.getpixel((x, y))
                            if pixel == 0:  # Black pixel
                                byte |= (1 << (7 - bit))
                    row_bytes.append(byte)
                hex_data.append(''.join(f'{b:02X}' for b in row_bytes))

            total_bytes = bytes_per_row * h
            hex_string = ''.join(hex_data)

            # Build ZPL
            zpl = f"""^XA
^FO0,0
^GFA,{total_bytes},{total_bytes},{bytes_per_row},
{hex_string}
^FS
^XZ"""

            return zpl

        except ImportError:
            raise ImportError("PIL/Pillow required for image conversion")

    def print_image(self, image_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        Print an image via ZPL.

        Args:
            image_data: Raw image bytes (PNG/JPEG)
            width: Target width in dots (optional)
            height: Target height in dots (optional)

        Returns:
            Dict with success status
        """
        try:
            width = kwargs.get('width')
            height = kwargs.get('height')

            zpl = self._image_to_zpl(image_data, width, height)
            result = self._send_zpl(zpl)

            if result['success']:
                result['format'] = 'zpl_grf'

            return result

        except ImportError as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def print_text(self, text: str, font_size: int = 30, x: int = 20, y: int = 20) -> Dict[str, Any]:
        """
        Print text label.

        Args:
            text: Text to print
            font_size: Font size in dots
            x: X position
            y: Y position

        Returns:
            Dict with success status
        """
        zpl = f"""^XA
^FO{x},{y}
^A0N,{font_size},{font_size}
^FD{text}^FS
^XZ"""

        return self._send_zpl(zpl)

    def print_barcode(self, data: str, barcode_type: str = 'C128',
                      x: int = 20, y: int = 20, height: int = 100) -> Dict[str, Any]:
        """
        Print barcode.

        Args:
            data: Barcode data
            barcode_type: Barcode type (C128, C39, QR, etc.)
            x: X position
            y: Y position
            height: Barcode height

        Returns:
            Dict with success status
        """
        if barcode_type == 'QR':
            zpl = f"""^XA
^FO{x},{y}
^BQN,2,5
^FDQA,{data}^FS
^XZ"""
        else:
            zpl = f"""^XA
^FO{x},{y}
^BY2
^B{barcode_type[0]}N,{height},Y,N,N
^FD{data}^FS
^XZ"""

        return self._send_zpl(zpl)

    def get_status(self) -> Dict[str, Any]:
        """Get printer status via ~HS command."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(DEFAULT_TIMEOUT)
            sock.connect((host, port))

            # Send host status command
            sock.send(b'~HS')

            # Read response
            response = sock.recv(1024).decode('utf-8', errors='ignore')
            sock.close()

            # Parse response (ZPL format: <STX>...<ETX>)
            status = 'unknown'
            if response:
                # Basic parsing - adapt based on printer model
                if 'PAUSE' in response.upper():
                    status = 'paused'
                elif 'HEAD OPEN' in response.upper():
                    status = 'error_head_open'
                elif 'RIBBON OUT' in response.upper():
                    status = 'error_ribbon'
                elif 'PAPER OUT' in response.upper():
                    status = 'error_paper'
                else:
                    status = 'ready'

            return {
                'success': True,
                'host': host,
                'port': port,
                'status': status,
                'raw_response': response[:200] if response else None
            }

        except socket.timeout:
            return {'success': False, 'error': 'Status query timeout', 'status': 'offline'}
        except ConnectionRefusedError:
            return {'success': False, 'error': 'Connection refused', 'status': 'offline'}
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

    def get_printer_info(self) -> Dict[str, Any]:
        """Get printer identification via ~HI command."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(DEFAULT_TIMEOUT)
            sock.connect((host, port))
            sock.send(b'~HI')
            response = sock.recv(1024).decode('utf-8', errors='ignore')
            sock.close()

            return {
                'success': True,
                'host': host,
                'port': port,
                'info': response.strip() if response else None
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}
