"""
EGS Print Service
=================

Standalone multi-brand printer management service.

Supports:
- Evolis badge printers (via Windows drivers)
- Zebra/CAB label printers (via ZPL)
- SATO label printers (via SBPL)
- Star/Epson thermal printers (via ESC/POS)

Usage:
    python -m egs_print_service

API Endpoints:
    GET  /api/printers           - List all printers
    POST /api/printers           - Add new printer
    GET  /api/printers/{id}      - Get printer details
    POST /api/printers/{id}/print - Submit print job
    GET  /api/printers/{id}/status - Get status
    POST /api/printers/{id}/power  - Power management (Evolis)
    GET  /api/jobs               - Job queue & history
"""

__version__ = '1.0.0'
__author__ = 'EGS Software AG'
