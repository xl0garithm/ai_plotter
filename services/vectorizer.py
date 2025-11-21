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


def crop_and_scale_vector_data(
    data: VectorData,
    *,
    padding_ratio: float = 0.05,
    target_dimension: int | None = None,
) -> VectorData:
    """Trim extra whitespace and scale vectors to fill the target dimension."""

    if not data.paths:
        return data

    all_x: List[float] = []
    all_y: List[float] = []
    for path in data.paths:
        for x, y in path:
            all_x.append(float(x))
            all_y.append(float(y))

    if not all_x or not all_y:
        return data

    min_x = min(all_x)
    max_x = max(all_x)
    min_y = min(all_y)
    max_y = max(all_y)

    content_width = max_x - min_x
    content_height = max_y - min_y
    if content_width <= 0 or content_height <= 0:
        return data

    padding_ratio = max(0.0, padding_ratio)
    pad = max(content_width, content_height) * padding_ratio

    crop_min_x = max(min_x - pad, 0.0)
    crop_min_y = max(min_y - pad, 0.0)
    crop_max_x = min(max_x + pad, float(data.width))
    crop_max_y = min(max_y + pad, float(data.height))

    new_width = crop_max_x - crop_min_x
    new_height = crop_max_y - crop_min_y
    if new_width <= 0 or new_height <= 0:
        return data

    target = target_dimension or max(data.width, data.height)
    scale = 1.0
    max_extent = max(new_width, new_height)
    if target and max_extent > 0:
        scale = target / max_extent

    scaled_paths: List[List[Point]] = []
    for path in data.paths:
        scaled_paths.append(
            [((x - crop_min_x) * scale, (y - crop_min_y) * scale) for x, y in path]
        )

    scaled_width = max(1, int(round(new_width * scale)))
    scaled_height = max(1, int(round(new_height * scale)))

    return VectorData(width=scaled_width, height=scaled_height, paths=scaled_paths)


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

