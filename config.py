"""Application configuration."""

from __future__ import annotations

import logging
import os
from pathlib import Path


class Config:
    """Base configuration for the AI plotter application."""

    BASE_DIR = Path(__file__).resolve().parent
    STORAGE_DIR = BASE_DIR / "storage"
    UPLOAD_DIR = STORAGE_DIR / "uploads"
    GENERATED_DIR = STORAGE_DIR / "processed"
    GCODE_DIR = STORAGE_DIR / "gcode"
    DB_PATH = STORAGE_DIR / "app.db"

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")
    ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-preview-image")

    # Logging - set to DEBUG for verbose output
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()

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

    # Vectorization / image conversion
    VECTOR_RESOLUTION = int(os.environ.get("PLOTTER_VECTOR_RESOLUTION", "1600"))
    VECTORIZE_THRESHOLD = int(os.environ.get("PLOTTER_VECTORIZE_THRESHOLD", "240"))
    VECTORIZE_SIMPLIFY_PX = float(os.environ.get("PLOTTER_VECTORIZE_SIMPLIFY_PX", "2.0"))
    VECTORIZE_MIN_POINTS = int(os.environ.get("PLOTTER_VECTORIZE_MIN_POINTS", "24"))
    VECTORIZE_DOWNSAMPLE_STEP = int(os.environ.get("PLOTTER_VECTORIZE_DOWNSAMPLE_STEP", "1"))
    VECTORIZE_STROKE_WIDTH = float(os.environ.get("PLOTTER_VECTORIZE_STROKE_WIDTH", "3.0"))
    VECTORIZE_CROP_PADDING_RATIO = float(os.environ.get("PLOTTER_VECTORIZE_CROP_PADDING_RATIO", "0.05"))

    # Plotting behavior
    PLOTTER_FEED_RATE = int(os.environ.get("PLOTTER_FEED_RATE", "5000"))

    # Chess robot
    CHESS_BOARD_SIZE_MM = float(os.environ.get("CHESS_BOARD_SIZE_MM", "215.9"))
    CHESS_SQUARE_COUNT = int(os.environ.get("CHESS_SQUARE_COUNT", "8"))
    CHESS_GAP_MM = float(os.environ.get("CHESS_GAP_MM", "2.0"))
    CHESS_ORIGIN_X_MM = float(os.environ.get("CHESS_ORIGIN_X_MM", "0.0"))
    CHESS_ORIGIN_Y_MM = float(os.environ.get("CHESS_ORIGIN_Y_MM", "0.0"))
    CHESS_TAP_DWELL_S = float(os.environ.get("CHESS_TAP_DWELL_S", "0.3"))

    # Chess electromagnet control
    CHESS_MAGNET_ON_GCODE = os.environ.get("CHESS_MAGNET_ON_GCODE", "M3 S255").replace("\\n", "\n")
    CHESS_MAGNET_OFF_GCODE = os.environ.get("CHESS_MAGNET_OFF_GCODE", "M3 S0\nM5").replace("\\n", "\n")
    CHESS_MAGNET_ENGAGE_DWELL_S = float(os.environ.get("CHESS_MAGNET_ENGAGE_DWELL_S", "0.3"))
    CHESS_MAGNET_RELEASE_DWELL_S = float(os.environ.get("CHESS_MAGNET_RELEASE_DWELL_S", "0.3"))
    CHESS_MOVE_FEED_RATE = int(os.environ.get("CHESS_MOVE_FEED_RATE", "3000"))
    CHESS_CAPTURE_X_MM = float(os.environ.get("CHESS_CAPTURE_X_MM", "-30.0"))
    CHESS_CAPTURE_Y_MM = float(os.environ.get("CHESS_CAPTURE_Y_MM", "0.0"))
    CHESS_CAPTURE_SPACING_MM = float(os.environ.get("CHESS_CAPTURE_SPACING_MM", "15.0"))

    # File settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB uploads
    ENABLE_MANUAL_UPLOAD = os.environ.get("ENABLE_MANUAL_UPLOAD", "false").strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure required directories exist."""
        for directory in (cls.STORAGE_DIR, cls.UPLOAD_DIR, cls.GENERATED_DIR, cls.GCODE_DIR):
            directory.mkdir(parents=True, exist_ok=True)
