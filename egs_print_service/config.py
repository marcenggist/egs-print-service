"""
EGS Print Service Configuration
"""

import os

# =============================================================================
# Server Configuration
# =============================================================================

PORT = int(os.environ.get('EGS_PRINT_PORT', 5100))
HOST = os.environ.get('EGS_PRINT_HOST', '0.0.0.0')
DEBUG = os.environ.get('EGS_PRINT_DEBUG', 'false').lower() == 'true'

# API Key for authentication
API_KEY = os.environ.get('EGS_PRINT_API_KEY', 'egs-print-2026')

# =============================================================================
# Printer Defaults
# =============================================================================

DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_RETRIES = 3

# ZPL/Network printer default port
ZPL_PORT = 9100

# =============================================================================
# Supported Printer Types
# =============================================================================

PRINTER_TYPES = {
    'evolis': {
        'name': 'Evolis Badge Printer',
        'handler': 'evolis',
        'connection': ['usb'],
        'supports_power_management': True,
    },
    'zebra': {
        'name': 'Zebra Label Printer',
        'handler': 'zpl',
        'connection': ['network', 'usb'],
        'default_port': 9100,
    },
    'cab': {
        'name': 'CAB Label Printer',
        'handler': 'zpl',  # CAB supports ZPL emulation
        'connection': ['network', 'usb'],
        'default_port': 9100,
    },
    'sato': {
        'name': 'SATO Label Printer',
        'handler': 'sbpl',
        'connection': ['network', 'usb'],
        'default_port': 9100,
    },
    'star': {
        'name': 'Star Thermal Printer',
        'handler': 'escpos',
        'connection': ['network', 'usb'],
        'default_port': 9100,
    },
    'epson': {
        'name': 'Epson Thermal Printer',
        'handler': 'escpos',
        'connection': ['network', 'usb'],
        'default_port': 9100,
    },
    # TSPL-based printers (Gainsha, TSC, PrepSafe)
    'gainsha': {
        'name': 'Gainsha/Gprinter Label Printer',
        'handler': 'tspl',
        'connection': ['network', 'usb', 'bluetooth'],
        'default_port': 9100,
        'models': ['GS-2208', 'GS-2406T', 'GS-2408D', 'GI-2408T'],
    },
    'gprinter': {
        'name': 'Gprinter Label Printer',
        'handler': 'tspl',
        'connection': ['network', 'usb', 'bluetooth'],
        'default_port': 9100,
    },
    'prepsafe': {
        'name': 'PrepSafe Food Label Printer',
        'handler': 'tspl',  # PrepSafe uses Gainsha printers with TSPL
        'connection': ['network', 'usb', 'bluetooth'],
        'default_port': 9100,
    },
    'tsc': {
        'name': 'TSC Label Printer',
        'handler': 'tspl',
        'connection': ['network', 'usb'],
        'default_port': 9100,
    },
}

# =============================================================================
# Storage Configuration
# =============================================================================

# Where to store printer configuration (local file-based for standalone)
DATA_DIR = os.environ.get('EGS_PRINT_DATA_DIR', os.path.expanduser('~/.egs_print_service'))

# Job history retention (days)
JOB_HISTORY_DAYS = 30
