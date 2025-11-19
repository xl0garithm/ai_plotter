"""Application configuration."""

from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Base configuration for the AI plotter application."""

    BASE_DIR = Path(__file__).resolve().parent
    STORAGE_DIR = BASE_DIR / "storage"
    UPLOAD_DIR = BASE_DIR / "uploads"
    GENERATED_DIR = BASE_DIR / "processed"
    GCODE_DIR = BASE_DIR / "gcode"
    DB_PATH = STORAGE_DIR / "app.db"

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-preview-image")

    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

    # Serial connection
    SERIAL_PORT = os.environ.get("PLOTTER_SERIAL_PORT", "COM3")
    SERIAL_BAUDRATE = int(os.environ.get("PLOTTER_BAUDRATE", "115200"))
    SERIAL_TIMEOUT = float(os.environ.get("PLOTTER_SERIAL_TIMEOUT", "10.0"))
    PLOTTER_DRY_RUN = os.environ.get("PLOTTER_DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "on"}
    PLOTTER_INVERT_Z = os.environ.get("PLOTTER_INVERT_Z", "false").strip().lower() in {"1", "true", "yes", "on"}
    PLOTTER_LINE_DELAY = float(os.environ.get("PLOTTER_LINE_DELAY", "0.1"))

    # Queue
    MAX_RETRY = int(os.environ.get("PLOTTER_MAX_RETRY", "3"))

    # File settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB uploads

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure required directories exist."""
        for directory in (cls.STORAGE_DIR, cls.UPLOAD_DIR, cls.GENERATED_DIR, cls.GCODE_DIR):
            directory.mkdir(parents=True, exist_ok=True)
