"""Database models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from services.database import Base


class Job(Base):
    """Represents a queued plotter job."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    asset_key = Column(String(64), unique=True, nullable=False)
    status = Column(String(32), nullable=False, default="submitted")
    requester = Column(String(128), nullable=True)
    prompt = Column(Text, nullable=True)
    original_path = Column(Text, nullable=False)
    generated_path = Column(Text, nullable=True)
    gcode_path = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self, *, admin: bool = False) -> Dict[str, Any]:
        """Serialize the job for JSON responses."""
        data: Dict[str, Any] = {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if admin:
            data.update(
                {
                    "requester": self.requester,
                    "prompt": self.prompt,
                    "metadata": self.metadata_json,
                    "generated_path": self.generated_path,
                    "gcode_path": self.gcode_path,
                    "retry_count": self.retry_count,
                    "error_message": self.error_message,
                    "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
                    "approved_at": self.approved_at.isoformat() if self.approved_at else None,
                    "started_at": self.started_at.isoformat() if self.started_at else None,
                    "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                }
            )

        return data

