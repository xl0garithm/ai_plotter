"""Application configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path

_CHESS_JSON_KEYS = (
    "board_size_mm",
    "square_count",
    "origin_x_mm",
    "origin_y_mm",
    "discard_offset_squares",
)


def _load_chess_dimensions_json() -> dict | None:
    """Load chess dimensions from optional JSON file (e.g. exported from CAD). Returns None if not set or invalid."""
    path = os.environ.get("CHESS_DIMENSIONS_JSON", "").strip()
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {k: data[k] for k in _CHESS_JSON_KEYS if k in data}
    except (OSError, json.JSONDecodeError, TypeError):
        return None


_chess_json = _load_chess_dimensions_json()
_CHESS_DEFAULTS = {
    "board_size_mm": 200.0,
    "square_count": 8,
    "origin_x_mm": 0.0,
    "origin_y_mm": 0.0,
    "discard_offset_squares": 1.5,
}
if _chess_json:
    _CHESS_DEFAULTS.update(_chess_json)


class Config:
    """Base configuration for the AI plotter application.

    Values are read from the environment when the instance is constructed so
    ``load_dotenv()`` and per-process env (e.g. ``PLOTTER_DRY_RUN``) apply correctly.
    """

    BASE_DIR = Path(__file__).resolve().parent

    def __init__(self) -> None:
        self.STORAGE_DIR = self.BASE_DIR / "storage"
        self.UPLOAD_DIR = self.STORAGE_DIR / "uploads"
        self.GENERATED_DIR = self.STORAGE_DIR / "processed"
        self.GCODE_DIR = self.STORAGE_DIR / "gcode"
        self.DB_PATH = self.STORAGE_DIR / "app.db"

        self.SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-this-secret")
        self.ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")
        self.DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{self.DB_PATH}")

        self.SERIAL_PORT = os.environ.get("PLOTTER_SERIAL_PORT", "COM3")
        self.SERIAL_BAUDRATE = int(os.environ.get("PLOTTER_BAUDRATE", "115200"))
        self.SERIAL_TIMEOUT = float(os.environ.get("PLOTTER_SERIAL_TIMEOUT", "10.0"))
        self.PLOTTER_DRY_RUN = os.environ.get("PLOTTER_DRY_RUN", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.PLOTTER_INVERT_Z = os.environ.get("PLOTTER_INVERT_Z", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.PLOTTER_LINE_DELAY = float(os.environ.get("PLOTTER_LINE_DELAY", "0.1"))

        self.MAX_RETRY = int(os.environ.get("PLOTTER_MAX_RETRY", "3"))

        self.VECTOR_RESOLUTION = int(os.environ.get("PLOTTER_VECTOR_RESOLUTION", "1600"))
        self.VECTORIZE_THRESHOLD = int(os.environ.get("PLOTTER_VECTORIZE_THRESHOLD", "240"))
        self.VECTORIZE_SIMPLIFY_PX = float(os.environ.get("PLOTTER_VECTORIZE_SIMPLIFY_PX", "2.0"))
        self.VECTORIZE_MIN_POINTS = int(os.environ.get("PLOTTER_VECTORIZE_MIN_POINTS", "24"))
        self.VECTORIZE_DOWNSAMPLE_STEP = int(
            os.environ.get("PLOTTER_VECTORIZE_DOWNSAMPLE_STEP", "1")
        )
        self.VECTORIZE_STROKE_WIDTH = float(os.environ.get("PLOTTER_VECTORIZE_STROKE_WIDTH", "3.0"))
        self.VECTORIZE_CROP_PADDING_RATIO = float(
            os.environ.get("PLOTTER_VECTORIZE_CROP_PADDING_RATIO", "0.05")
        )

        self.PLOTTER_FEED_RATE = int(os.environ.get("PLOTTER_FEED_RATE", "5000"))

        self.CHESS_BOARD_SIZE_MM = float(
            os.environ.get("CHESS_BOARD_SIZE_MM", str(_CHESS_DEFAULTS["board_size_mm"]))
        )
        self.CHESS_SQUARE_COUNT = int(
            os.environ.get("CHESS_SQUARE_COUNT", str(_CHESS_DEFAULTS["square_count"]))
        )
        self.CHESS_ORIGIN_X_MM = float(
            os.environ.get("CHESS_ORIGIN_X_MM", str(_CHESS_DEFAULTS["origin_x_mm"]))
        )
        self.CHESS_ORIGIN_Y_MM = float(
            os.environ.get("CHESS_ORIGIN_Y_MM", str(_CHESS_DEFAULTS["origin_y_mm"]))
        )
        self.CHESS_DISCARD_OFFSET_SQUARES = float(
            os.environ.get(
                "CHESS_DISCARD_OFFSET_SQUARES",
                str(_CHESS_DEFAULTS["discard_offset_squares"]),
            )
        )
        self.CHESS_TAP_DWELL_S = float(os.environ.get("CHESS_TAP_DWELL_S", "0.3"))
        self.CHESS_MAGNET_SETTLE_S = float(os.environ.get("CHESS_MAGNET_SETTLE_S", "0.5"))
        self.CHESS_RAPID_FEED_MM_S = float(os.environ.get("CHESS_RAPID_FEED_MM_S", "100.0"))
        _mag_max = os.environ.get("CHESS_MAGNET_MAX_ON_S", "").strip()
        self.CHESS_MAGNET_MAX_ON_S = float(_mag_max) if _mag_max else None

        self.MAX_CONTENT_LENGTH = 16 * 1024 * 1024
        self.ENABLE_MANUAL_UPLOAD = os.environ.get(
            "ENABLE_MANUAL_UPLOAD", "false"
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        for directory in (self.STORAGE_DIR, self.UPLOAD_DIR, self.GENERATED_DIR, self.GCODE_DIR):
            directory.mkdir(parents=True, exist_ok=True)
