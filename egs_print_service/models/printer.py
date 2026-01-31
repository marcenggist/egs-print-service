"""
Printer Model
=============

Represents a printer in the registry.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any


@dataclass
class Printer:
    """Printer configuration and state."""

    # Identification
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    name: str = ""
    printer_type: str = ""  # evolis, zebra, cab, sato, star, epson
    model: str = ""  # e.g., "Primacy 2", "ZD421"

    # Connection
    connection_mode: str = "usb"  # usb, network, bluetooth
    host: Optional[str] = None  # For network printers
    port: int = 9100  # For network printers

    # Windows printer name (for USB printers)
    windows_name: Optional[str] = None

    # Location (for multi-site)
    location: str = ""

    # Power settings (Evolis only)
    sleep_timeout_minutes: int = 30

    # Status
    status: str = "unknown"  # online, offline, sleeping, error, unknown
    last_status_check: Optional[datetime] = None
    last_error: Optional[str] = None

    # Flags
    is_active: bool = True
    is_default: bool = False

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ['created_at', 'updated_at', 'last_status_check']:
            if data.get(key):
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Printer':
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        for key in ['created_at', 'updated_at', 'last_status_check']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)

    def update_status(self, status: str, error: Optional[str] = None):
        """Update printer status."""
        self.status = status
        self.last_status_check = datetime.now()
        self.last_error = error
        self.updated_at = datetime.now()
