"""
EGS Print Service Client
========================

Python SDK for interacting with EGS Print Service.

Usage:
    from egs_print_service.client import PrintClient

    client = PrintClient('http://localhost:5100', api_key='your-key')

    # List printers
    printers = client.list_printers()

    # Print image
    with open('badge.png', 'rb') as f:
        result = client.print_image('PRINTER-ID', f.read())

    # Power management
    client.set_sleep_timeout('PRINTER-ID', 30)
    client.wake('PRINTER-ID')
"""

import base64
import requests
from typing import Dict, Any, Optional, List


class PrintClient:
    """Client for EGS Print Service."""

    def __init__(self, base_url: str = 'http://localhost:5100', api_key: str = None):
        """
        Initialize client.

        Args:
            base_url: Base URL of the print service
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make API request."""
        url = f'{self.base_url}{endpoint}'

        if data and self.api_key:
            data['api_key'] = self.api_key

        try:
            if method == 'GET':
                response = requests.get(url, headers=self._headers(), timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=self._headers(), timeout=60)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=self._headers(), timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self._headers(), timeout=30)
            else:
                raise ValueError(f'Unknown method: {method}')

            return response.json()

        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': f'Cannot connect to {self.base_url}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Health
    # =========================================================================

    def health(self) -> Dict[str, Any]:
        """Check service health."""
        return self._request('GET', '/health')

    def is_online(self) -> bool:
        """Check if service is online."""
        result = self.health()
        return result.get('status') == 'online'

    # =========================================================================
    # Printers
    # =========================================================================

    def list_printers(self) -> List[Dict[str, Any]]:
        """List all printers."""
        result = self._request('GET', '/api/printers')
        return result.get('printers', [])

    def get_printer(self, printer_id: str) -> Optional[Dict[str, Any]]:
        """Get printer by ID."""
        result = self._request('GET', f'/api/printers/{printer_id}')
        return result.get('printer') if result.get('success') else None

    def add_printer(self, name: str, printer_type: str, **kwargs) -> Dict[str, Any]:
        """
        Add a new printer.

        Args:
            name: Printer display name
            printer_type: Type (evolis, zebra, cab, sato, star, epson)
            **kwargs: Additional options (model, host, port, etc.)
        """
        data = {
            'name': name,
            'printer_type': printer_type,
            **kwargs
        }
        return self._request('POST', '/api/printers', data)

    def update_printer(self, printer_id: str, **kwargs) -> Dict[str, Any]:
        """Update printer configuration."""
        return self._request('PUT', f'/api/printers/{printer_id}', kwargs)

    def delete_printer(self, printer_id: str) -> Dict[str, Any]:
        """Delete a printer."""
        return self._request('DELETE', f'/api/printers/{printer_id}')

    def discover_printers(self) -> List[Dict[str, Any]]:
        """Auto-discover available printers."""
        result = self._request('GET', '/api/discover')
        return result.get('discovered', [])

    # =========================================================================
    # Printing
    # =========================================================================

    def print_image(self, printer_id: str, image_data: bytes,
                    document_name: str = 'Print Job', **options) -> Dict[str, Any]:
        """
        Print an image.

        Args:
            printer_id: Target printer ID
            image_data: Raw image bytes (PNG/JPEG)
            document_name: Job name
            **options: Handler-specific options
        """
        data = {
            'image_base64': base64.b64encode(image_data).decode('utf-8'),
            'document_name': document_name,
            'options': options,
        }
        return self._request('POST', f'/api/printers/{printer_id}/print', data)

    def print_file(self, printer_id: str, file_path: str, **options) -> Dict[str, Any]:
        """Print an image file."""
        with open(file_path, 'rb') as f:
            return self.print_image(printer_id, f.read(), **options)

    # =========================================================================
    # Status
    # =========================================================================

    def get_status(self, printer_id: str) -> Dict[str, Any]:
        """Get detailed printer status (paper, ribbon, head status, etc.)."""
        return self._request('GET', f'/api/printers/{printer_id}/status')

    def test_connection(self, printer_id: str) -> Dict[str, Any]:
        """Test printer connection (quick TCP check)."""
        return self._request('POST', f'/api/printers/{printer_id}/test')

    def get_all_status(self) -> Dict[str, Any]:
        """
        Check online/offline status for ALL printers at once.

        Returns:
            Dict with printers list and summary counts
            Example: {'printers': [...], 'summary': {'total': 2, 'online': 1, 'offline': 1}}
        """
        return self._request('GET', '/api/printers/status')

    def is_printer_online(self, printer_id: str) -> bool:
        """
        Quick check if a specific printer is online.

        Args:
            printer_id: Printer ID to check

        Returns:
            True if online, False if offline or error
        """
        result = self.test_connection(printer_id)
        return result.get('success', False)

    def list_printers_with_status(self) -> List[Dict[str, Any]]:
        """
        List all printers with their online/offline status.

        Returns:
            List of printer dicts with 'is_online' field
        """
        result = self._request('GET', '/api/printers?status=true')
        return result.get('printers', [])

    # =========================================================================
    # Power Management (Evolis)
    # =========================================================================

    def get_sleep_timeout(self, printer_id: str) -> Dict[str, Any]:
        """Get sleep timeout setting."""
        return self._request('GET', f'/api/printers/{printer_id}/power/sleep-timeout')

    def set_sleep_timeout(self, printer_id: str, minutes: int) -> Dict[str, Any]:
        """Set sleep timeout."""
        return self._request('POST', f'/api/printers/{printer_id}/power/sleep-timeout',
                             {'minutes': minutes})

    def wake(self, printer_id: str) -> Dict[str, Any]:
        """Wake printer from sleep."""
        return self._request('POST', f'/api/printers/{printer_id}/power/wake')

    def reboot(self, printer_id: str) -> Dict[str, Any]:
        """Reboot printer."""
        return self._request('POST', f'/api/printers/{printer_id}/power/reboot')

    def flash_led(self, printer_id: str, duration: int = 5) -> Dict[str, Any]:
        """Flash LED to identify printer."""
        return self._request('POST', f'/api/printers/{printer_id}/power/led-flash',
                             {'duration': duration})

    # =========================================================================
    # Jobs
    # =========================================================================

    def list_jobs(self, printer_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent print jobs."""
        endpoint = f'/api/jobs?limit={limit}'
        if printer_id:
            endpoint += f'&printer_id={printer_id}'
        result = self._request('GET', endpoint)
        return result.get('jobs', [])
