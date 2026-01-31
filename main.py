#!/usr/bin/env python
"""
EGS Print Service - Standalone Entry Point

Run directly:
    python main.py

Or with environment variables:
    EGS_PRINT_PORT=5200 python main.py
"""

import os
import sys

# Ensure package is importable when running directly
if __name__ == '__main__':
    # Add parent directory to path for standalone execution
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from egs_print_service.app import app
from egs_print_service.config import PORT, HOST, DEBUG


def main():
    """Start the EGS Print Service."""
    print("=" * 60)
    print("EGS Print Service")
    print("=" * 60)
    print(f"Starting on http://{HOST}:{PORT}")
    print(f"Dashboard: http://localhost:{PORT}/")
    print(f"API: http://localhost:{PORT}/api")
    print("=" * 60)

    app.run(host=HOST, port=PORT, debug=DEBUG)


if __name__ == '__main__':
    main()
