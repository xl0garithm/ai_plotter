"""PNG-to-vector utilities for plotter pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from PIL import Image
from skimage import measure

Point = Tuple[float, float]


@dataclass
class VectorData:
    """Container for traced vector paths."""

    width: int
    height: int
    paths: List[List[Point]]


def _rdp(points: Sequence[Point], epsilon: float) -> List[Point]:
    """Ramer-Douglas-Peucker simplification."""
    if len(points) < 3 or epsilon <= 0:
        return list(points)

    start, end = np.array(points[0]), np.array(points[-1])
    line = end - start
    if np.allclose(line, 0):
        distances = np.linalg.norm(np.array(points) - start, axis=1)
    else:
        line_norm = np.linalg.norm(line)
        distances = np.abs(np.cross(line, np.array(points) - start)) / line_norm

    idx = int(np.argmax(distances))
    max_distance = distances[idx]
    if max_distance <= epsilon:
        return [points[0], points[-1]]

    first_half = _rdp(points[: idx + 1], epsilon)
    second_half = _rdp(points[idx:], epsilon)
    return first_half[:-1] + second_half


def _downsample(points: Sequence[Point], step: int) -> List[Point]:
    if step <= 1:
        return list(points)
    return list(points)[:: step]


def vectorize_image(
    image_path: Path,
    *,
    threshold: int = 230,
    simplify_tolerance: float = 2.0,
    min_path_points: int = 24,
    downsample_step: int = 1,
) -> VectorData:
    """Convert a black/white PNG into vector paths using contour tracing."""

    image = Image.open(image_path).convert("L")
    width, height = image.size
    arr = np.array(image)
    mask = arr < threshold  # True for strokes

    # skimage coordinates are (row, col); convert to (x, y) later
    contours = measure.find_contours(mask.astype(float), 0.5)
    paths: List[List[Point]] = []

    for contour in contours:
        # contour is N x 2 array of [row, col]
        if contour.shape[0] < min_path_points:
            continue
        simplified = _rdp([(c[1], c[0]) for c in contour], simplify_tolerance)
        simplified = _downsample(simplified, downsample_step)
        if len(simplified) < min_path_points // 2:
            continue
        paths.append(simplified)

    return VectorData(width=width, height=height, paths=paths)


def save_vector_data(data: VectorData, output_path: Path) -> Path:
    payload = {
        "width": data.width,
        "height": data.height,
        "paths": [[[float(x), float(y)] for x, y in path] for path in data.paths],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload), encoding="utf-8")
    return output_path


def load_vector_data(path: Path) -> VectorData:
    payload = json.loads(path.read_text(encoding="utf-8"))
    paths = [
        [(float(x), float(y)) for x, y in path_points]
        for path_points in payload.get("paths", [])
    ]
    return VectorData(
        width=int(payload.get("width", 0)),
        height=int(payload.get("height", 0)),
        paths=paths,
    )


def save_svg(data: VectorData, output_path: Path, *, stroke_px: float = 3.0) -> Path:
    """Write a minimal SVG representation for debugging and preview."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    svg_lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{data.width}" height="{data.height}" viewBox="0 0 {data.width} {data.height}" fill="none" stroke="black" stroke-width="{stroke_px}" stroke-linecap="round" stroke-linejoin="round">',
    ]

    for path in data.paths:
        if len(path) < 2:
            continue
        d = " ".join(
            ["M {:.2f} {:.2f}".format(*path[0])]
            + ["L {:.2f} {:.2f}".format(x, y) for x, y in path[1:]]
        )
        svg_lines.append(f'<path d="{d}" />')

    svg_lines.append("</svg>")
    output_path.write_text("\n".join(svg_lines), encoding="utf-8")
    return output_path

