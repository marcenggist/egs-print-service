"""
Print Job Model
===============

Represents a print job in the queue.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any


@dataclass
class PrintJob:
    """Print job configuration and state."""

    # Identification
    id: str = field(default_factory=lambda: f"JOB-{str(uuid.uuid4())[:8].upper()}")
    printer_id: str = ""

    # Job details
    job_type: str = "print"  # print, test, wake
    document_name: str = ""
    copies: int = 1

    # Status
    status: str = "pending"  # pending, printing, completed, failed, cancelled
    progress: int = 0  # 0-100
    error_message: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Source
    source: str = "api"  # api, dashboard, scheduled
    source_ip: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO format
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key):
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrintJob':
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)

    def start(self):
        """Mark job as started."""
        self.status = "printing"
        self.started_at = datetime.now()
        self.progress = 0

    def complete(self):
        """Mark job as completed."""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.progress = 100

    def fail(self, error: str):
        """Mark job as failed."""
        self.status = "failed"
        self.completed_at = datetime.now()
        self.error_message = error

    def cancel(self):
        """Mark job as cancelled."""
        self.status = "cancelled"
        self.completed_at = datetime.now()
