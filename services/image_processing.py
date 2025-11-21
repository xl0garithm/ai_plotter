"""Image processing utilities."""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Tuple

from PIL import Image
from werkzeug.datastructures import FileStorage


def generate_asset_key(job_id: int) -> str:
    """Generate a stable asset basename for a job's artifacts."""
    if job_id is None:
        raise ValueError("job_id is required to generate an asset key.")
    random_part = uuid.uuid4().hex[:8]
    return f"{job_id}-{random_part}"


def save_upload(file: FileStorage, destination: Path) -> Path:
    """Save an uploaded file to the destination path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    file.save(destination)
    return destination


def resize_image_bytes(image_bytes: bytes, size: Tuple[int, int] = (400, 400)) -> bytes:
    """Resize image bytes to the specified size."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        resized = img.resize(size, Image.LANCZOS)
        buffer = io.BytesIO()
        resized.save(buffer, format="PNG")
        return buffer.getvalue()


def save_image_bytes(image_bytes: bytes, destination: Path) -> Path:
    """Save image bytes to the destination path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as fp:
        fp.write(image_bytes)
    return destination

