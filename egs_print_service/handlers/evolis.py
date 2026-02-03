"""
Evolis Handler
==============

Handler for Evolis badge printers (Primacy, Primacy 2, Zenius, etc.)
Uses Windows print drivers via pywin32.
"""

import sys
from io import BytesIO
from typing import Dict, Any, Optional

from .base import BaseHandler
from ..models import Printer


class EvolisHandler(BaseHandler):
    """Handler for Evolis badge printers."""

    def __init__(self, printer: Printer):
        super().__init__(printer)
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required modules are available."""
        if sys.platform != 'win32':
            raise RuntimeError("Evolis handler requires Windows")

    def _get_printer_name(self) -> Optional[str]:
        """Get Windows printer name."""
        if self.printer.windows_name:
            return self.printer.windows_name

        # Auto-detect Evolis printer
        try:
            import win32print
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            for p in printers:
                if 'evolis' in p[2].lower():
                    return p[2]
        except Exception:
            pass
        return None

    def print_image(self, image_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        Print an image to the Evolis printer.

        Args:
            image_data: Raw image bytes (PNG or JPEG)
            copies: Number of copies (default 1)
            orientation: 'landscape' (default), 'portrait', or 'auto'
                - landscape: CR-80 standard (3.375" x 2.125"), rotates portrait images
                - portrait: Rotates to portrait mode (2.125" x 3.375")
                - auto: Keeps original image orientation

        Returns:
            Dict with success status
        """
        try:
            from PIL import Image
            import win32print
            import win32ui
            from PIL import ImageWin

            printer_name = self._get_printer_name()
            if not printer_name:
                return {'success': False, 'error': 'No Evolis printer found'}

            # Load image
            image = Image.open(BytesIO(image_data))
            orientation = kwargs.get('orientation', 'landscape')

            # Create printer DC
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc(kwargs.get('document_name', 'EGS Print Service'))
            hdc.StartPage()

            # CR-80 card dimensions: 3.375" x 2.125"
            dpi_x = hdc.GetDeviceCaps(88)
            dpi_y = hdc.GetDeviceCaps(90)

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            img_w, img_h = image.size
            is_portrait_image = img_h > img_w

            if orientation == 'landscape':
                # CR-80 landscape: 3.375" x 2.125" (wider than tall)
                w = int(3.375 * dpi_x)
                h = int(2.125 * dpi_y)
                # If image is portrait, rotate it to landscape
                if is_portrait_image:
                    image = image.rotate(90, expand=True)
            elif orientation == 'portrait':
                # CR-80 portrait: 2.125" x 3.375" (taller than wide)
                w = int(2.125 * dpi_x)
                h = int(3.375 * dpi_y)
                # If image is landscape, rotate it to portrait
                if not is_portrait_image:
                    image = image.rotate(90, expand=True)
            else:  # 'auto' - match image orientation
                if is_portrait_image:
                    w = int(2.125 * dpi_x)
                    h = int(3.375 * dpi_y)
                else:
                    w = int(3.375 * dpi_x)
                    h = int(2.125 * dpi_y)

            # Resize to target dimensions
            image = image.resize((w, h), Image.Resampling.LANCZOS)

            # Print
            dib = ImageWin.Dib(image)
            dib.draw(hdc.GetHandleOutput(), (0, 0, w, h))

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()

            return {
                'success': True,
                'printer': printer_name,
                'size': f'{w}x{h}',
                'dpi': f'{dpi_x}x{dpi_y}',
                'orientation': orientation,
                'rotated': (orientation == 'landscape' and is_portrait_image) or
                           (orientation == 'portrait' and not is_portrait_image)
            }

        except ImportError as e:
            return {'success': False, 'error': f'Missing module: {e}. Install: pip install pillow pywin32'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get printer status."""
        try:
            import win32print

            printer_name = self._get_printer_name()
            if not printer_name:
                return {'success': False, 'error': 'No Evolis printer found'}

            handle = win32print.OpenPrinter(printer_name)
            info = win32print.GetPrinter(handle, 2)
            win32print.ClosePrinter(handle)

            status_code = info['Status']
            status_map = {
                0: 'ready',
                1: 'paused',
                2: 'error',
                128: 'offline',
                512: 'busy',
                1024: 'printing',
                8192: 'waiting',
                16384: 'processing',
                32768: 'initializing',
                65536: 'warming_up',
                16777216: 'power_save',
            }

            status = 'unknown'
            for code, text in status_map.items():
                if status_code & code:
                    status = text
                    break
            if status_code == 0:
                status = 'ready'

            return {
                'success': True,
                'printer': printer_name,
                'status_code': status_code,
                'status': status,
                'jobs': info.get('cJobs', 0),
                'is_sleeping': status_code & 16777216 > 0,
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to printer."""
        try:
            import win32print

            printer_name = self._get_printer_name()
            if not printer_name:
                return {'success': False, 'error': 'No Evolis printer found'}

            handle = win32print.OpenPrinter(printer_name)
            win32print.ClosePrinter(handle)

            return {
                'success': True,
                'printer': printer_name,
                'message': 'Connection successful'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def supports_power_management(self) -> bool:
        """Evolis supports power management."""
        return True

    def set_sleep_timeout(self, minutes: int) -> Dict[str, Any]:
        """Set sleep timeout via Windows Registry."""
        try:
            import winreg

            reg_paths = [
                r'SOFTWARE\Evolis\PrintCenter',
                r'SOFTWARE\WOW6432Node\Evolis\PrintCenter',
            ]

            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, reg_path, 0,
                        winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
                    )
                    winreg.SetValueEx(key, 'SleepTimeout', 0, winreg.REG_DWORD, int(minutes))
                    winreg.CloseKey(key)

                    return {
                        'success': True,
                        'sleep_timeout_minutes': int(minutes),
                        'registry_path': reg_path,
                        'message': 'Restart Evolis Print Center for changes to take effect.'
                    }
                except PermissionError:
                    return {'success': False, 'error': 'Permission denied. Run as Administrator.'}
                except FileNotFoundError:
                    continue

            return {'success': False, 'error': 'Evolis registry not found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_sleep_timeout(self) -> Dict[str, Any]:
        """Get current sleep timeout."""
        try:
            import winreg

            reg_paths = [
                r'SOFTWARE\Evolis\PrintCenter',
                r'SOFTWARE\WOW6432Node\Evolis\PrintCenter',
                r'SOFTWARE\Evolis\Primacy',
                r'SOFTWARE\Evolis\Primacy 2',
            ]

            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    value, _ = winreg.QueryValueEx(key, 'SleepTimeout')
                    winreg.CloseKey(key)
                    return {
                        'success': True,
                        'sleep_timeout_minutes': value,
                        'registry_path': reg_path
                    }
                except (FileNotFoundError, Exception):
                    continue

            return {
                'success': True,
                'sleep_timeout_minutes': None,
                'message': 'Registry not found. Use Evolis Print Center to configure.'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def wake(self) -> Dict[str, Any]:
        """Wake printer from sleep."""
        try:
            import win32print
            import win32ui

            printer_name = self._get_printer_name()
            if not printer_name:
                return {'success': False, 'error': 'No Evolis printer found'}

            # Method 1: Open printer handle
            try:
                handle = win32print.OpenPrinter(printer_name)
                win32print.ClosePrinter(handle)
            except:
                pass

            # Method 2: Start and abort a print job (wakes without printing)
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc('Wake Command')
            hdc.AbortDoc()
            hdc.DeleteDC()

            return {
                'success': True,
                'printer': printer_name,
                'message': 'Wake command sent'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def reboot(self) -> Dict[str, Any]:
        """Soft reboot via pause/resume cycle."""
        try:
            import win32print
            import time

            printer_name = self._get_printer_name()
            if not printer_name:
                return {'success': False, 'error': 'No Evolis printer found'}

            handle = win32print.OpenPrinter(printer_name)
            win32print.SetPrinter(handle, 0, None, win32print.PRINTER_CONTROL_PAUSE)
            time.sleep(1)
            win32print.SetPrinter(handle, 0, None, win32print.PRINTER_CONTROL_RESUME)
            win32print.ClosePrinter(handle)

            return {
                'success': True,
                'printer': printer_name,
                'message': 'Reboot command sent (pause/resume cycle)'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def flash_led(self, duration: int = 5) -> Dict[str, Any]:
        """Flash LED to identify printer."""
        try:
            printer_name = self._get_printer_name()
            if not printer_name:
                return {'success': False, 'error': 'No Evolis printer found'}

            # Try Evolis COM interface
            try:
                import win32com.client
                evolis = win32com.client.Dispatch('Evolis.PrintCenter')
                evolis.FlashLED(printer_name, duration)
                return {
                    'success': True,
                    'printer': printer_name,
                    'duration': duration,
                    'method': 'evolis_com'
                }
            except:
                pass

            # Fallback: Wake cycles
            import win32ui
            import time

            for i in range(min(duration, 5)):
                try:
                    hdc = win32ui.CreateDC()
                    hdc.CreatePrinterDC(printer_name)
                    hdc.StartDoc(f'LED Flash {i+1}')
                    hdc.AbortDoc()
                    hdc.DeleteDC()
                    time.sleep(0.5)
                except:
                    pass

            return {
                'success': True,
                'printer': printer_name,
                'duration': duration,
                'method': 'wake_cycle',
                'message': 'LED flash simulated. Install Evolis SDK for true LED control.'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}
