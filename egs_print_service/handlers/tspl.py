"""
TSPL Handler
============

Handler for TSPL/TSPL2 printers (Gainsha/Gprinter, TSC, PrepSafe).

TSPL (TSC Printer Language) is used by many thermal label printers including:
- Gainsha/Gprinter: GS-2208, GS-2406T, GS-2408D, etc.
- TSC: All models
- PrepSafe: Food safety label printers (Gainsha OEM)

Protocol Reference:
- TSPL/TSPL2 Programming Manual: https://www.tscprinters.com/cms/upload/download_en/TSPL_TSPL2_Programming.pdf
- Network port: 9100 (default)
- USB: Via Windows drivers or direct USB

Key Commands:
- SIZE w,h          - Label size in mm
- GAP g,o           - Gap between labels
- SPEED n           - Print speed (1-15)
- DENSITY n         - Print darkness (0-15)
- DIRECTION n,m     - Print direction
- CLS               - Clear image buffer
- TEXT x,y,...      - Print text
- BARCODE x,y,...   - Print barcode
- BITMAP x,y,...    - Print bitmap
- PRINT m,n         - Print labels
"""

import socket
from io import BytesIO
from typing import Dict, Any, List

from .base import BaseHandler
from ..models import Printer
from ..config import DEFAULT_TIMEOUT


class TSPLHandler(BaseHandler):
    """Handler for TSPL/TSPL2 printers (Gainsha, TSC, PrepSafe)."""

    # Default settings
    DEFAULT_PORT = 9100
    DEFAULT_SPEED = 4
    DEFAULT_DENSITY = 8

    def __init__(self, printer: Printer):
        super().__init__(printer)

    def _get_connection(self) -> tuple:
        """Get host and port for connection."""
        host = self.printer.host
        port = self.printer.port or self.DEFAULT_PORT
        return host, port

    def _send_tspl(self, commands: List[str], timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """
        Send TSPL commands to printer.

        Args:
            commands: List of TSPL command strings
            timeout: Connection timeout

        Returns:
            Dict with success status
        """
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        # Build command string (commands separated by newlines)
        command_str = '\r\n'.join(commands) + '\r\n'

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(command_str.encode('utf-8'))
            sock.close()

            return {
                'success': True,
                'host': host,
                'port': port,
                'bytes_sent': len(command_str),
                'commands': len(commands)
            }

        except socket.timeout:
            return {'success': False, 'error': f'Connection timeout to {host}:{port}'}
        except ConnectionRefusedError:
            return {'success': False, 'error': f'Connection refused by {host}:{port}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _image_to_tspl_bitmap(self, image_data: bytes, x: int = 0, y: int = 0) -> List[str]:
        """
        Convert image to TSPL BITMAP command.

        BITMAP command format:
        BITMAP x,y,width,height,mode,data

        Args:
            image_data: Raw image bytes (PNG/JPEG)
            x: X position in dots
            y: Y position in dots

        Returns:
            List of TSPL commands
        """
        try:
            from PIL import Image

            # Load and convert to 1-bit
            img = Image.open(BytesIO(image_data))
            img = img.convert('1')

            width, height = img.size
            bytes_per_row = (width + 7) // 8

            # Build bitmap data (MSB first)
            bitmap_data = []
            for row_y in range(height):
                for x_byte in range(bytes_per_row):
                    byte = 0
                    for bit in range(8):
                        px = x_byte * 8 + bit
                        if px < width:
                            pixel = img.getpixel((px, row_y))
                            if pixel == 0:  # Black pixel = 1
                                byte |= (1 << (7 - bit))
                    bitmap_data.append(byte)

            # Convert to hex string
            hex_data = ''.join(f'{b:02X}' for b in bitmap_data)

            # BITMAP x,y,width_bytes,height,mode,data
            # mode 0 = overwrite, mode 1 = OR, mode 2 = XOR
            return [f'BITMAP {x},{y},{bytes_per_row},{height},0,{hex_data}']

        except ImportError:
            raise ImportError("PIL/Pillow required for image conversion")

    def print_image(self, image_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        Print an image via TSPL.

        Args:
            image_data: Raw image bytes (PNG/JPEG)
            label_width: Label width in mm (default 50)
            label_height: Label height in mm (default 30)
            gap: Gap between labels in mm (default 2)
            x: X position in dots (default 0)
            y: Y position in dots (default 0)

        Returns:
            Dict with success status
        """
        try:
            label_width = kwargs.get('label_width', 50)
            label_height = kwargs.get('label_height', 30)
            gap = kwargs.get('gap', 2)
            x = kwargs.get('x', 0)
            y = kwargs.get('y', 0)
            copies = kwargs.get('copies', 1)

            commands = [
                f'SIZE {label_width} mm,{label_height} mm',
                f'GAP {gap} mm,0 mm',
                f'SPEED {self.DEFAULT_SPEED}',
                f'DENSITY {self.DEFAULT_DENSITY}',
                'DIRECTION 1,0',
                'CLS',
            ]

            # Add bitmap
            bitmap_cmd = self._image_to_tspl_bitmap(image_data, x, y)
            commands.extend(bitmap_cmd)

            # Print
            commands.append(f'PRINT 1,{copies}')

            result = self._send_tspl(commands)

            if result['success']:
                result['format'] = 'tspl_bitmap'
                result['label_size'] = f'{label_width}x{label_height}mm'

            return result

        except ImportError as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def print_text(self, text: str, x: int = 100, y: int = 100,
                   font: str = '3', rotation: int = 0,
                   x_mult: int = 1, y_mult: int = 1) -> Dict[str, Any]:
        """
        Print text label.

        Args:
            text: Text to print
            x: X position in dots
            y: Y position in dots
            font: Font number (1-8 for internal, or font name)
            rotation: Rotation (0, 90, 180, 270)
            x_mult: X magnification (1-10)
            y_mult: Y magnification (1-10)

        Returns:
            Dict with success status
        """
        # TEXT x,y,"font",rotation,x_multiplication,y_multiplication,"content"
        commands = [
            'SIZE 50 mm,30 mm',
            'GAP 2 mm,0 mm',
            'CLS',
            f'TEXT {x},{y},"{font}",{rotation},{x_mult},{y_mult},"{text}"',
            'PRINT 1,1',
        ]

        return self._send_tspl(commands)

    def print_barcode(self, data: str, barcode_type: str = '128',
                      x: int = 100, y: int = 100, height: int = 100,
                      readable: int = 1) -> Dict[str, Any]:
        """
        Print barcode.

        Args:
            data: Barcode data
            barcode_type: Type (128, 39, EAN13, UPCA, QR, etc.)
            x: X position in dots
            y: Y position in dots
            height: Barcode height in dots
            readable: Show human-readable text (0=no, 1=yes)

        Returns:
            Dict with success status
        """
        # Map common names to TSPL codes
        type_map = {
            '128': '128',
            'C128': '128',
            'CODE128': '128',
            '39': '39',
            'C39': '39',
            'CODE39': '39',
            'EAN13': 'EAN13',
            'EAN8': 'EAN8',
            'UPCA': 'UPCA',
            'UPCE': 'UPCE',
            '93': '93',
            'CODA': 'CODA',
            'QR': 'QR',
            'QRCODE': 'QR',
        }

        bc_type = type_map.get(barcode_type.upper(), '128')

        if bc_type == 'QR':
            # QRCODE x,y,ECC level,cell width,mode,rotation,"data"
            commands = [
                'SIZE 50 mm,50 mm',
                'GAP 2 mm,0 mm',
                'CLS',
                f'QRCODE {x},{y},L,5,A,0,"{data}"',
                'PRINT 1,1',
            ]
        else:
            # BARCODE x,y,"type",height,readable,rotation,narrow,wide,"data"
            commands = [
                'SIZE 50 mm,30 mm',
                'GAP 2 mm,0 mm',
                'CLS',
                f'BARCODE {x},{y},"{bc_type}",{height},{readable},0,2,4,"{data}"',
                'PRINT 1,1',
            ]

        return self._send_tspl(commands)

    def print_food_label(self, dish_name: str, allergens: List[str] = None,
                         date: str = None, prep_by: str = None,
                         label_width: int = 50, label_height: int = 30) -> Dict[str, Any]:
        """
        Print a PrepSafe-style food safety label.

        Args:
            dish_name: Name of the dish
            allergens: List of allergens
            date: Prep/use-by date
            prep_by: Prepared by name
            label_width: Label width in mm
            label_height: Label height in mm

        Returns:
            Dict with success status
        """
        commands = [
            f'SIZE {label_width} mm,{label_height} mm',
            'GAP 2 mm,0 mm',
            'SPEED 4',
            'DENSITY 8',
            'DIRECTION 1,0',
            'CLS',
            # Title (larger font)
            f'TEXT 10,10,"4",0,1,1,"{dish_name}"',
        ]

        y_pos = 50

        # Allergens
        if allergens:
            allergen_str = ', '.join(allergens[:5])  # Limit to 5
            commands.append(f'TEXT 10,{y_pos},"2",0,1,1,"Allergens: {allergen_str}"')
            y_pos += 30

        # Date
        if date:
            commands.append(f'TEXT 10,{y_pos},"2",0,1,1,"Date: {date}"')
            y_pos += 25

        # Prepared by
        if prep_by:
            commands.append(f'TEXT 10,{y_pos},"2",0,1,1,"Prep: {prep_by}"')

        commands.append('PRINT 1,1')

        return self._send_tspl(commands)

    def get_status(self) -> Dict[str, Any]:
        """Get printer status."""
        host, port = self._get_connection()

        if not host:
            return {'success': False, 'error': 'Printer host not configured'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(DEFAULT_TIMEOUT)
            sock.connect((host, port))

            # TSPL status command - returns printer status byte
            sock.send(b'\x1b!?\r\n')  # ESC ! ? - status query

            response = sock.recv(256)
            sock.close()

            # Parse status response
            status = 'unknown'
            if response:
                status_byte = response[0] if len(response) > 0 else 0

                # Status bits (varies by printer model)
                if status_byte == 0:
                    status = 'ready'
                elif status_byte & 0x01:
                    status = 'head_open'
                elif status_byte & 0x02:
                    status = 'paper_jam'
                elif status_byte & 0x04:
                    status = 'paper_out'
                elif status_byte & 0x08:
                    status = 'ribbon_out'
                elif status_byte & 0x10:
                    status = 'paused'
                elif status_byte & 0x20:
                    status = 'printing'
                else:
                    status = 'ready'

            return {
                'success': True,
                'host': host,
                'port': port,
                'status': status,
                'raw_response': response.hex() if response else None
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

    def calibrate(self) -> Dict[str, Any]:
        """
        Run automatic label calibration.

        The printer will feed labels to detect gap/size.
        """
        commands = [
            'GAPDETECT',  # Auto-detect gap
        ]
        return self._send_tspl(commands)

    def feed(self, count: int = 1) -> Dict[str, Any]:
        """Feed labels."""
        commands = [
            f'FORMFEED',  # Feed one label
        ] * count
        return self._send_tspl(commands)

    def set_label_size(self, width_mm: int, height_mm: int, gap_mm: int = 2) -> Dict[str, Any]:
        """
        Configure label size.

        Args:
            width_mm: Label width in mm
            height_mm: Label height in mm
            gap_mm: Gap between labels in mm
        """
        commands = [
            f'SIZE {width_mm} mm,{height_mm} mm',
            f'GAP {gap_mm} mm,0 mm',
        ]
        return self._send_tspl(commands)
