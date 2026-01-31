"""
SBPL Handler
============

Handler for SATO printers using SBPL (SATO Barcode Printer Language).
SATO printers also support SZPL (Zebra ZPL emulation) mode.
"""

import socket
from io import BytesIO
from typing import Dict, Any

from .base import BaseHandler
from ..models import Printer
from ..config import DEFAULT_TIMEOUT


class SBPLHandler(BaseHandler):
    """Handler for SATO printers using SBPL."""

    # SBPL Control Codes
    STX = b'\x02'  # Start of text
    ETX = b'\x03'  # End of text
    ESC = b'\x1b'

    def __init__(self, printer: Printer):
        super().__init__(printer)

    def _get_connection(self) -> tuple:
        """Get host and port for connection."""
        host = self.printer.host
        port = self.printer.port or 9100
        return host, port

    def _send_sbpl(self, commands: bytes, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Send SBPL commands to printer."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(commands)
            sock.close()

            return {
                'success': True,
                'host': host,
                'port': port,
                'bytes_sent': len(commands)
            }

        except socket.timeout:
            return {'success': False, 'error': f'Connection timeout to {host}:{port}'}
        except ConnectionRefusedError:
            return {'success': False, 'error': f'Connection refused by {host}:{port}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _build_sbpl_label(self, commands: list) -> bytes:
        """
        Build SBPL label command sequence.

        Args:
            commands: List of SBPL command strings

        Returns:
            Complete SBPL command bytes
        """
        data = bytearray()
        data.extend(self.STX)
        data.extend(self.ESC + b'A')  # Start of label format

        for cmd in commands:
            if isinstance(cmd, str):
                data.extend(cmd.encode('utf-8'))
            else:
                data.extend(cmd)

        data.extend(self.ESC + b'Z')  # End of label format
        data.extend(self.ETX)

        return bytes(data)

    def print_image(self, image_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        Print an image.

        Args:
            image_data: Raw image bytes (PNG/JPEG)
            x: X position in dots
            y: Y position in dots

        Returns:
            Dict with success status
        """
        try:
            from PIL import Image

            img = Image.open(BytesIO(image_data))
            img = img.convert('1')  # Convert to 1-bit

            x = kwargs.get('x', 0)
            y = kwargs.get('y', 0)

            # Build SBPL graphic command
            commands = []

            # Set position
            commands.append(f'H{x:04d}')  # Horizontal position
            commands.append(f'V{y:04d}')  # Vertical position

            # Graphic data command
            width, height = img.size
            bytes_per_row = (width + 7) // 8

            # GM command for graphic memory
            commands.append(f'GM{bytes_per_row:03d}{height:04d}')

            # Convert image to hex
            hex_data = []
            for row_y in range(height):
                for x_byte in range(bytes_per_row):
                    byte = 0
                    for bit in range(8):
                        px = x_byte * 8 + bit
                        if px < width:
                            pixel = img.getpixel((px, row_y))
                            if pixel == 0:  # Black
                                byte |= (1 << (7 - bit))
                    hex_data.append(f'{byte:02X}')

            commands.append(''.join(hex_data))

            # Print command
            commands.append('Q1')  # Print 1 label

            sbpl = self._build_sbpl_label(commands)
            result = self._send_sbpl(sbpl)

            if result['success']:
                result['format'] = 'sbpl_graphic'
                result['size'] = f'{width}x{height}'

            return result

        except ImportError:
            return {'success': False, 'error': 'PIL/Pillow required for image printing'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def print_text(self, text: str, x: int = 100, y: int = 100,
                   font: str = 'A', size: int = 1) -> Dict[str, Any]:
        """
        Print text label.

        Args:
            text: Text to print
            x: X position in dots
            y: Y position in dots
            font: Font name (A, B, C, etc.)
            size: Font size multiplier

        Returns:
            Dict with success status
        """
        commands = [
            f'H{x:04d}',  # Horizontal position
            f'V{y:04d}',  # Vertical position
            f'P{size}',   # Pitch/size
            f'${font}',   # Font selection
            text,         # Text data
            'Q1',         # Print 1 label
        ]

        sbpl = self._build_sbpl_label(commands)
        return self._send_sbpl(sbpl)

    def print_barcode(self, data: str, barcode_type: str = 'C128',
                      x: int = 100, y: int = 100, height: int = 100) -> Dict[str, Any]:
        """
        Print barcode.

        Args:
            data: Barcode data
            barcode_type: Barcode type (C128, C39, EAN13, QR, etc.)
            x: X position
            y: Y position
            height: Barcode height

        Returns:
            Dict with success status
        """
        # SBPL barcode type mapping
        type_map = {
            'C128': 'K',   # Code 128
            'C39': '3',    # Code 39
            'EAN13': 'E',  # EAN-13
            'EAN8': 'e',   # EAN-8
            'UPCA': 'U',   # UPC-A
            'ITF': 'I',    # Interleaved 2 of 5
            'QR': 'Q',     # QR Code
        }

        bc_type = type_map.get(barcode_type.upper(), 'K')

        if bc_type == 'Q':  # QR Code
            commands = [
                f'H{x:04d}',
                f'V{y:04d}',
                f'2D30,{len(data):04d},{data}',  # QR Code command
                'Q1',
            ]
        else:
            commands = [
                f'H{x:04d}',
                f'V{y:04d}',
                f'B{bc_type}{height:03d}*{data}*',  # Barcode command
                'Q1',
            ]

        sbpl = self._build_sbpl_label(commands)
        return self._send_sbpl(sbpl)

    def get_status(self) -> Dict[str, Any]:
        """Get printer status."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(DEFAULT_TIMEOUT)
            sock.connect((host, port))

            # SBPL status request command
            status_cmd = self.STX + self.ESC + b'S' + self.ETX
            sock.send(status_cmd)

            response = sock.recv(256)
            sock.close()

            # Parse response
            status = 'unknown'
            if response:
                # SBPL status response parsing
                if b'READY' in response.upper() or response == b'\x06':  # ACK
                    status = 'ready'
                elif b'PAUSE' in response.upper():
                    status = 'paused'
                elif b'ERROR' in response.upper():
                    status = 'error'
                elif b'PAPER' in response.upper():
                    status = 'paper_error'

            return {
                'success': True,
                'host': host,
                'port': port,
                'status': status,
                'raw_response': response.hex() if response else None
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

    def use_zpl_mode(self) -> bool:
        """
        Check if this SATO printer should use ZPL emulation.
        Returns True if configured for SZPL mode.
        """
        # Could be configured per-printer
        return getattr(self.printer, 'use_zpl_emulation', False)
