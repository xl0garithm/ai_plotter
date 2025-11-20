"""Utilities for converting images to G-code."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageFilter


class GCodeError(RuntimeError):
    """Raised when G-code generation fails."""


@dataclass
class GCodeSettings:
    """Settings controlling image-to-G-code conversion."""

    pixel_size_mm: float = 0.25
    feed_rate: int = 500
    travel_height: float = 5.0
    draw_height: float = 0.0
    invert_z: bool = False
    threshold: int = 200
    blur_radius: float = 1.5
    thinning_iterations: int = 20
    point_skip: int = 1
    min_move_mm: float = 0.25
    simplification_error: float = 0.1
    smoothing_iterations: int = 2


def image_to_gcode(image_path: Path, output_path: Path, settings: GCodeSettings | None = None) -> Path:
    """Convert a raster image to G-code file."""
    if settings is None:
        settings = GCodeSettings()

    if not image_path.exists():
        raise GCodeError(f"Image '{image_path}' does not exist.")

    image = Image.open(image_path).convert("L")
    if settings.blur_radius > 0:
        image = image.filter(ImageFilter.GaussianBlur(radius=settings.blur_radius))

    gray = np.array(image, dtype=np.uint8)
    mask = gray < settings.threshold

    if not mask.any():
        raise GCodeError("Thresholding removed all pixels; cannot produce outline.")

    skeleton = _zhang_suen_thinning(mask, iterations=settings.thinning_iterations)

    if not skeleton.any():
        raise GCodeError("Unable to derive skeleton from outline.")


    height, width = skeleton.shape
    pixel = settings.pixel_size_mm

    paths = _extract_paths(skeleton, settings.point_skip)

    if not paths:
        raise GCodeError("No drawable paths detected in skeleton.")

    commands: List[str] = []

    for path in paths:
        mm_points = _pixels_to_mm(path, height, pixel)
        
        # 1. Simplify jagged pixel path into vectors (RDP)
        if settings.simplification_error > 0:
            mm_points = _simplify_path_rdp(mm_points, settings.simplification_error)
            
        # 2. Smooth the sharp corners (Chaikin)
        if settings.smoothing_iterations > 0:
            mm_points = _smooth_path_chaikin(mm_points, settings.smoothing_iterations)
            
        # 3. Filter tiny leftover segments
        mm_points = _filter_min_move(mm_points, settings.min_move_mm)
        
        if len(mm_points) < 2:
            continue

        x0, y0 = mm_points[0]
        # Format to 1 decimal place for GRBL compatibility if needed, or keep 2 but ensure no trailing weirdness
        commands.append(f"G0 X{x0:.2f} Y{y0:.2f} ; move to start")
        commands.append(f"F{settings.feed_rate} ; set feed rate")
        commands.append("M3 S90 ; pen down")

        for x, y in mm_points:
            commands.append(f"G1 X{x:.2f} Y{y:.2f}")

        commands.append("M5 ; pen up")

    commands.extend(
        [
            "G0 X0.00 Y0.00 ; return to origin",
            "G4 P2.0 ; long dwell for home completion",
            "M5 ; pen up",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(commands), encoding="utf-8")
    return output_path


def _zhang_suen_thinning(mask: np.ndarray, iterations: int = 20) -> np.ndarray:
    """Perform Zhang-Suen thinning to produce a 1px-wide skeleton."""
    binary = mask.astype(np.uint8)
    rows, cols = binary.shape

    def _neighborhood(y: int, x: int) -> Tuple[int, ...]:
        return (
            binary[y - 1, x],
            binary[y - 1, x + 1],
            binary[y, x + 1],
            binary[y + 1, x + 1],
            binary[y + 1, x],
            binary[y + 1, x - 1],
            binary[y, x - 1],
            binary[y - 1, x - 1],
        )

    changed = True
    iter_count = 0
    while changed and (iterations is None or iter_count < iterations):
        changed = False
        iter_count += 1
        for step in (0, 1):
            to_remove = []
            for y in range(1, rows - 1):
                for x in range(1, cols - 1):
                    if binary[y, x] == 0:
                        continue
                    neighbors = _neighborhood(y, x)
                    transitions = sum(
                        neighbors[i] == 0 and neighbors[(i + 1) % 8] == 1 for i in range(8)
                    )
                    total = sum(neighbors)
                    if not (2 <= total <= 6 and transitions == 1):
                        continue
                    if step == 0:
                        if neighbors[0] * neighbors[2] * neighbors[4] != 0:
                            continue
                        if neighbors[2] * neighbors[4] * neighbors[6] != 0:
                            continue
                    else:
                        if neighbors[0] * neighbors[2] * neighbors[6] != 0:
                            continue
                        if neighbors[0] * neighbors[4] * neighbors[6] != 0:
                            continue
                    to_remove.append((y, x))
            if to_remove:
                changed = True
                for y, x in to_remove:
                    binary[y, x] = 0

    return binary.astype(bool)


NEIGHBOR_OFFSETS = [
    (-1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
]


def _extract_paths(mask: np.ndarray, point_skip: int) -> List[List[Tuple[int, int]]]:
    """Extract continuous paths from a skeleton mask."""
    working = mask.copy()
    paths: List[List[Tuple[int, int]]] = []

    while True:
        coords = np.argwhere(working)
        if coords.size == 0:
            break
        start = _choose_start(working, coords)
        path = _trace_path(working, start)
        if point_skip > 1:
            path = path[::point_skip]
        if len(path) >= 2:
            paths.append(path)

    return paths


def _choose_start(mask: np.ndarray, coords: np.ndarray) -> Tuple[int, int]:
    for y, x in coords:
        if _neighbor_count(mask, (y, x)) <= 1:
            return int(y), int(x)
    y, x = coords[0]
    return int(y), int(x)


def _neighbor_count(mask: np.ndarray, point: Tuple[int, int]) -> int:
    return sum(
        1
        for dy, dx in NEIGHBOR_OFFSETS
        if 0 <= point[0] + dy < mask.shape[0]
        and 0 <= point[1] + dx < mask.shape[1]
        and mask[point[0] + dy, point[1] + dx]
    )


def _trace_path(mask: np.ndarray, start: Tuple[int, int]) -> List[Tuple[int, int]]:
    path: List[Tuple[int, int]] = []
    current = start
    prev = None

    while True:
        path.append(current)
        y, x = current
        mask[y, x] = False
        neighbors = [
            (y + dy, x + dx)
            for dy, dx in NEIGHBOR_OFFSETS
            if 0 <= y + dy < mask.shape[0]
            and 0 <= x + dx < mask.shape[1]
            and mask[y + dy, x + dx]
        ]

        if not neighbors:
            break

        if prev and prev in neighbors and len(neighbors) > 1:
            neighbors.remove(prev)

        next_point = neighbors[0]
        prev = current
        current = next_point

    return path


def _simplify_path_rdp(points: List[Tuple[float, float]], epsilon: float) -> List[Tuple[float, float]]:
    """Simplify path using Ramer-Douglas-Peucker algorithm."""
    if len(points) < 3:
        return points

    # Find the point with the maximum distance
    dmax = 0.0
    index = 0
    end = len(points) - 1
    
    # Line defined by points[0] and points[end]
    x1, y1 = points[0]
    x2, y2 = points[end]
    
    # Precompute line vector
    dx = x2 - x1
    dy = y2 - y1
    
    # Normalize if length > 0
    line_len_sq = dx*dx + dy*dy
    
    if line_len_sq == 0:
        # Start and end are same, dist is dist to point
        for i in range(1, end):
            px, py = points[i]
            d = np.sqrt((px - x1)**2 + (py - y1)**2)
            if d > dmax:
                index = i
                dmax = d
    else:
        # Perpendicular distance formula
        for i in range(1, end):
            px, py = points[i]
            # Distance from point to line segment
            # |(y2-y1)x0 - (x2-x1)y0 + x2y1 - y2x1| / sqrt((y2-y1)^2 + (x2-x1)^2)
            num = abs(dy*px - dx*py + x2*y1 - y2*x1)
            d = num / np.sqrt(line_len_sq)
            if d > dmax:
                index = i
                dmax = d

    # If max distance is greater than epsilon, recursively simplify
    if dmax > epsilon:
        rec_results1 = _simplify_path_rdp(points[:index+1], epsilon)
        rec_results2 = _simplify_path_rdp(points[index:], epsilon)
        return rec_results1[:-1] + rec_results2
    else:
        return [points[0], points[end]]


def _smooth_path_chaikin(points: List[Tuple[float, float]], iterations: int = 1) -> List[Tuple[float, float]]:
    """Smooth path using Chaikin's algorithm (corner cutting)."""
    if len(points) < 3 or iterations < 1:
        return points

    current_points = points
    for _ in range(iterations):
        new_points = [current_points[0]]
        for i in range(len(current_points) - 1):
            p0 = current_points[i]
            p1 = current_points[i+1]
            
            # Cut at 25% and 75%
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            
            new_points.append(q)
            new_points.append(r)
        
        new_points.append(current_points[-1])
        current_points = new_points
        
    return current_points


def _pixels_to_mm(path: List[Tuple[int, int]], height: int, pixel_size: float) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    for row, col in path:
        x_mm = col * pixel_size
        y_mm = (height - row - 1) * pixel_size
        points.append((x_mm, y_mm))
    return points


def _filter_min_move(points: List[Tuple[float, float]], min_dist: float) -> List[Tuple[float, float]]:
    if not points or min_dist <= 0:
        return points

    filtered = [points[0]]
    last_x, last_y = points[0]
    for x, y in points[1:]:
        dx = x - last_x
        dy = y - last_y
        if dx * dx + dy * dy < min_dist * min_dist:
            continue
        filtered.append((x, y))
        last_x, last_y = x, y
    if filtered[-1] != points[-1]:
        filtered.append(points[-1])
    return filtered

