"""
EGS Print Service - Main Application
=====================================

Standalone multi-brand printer management service.

Run: python -m egs_print_service
"""

import os
import sys
import json
import base64
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from . import __version__
from .config import PORT, HOST, DEBUG, API_KEY, DATA_DIR, PRINTER_TYPES
from .models import Printer, PrintJob
from .handlers import get_handler, EvolisHandler

# =============================================================================
# Application Setup
# =============================================================================

# Get web directory path
WEB_DIR = Path(__file__).parent / 'web'

app = Flask(__name__, static_folder=str(WEB_DIR / 'static'))
CORS(app)

# In-memory storage (will add file persistence)
_printers: dict = {}
_jobs: list = []

# =============================================================================
# Storage Functions
# =============================================================================

def _get_data_file(name: str) -> Path:
    """Get path to data file."""
    data_dir = Path(DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / f'{name}.json'


def _load_printers():
    """Load printers from storage."""
    global _printers
    try:
        path = _get_data_file('printers')
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                _printers = {k: Printer.from_dict(v) for k, v in data.items()}
    except Exception as e:
        print(f"[WARN] Failed to load printers: {e}")


def _save_printers():
    """Save printers to storage."""
    try:
        path = _get_data_file('printers')
        with open(path, 'w') as f:
            json.dump({k: v.to_dict() for k, v in _printers.items()}, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save printers: {e}")


def _check_api_key():
    """Validate API key from request."""
    data = request.get_json(silent=True) or {}
    auth_header = request.headers.get('Authorization', '')

    # Check body
    if data.get('api_key') == API_KEY:
        return True

    # Check header (Bearer token)
    if auth_header.startswith('Bearer ') and auth_header[7:] == API_KEY:
        return True

    return False


# =============================================================================
# Web Dashboard
# =============================================================================

@app.route('/', methods=['GET'])
def dashboard():
    """Serve web dashboard."""
    return send_from_directory(str(WEB_DIR), 'index.html')


@app.route('/dashboard', methods=['GET'])
def dashboard_alt():
    """Alternative dashboard route."""
    return send_from_directory(str(WEB_DIR), 'index.html')


@app.route('/api', methods=['GET'])
def api_info():
    """API info (JSON)."""
    return jsonify({
        'service': 'EGS Print Service',
        'version': __version__,
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'printers': '/api/printers',
            'jobs': '/api/jobs',
            'discover': '/api/discover',
        }
    })


# =============================================================================
# Health & Info Endpoints
# =============================================================================


@app.route('/health', methods=['GET'])
def health():
    """Health check with system info."""
    import platform
    import socket as sock

    return jsonify({
        'status': 'online',
        'version': __version__,
        'hostname': sock.gethostname(),
        'platform': platform.system(),
        'python': sys.version.split()[0],
        'printers_registered': len(_printers),
        'timestamp': datetime.now().isoformat(),
    })


# =============================================================================
# Printer Management API
# =============================================================================

@app.route('/api/printers', methods=['GET'])
def list_printers():
    """List all registered printers.

    Query params:
        status=true - Check live online/offline status for each printer
    """
    include_status = request.args.get('status', 'false').lower() == 'true'

    printers_data = []
    for p in _printers.values():
        printer_dict = p.to_dict()

        # Optionally check live status
        if include_status:
            printer_dict['is_online'] = _check_printer_online(p)
        else:
            printer_dict['is_online'] = None  # Unknown (not checked)

        printers_data.append(printer_dict)

    return jsonify({
        'success': True,
        'printers': printers_data,
        'count': len(_printers)
    })


def _check_printer_online(printer: Printer) -> bool:
    """Check if a printer is online/reachable."""
    import socket

    # Network printers - TCP connection test
    if printer.host:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2 second timeout for quick check
            sock.connect((printer.host, printer.port or 9100))
            sock.close()
            return True
        except Exception:
            return False

    # USB printers (Windows) - check if in printer list
    if printer.windows_name and sys.platform == 'win32':
        try:
            import win32print
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            for p in printers:
                if p[2] == printer.windows_name:
                    return True
            return False
        except Exception:
            return False

    return False  # Unknown connection type


@app.route('/api/printers', methods=['POST'])
def add_printer():
    """Add a new printer."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400

    # Validate required fields
    if not data.get('name'):
        return jsonify({'success': False, 'error': 'Printer name required'}), 400
    if not data.get('printer_type'):
        return jsonify({'success': False, 'error': 'Printer type required'}), 400
    if data['printer_type'] not in PRINTER_TYPES:
        return jsonify({
            'success': False,
            'error': f'Invalid printer type. Valid: {list(PRINTER_TYPES.keys())}'
        }), 400

    # Create printer
    printer = Printer(
        name=data['name'],
        printer_type=data['printer_type'],
        model=data.get('model', ''),
        connection_mode=data.get('connection_mode', 'usb'),
        host=data.get('host'),
        port=data.get('port', 9100),
        windows_name=data.get('windows_name'),
        location=data.get('location', ''),
        is_default=data.get('is_default', False),
    )

    _printers[printer.id] = printer
    _save_printers()

    return jsonify({
        'success': True,
        'printer': printer.to_dict(),
        'message': 'Printer added successfully'
    }), 201


@app.route('/api/printers/<printer_id>', methods=['GET'])
def get_printer(printer_id):
    """Get printer details."""
    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    return jsonify({
        'success': True,
        'printer': printer.to_dict()
    })


@app.route('/api/printers/<printer_id>', methods=['PUT'])
def update_printer(printer_id):
    """Update printer configuration."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400

    # Update allowed fields
    for field in ['name', 'model', 'host', 'port', 'windows_name', 'location',
                  'is_active', 'is_default', 'sleep_timeout_minutes']:
        if field in data:
            setattr(printer, field, data[field])

    printer.updated_at = datetime.now()
    _save_printers()

    return jsonify({
        'success': True,
        'printer': printer.to_dict()
    })


@app.route('/api/printers/<printer_id>', methods=['DELETE'])
def delete_printer(printer_id):
    """Delete a printer."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    if printer_id not in _printers:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    del _printers[printer_id]
    _save_printers()

    return jsonify({
        'success': True,
        'message': 'Printer deleted'
    })


# =============================================================================
# Printer Actions
# =============================================================================

@app.route('/api/printers/status', methods=['GET'])
def all_printers_status():
    """Check online/offline status for all printers at once.

    Returns quick status check (TCP connection for network, driver check for USB).
    For detailed status (paper, ribbon, etc.), use /api/printers/{id}/status instead.
    """
    results = []
    online_count = 0
    offline_count = 0

    for printer in _printers.values():
        is_online = _check_printer_online(printer)
        status = 'online' if is_online else 'offline'

        if is_online:
            online_count += 1
        else:
            offline_count += 1

        results.append({
            'id': printer.id,
            'name': printer.name,
            'printer_type': printer.printer_type,
            'host': printer.host,
            'is_online': is_online,
            'status': status,
        })

    return jsonify({
        'success': True,
        'printers': results,
        'summary': {
            'total': len(results),
            'online': online_count,
            'offline': offline_count,
        }
    })


@app.route('/api/printers/<printer_id>/test', methods=['POST'])
def test_printer(printer_id):
    """Test connection to printer."""
    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    handler_class = get_handler(PRINTER_TYPES[printer.printer_type]['handler'])
    if not handler_class:
        return jsonify({'success': False, 'error': 'Handler not found'}), 500

    handler = handler_class(printer)
    result = handler.test_connection()

    # Update printer status
    if result['success']:
        printer.update_status('online')
    else:
        printer.update_status('offline', result.get('error'))
    _save_printers()

    return jsonify(result)


@app.route('/api/printers/<printer_id>/status', methods=['GET'])
def printer_status(printer_id):
    """Get printer status."""
    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    handler_class = get_handler(PRINTER_TYPES[printer.printer_type]['handler'])
    if not handler_class:
        return jsonify({'success': False, 'error': 'Handler not found'}), 500

    handler = handler_class(printer)
    result = handler.get_status()

    # Update printer status
    if result.get('success'):
        printer.update_status(result.get('status', 'unknown'))
    _save_printers()

    return jsonify(result)


@app.route('/api/printers/<printer_id>/print', methods=['POST'])
def print_to_printer(printer_id):
    """Submit print job."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400

    if not data.get('image_base64'):
        return jsonify({'success': False, 'error': 'image_base64 required'}), 400

    # Create job
    job = PrintJob(
        printer_id=printer_id,
        document_name=data.get('document_name', 'Print Job'),
        copies=data.get('copies', 1),
        source_ip=request.remote_addr,
    )
    job.start()

    # Get handler and print
    handler_class = get_handler(PRINTER_TYPES[printer.printer_type]['handler'])
    if not handler_class:
        job.fail('Handler not found')
        return jsonify({'success': False, 'error': 'Handler not found'}), 500

    handler = handler_class(printer)

    try:
        image_data = base64.b64decode(data['image_base64'])
        result = handler.print_image(image_data, **data.get('options', {}))

        if result['success']:
            job.complete()
            printer.update_status('ready')
        else:
            job.fail(result.get('error', 'Print failed'))
            printer.update_status('error', result.get('error'))

        _jobs.append(job)
        _save_printers()

        result['job'] = job.to_dict()
        return jsonify(result)

    except Exception as e:
        job.fail(str(e))
        _jobs.append(job)
        return jsonify({'success': False, 'error': str(e), 'job': job.to_dict()}), 500


# =============================================================================
# Power Management (Evolis)
# =============================================================================

@app.route('/api/printers/<printer_id>/power/sleep-timeout', methods=['GET', 'POST'])
def printer_sleep_timeout(printer_id):
    """Get or set sleep timeout (Evolis only)."""
    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    if printer.printer_type != 'evolis':
        return jsonify({'success': False, 'error': 'Power management only for Evolis'}), 400

    handler = EvolisHandler(printer)

    if request.method == 'GET':
        return jsonify(handler.get_sleep_timeout())
    else:
        if not _check_api_key():
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401

        data = request.get_json()
        if not data or 'minutes' not in data:
            return jsonify({'success': False, 'error': 'minutes required'}), 400

        return jsonify(handler.set_sleep_timeout(data['minutes']))


@app.route('/api/printers/<printer_id>/power/wake', methods=['POST'])
def printer_wake(printer_id):
    """Wake printer from sleep."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    handler_class = get_handler(PRINTER_TYPES[printer.printer_type]['handler'])
    handler = handler_class(printer)

    if handler.supports_power_management():
        return jsonify(handler.wake())
    else:
        return jsonify({'success': False, 'error': 'Power management not supported'}), 400


@app.route('/api/printers/<printer_id>/power/reboot', methods=['POST'])
def printer_reboot(printer_id):
    """Reboot printer."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    handler_class = get_handler(PRINTER_TYPES[printer.printer_type]['handler'])
    handler = handler_class(printer)

    if handler.supports_power_management():
        return jsonify(handler.reboot())
    else:
        return jsonify({'success': False, 'error': 'Power management not supported'}), 400


@app.route('/api/printers/<printer_id>/power/led-flash', methods=['POST'])
def printer_led_flash(printer_id):
    """Flash LED to identify printer."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    printer = _printers.get(printer_id)
    if not printer:
        return jsonify({'success': False, 'error': 'Printer not found'}), 404

    handler_class = get_handler(PRINTER_TYPES[printer.printer_type]['handler'])
    handler = handler_class(printer)

    data = request.get_json() or {}
    duration = data.get('duration', 5)

    return jsonify(handler.flash_led(duration))


# =============================================================================
# Job History
# =============================================================================

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List recent jobs."""
    limit = request.args.get('limit', 50, type=int)
    printer_id = request.args.get('printer_id')

    jobs = _jobs
    if printer_id:
        jobs = [j for j in jobs if j.printer_id == printer_id]

    # Most recent first
    jobs = sorted(jobs, key=lambda j: j.created_at, reverse=True)[:limit]

    return jsonify({
        'success': True,
        'jobs': [j.to_dict() for j in jobs],
        'count': len(jobs)
    })


# =============================================================================
# Auto-discover Printers
# =============================================================================

@app.route('/api/discover', methods=['GET'])
def discover_printers():
    """Auto-discover available printers."""
    discovered = []

    # Discover Windows printers (Evolis)
    if sys.platform == 'win32':
        try:
            import win32print
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            for p in printers:
                printer_info = {
                    'name': p[2],
                    'connection_mode': 'usb',
                    'windows_name': p[2],
                }
                if 'evolis' in p[2].lower():
                    printer_info['printer_type'] = 'evolis'
                elif 'zebra' in p[2].lower():
                    printer_info['printer_type'] = 'zebra'
                elif 'star' in p[2].lower():
                    printer_info['printer_type'] = 'star'
                elif 'epson' in p[2].lower():
                    printer_info['printer_type'] = 'epson'
                elif 'sato' in p[2].lower():
                    printer_info['printer_type'] = 'sato'
                elif 'cab' in p[2].lower():
                    printer_info['printer_type'] = 'cab'
                else:
                    printer_info['printer_type'] = 'unknown'

                discovered.append(printer_info)
        except Exception as e:
            pass

    return jsonify({
        'success': True,
        'discovered': discovered,
        'count': len(discovered)
    })


# =============================================================================
# Backward Compatibility with evolis_print_agent
# =============================================================================

@app.route('/print', methods=['POST'])
def legacy_print():
    """Legacy print endpoint for backward compatibility."""
    data = request.get_json()

    if not data or data.get('api_key') != API_KEY:
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    # Find or create default Evolis printer
    evolis_printer = None
    for p in _printers.values():
        if p.printer_type == 'evolis' and p.is_default:
            evolis_printer = p
            break

    if not evolis_printer:
        # Auto-discover
        if sys.platform == 'win32':
            try:
                import win32print
                printers = win32print.EnumPrinters(
                    win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                )
                for p in printers:
                    if 'evolis' in p[2].lower():
                        evolis_printer = Printer(
                            name='Evolis (Auto)',
                            printer_type='evolis',
                            windows_name=p[2],
                            is_default=True,
                        )
                        _printers[evolis_printer.id] = evolis_printer
                        _save_printers()
                        break
            except:
                pass

    if not evolis_printer:
        return jsonify({'success': False, 'error': 'No Evolis printer found'}), 404

    # Print using Evolis handler
    handler = EvolisHandler(evolis_printer)
    try:
        image_data = base64.b64decode(data['image_base64'])

        # Get options from request (orientation, document_name, etc.)
        options = data.get('options', {})
        document_name = data.get('document_name', 'Badge Print')
        copies = data.get('copies', 1)

        # Default to landscape for CR-80 badges
        orientation = options.get('orientation', 'landscape')

        result = handler.print_image(
            image_data,
            orientation=orientation,
            document_name=document_name,
            copies=copies,
            **options
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/printers', methods=['GET'])
def legacy_printers():
    """Legacy printers endpoint."""
    if sys.platform == 'win32':
        try:
            import win32print
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return jsonify({
                'success': True,
                'printers': [
                    {'name': p[2], 'is_evolis': 'evolis' in p[2].lower()}
                    for p in printers
                ]
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': True, 'printers': []})


# Legacy power management endpoints
@app.route('/evolis/power/sleep-timeout', methods=['GET', 'POST'])
def legacy_sleep_timeout():
    """Legacy sleep timeout endpoint."""
    # Find default Evolis
    for p in _printers.values():
        if p.printer_type == 'evolis':
            return printer_sleep_timeout(p.id)

    # Try auto-discover
    if sys.platform == 'win32':
        handler = EvolisHandler(Printer(name='temp', printer_type='evolis'))
        if request.method == 'GET':
            return jsonify(handler.get_sleep_timeout())
        else:
            if not _check_api_key():
                return jsonify({'success': False, 'error': 'Invalid API key'}), 401
            data = request.get_json()
            return jsonify(handler.set_sleep_timeout(data.get('minutes', 30)))

    return jsonify({'success': False, 'error': 'No Evolis printer found'}), 404


@app.route('/evolis/power/wake', methods=['POST'])
def legacy_wake():
    """Legacy wake endpoint."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    handler = EvolisHandler(Printer(name='temp', printer_type='evolis'))
    return jsonify(handler.wake())


@app.route('/evolis/power/status', methods=['GET'])
def legacy_status():
    """Legacy status endpoint."""
    handler = EvolisHandler(Printer(name='temp', printer_type='evolis'))
    return jsonify(handler.get_status())


@app.route('/evolis/power/reboot', methods=['POST'])
def legacy_reboot():
    """Legacy reboot endpoint."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    handler = EvolisHandler(Printer(name='temp', printer_type='evolis'))
    return jsonify(handler.reboot())


@app.route('/evolis/power/led-flash', methods=['POST'])
def legacy_led_flash():
    """Legacy LED flash endpoint."""
    if not _check_api_key():
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401

    data = request.get_json() or {}
    handler = EvolisHandler(Printer(name='temp', printer_type='evolis'))
    return jsonify(handler.flash_led(data.get('duration', 5)))


# =============================================================================
# Main
# =============================================================================

def main():
    """Run the service."""
    print("=" * 60)
    print("  EGS Print Service")
    print("=" * 60)
    print(f"  Version: {__version__}")
    print(f"  Port: {PORT}")
    print(f"  Data: {DATA_DIR}")
    print("=" * 60)
    print("  API Endpoints:")
    print("    GET  /health                          - Health check")
    print("    GET  /api/printers                    - List printers")
    print("    POST /api/printers                    - Add printer")
    print("    GET  /api/printers/{id}               - Get printer")
    print("    PUT  /api/printers/{id}               - Update printer")
    print("    DEL  /api/printers/{id}               - Delete printer")
    print("    POST /api/printers/{id}/print         - Submit print job")
    print("    GET  /api/printers/{id}/status        - Get status")
    print("    POST /api/printers/{id}/test          - Test connection")
    print("    GET  /api/printers/{id}/power/*       - Power management")
    print("    GET  /api/jobs                        - Job history")
    print("    GET  /api/discover                    - Auto-discover")
    print("=" * 60)
    print("  Legacy Endpoints (backward compatible):")
    print("    POST /print                           - Print to Evolis")
    print("    GET  /printers                        - List Windows printers")
    print("    GET/POST /evolis/power/*              - Evolis power mgmt")
    print("=" * 60)

    # Load saved printers
    _load_printers()
    print(f"  Loaded {len(_printers)} printer(s) from storage")
    print("=" * 60)

    app.run(host=HOST, port=PORT, debug=DEBUG)


if __name__ == '__main__':
    main()
