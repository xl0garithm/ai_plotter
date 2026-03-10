"""Utilities for converting images to G-code."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from services.vectorizer import VectorData


class GCodeError(RuntimeError):
    """Raised when G-code generation fails."""


@dataclass
class GCodeSettings:
    """Settings controlling image-to-G-code conversion."""

    pixel_size_mm: float = 0.25
    feed_rate: int = 10000
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
    pen_dwell_seconds: float = 0.0


@dataclass
class GCodeStats:
    """Summary metrics for a generated G-code file."""

    total_draw_mm: float
    total_travel_mm: float
    estimated_seconds: float
    path_count: int
    line_count: int


def _validate_feed_rate(settings: GCodeSettings) -> None:
    if settings.feed_rate is None or settings.feed_rate <= 0:
        raise GCodeError("Feed rate must be a positive value.")


def vector_data_to_gcode(
    vector_data: VectorData, output_path: Path, settings: GCodeSettings | None = None
) -> GCodeStats:
    """Convert traced vector paths directly into G-code and return draw statistics."""
    if settings is None:
        settings = GCodeSettings()
    _validate_feed_rate(settings)

    if not vector_data.paths:
        raise GCodeError("Vector data did not contain any drawable paths.")

    if vector_data.width <= 0 or vector_data.height <= 0:
        raise GCodeError("Vector data has invalid dimensions.")

    commands: list[str] = []
    pixel = settings.pixel_size_mm
    height = vector_data.height
    total_draw_mm = 0.0
    total_travel_mm = 0.0
    path_count = 0
    prev_endpoint: tuple[float, float] | None = None

    for path in vector_data.paths:
        if len(path) < 2:
            continue

        mm_points = [(x * pixel, (height - y - 1) * pixel) for x, y in path]
        mm_points = _filter_min_move(mm_points, settings.min_move_mm)
        if len(mm_points) < 2:
            continue

        travel_start = prev_endpoint if prev_endpoint is not None else (0.0, 0.0)
        total_travel_mm += _distance(travel_start, mm_points[0])

        path_length = _path_length(mm_points)
        total_draw_mm += path_length
        prev_endpoint = mm_points[-1]
        path_count += 1

        x0, y0 = mm_points[0]
        commands.append(f"G0 X{x0:.2f} Y{y0:.2f} ; move to start")
        commands.append(f"F{settings.feed_rate} ; set feed rate")
        commands.append("M3 S90 ; pen down")
        if settings.pen_dwell_seconds > 0:
            commands.append(f"G4 P{settings.pen_dwell_seconds:.2f} ; dwell")

        for x, y in mm_points:
            commands.append(f"G1 X{x:.2f} Y{y:.2f}")

        commands.append("M5 ; pen up")
        if settings.pen_dwell_seconds > 0:
            commands.append(f"G4 P{settings.pen_dwell_seconds:.2f} ; dwell")

    if not commands:
        raise GCodeError("Vector data did not produce drawable paths.")

    if prev_endpoint is not None:
        total_travel_mm += _distance(prev_endpoint, (0.0, 0.0))

    commands.extend(
        [
            "G0 X0.00 Y0.00 ; return to origin",
            "G4 P2.0 ; long dwell for home completion",
            "M5 ; pen up",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(commands), encoding="utf-8")

    feed_rate_mm_per_min = max(settings.feed_rate, 1)
    draw_minutes = total_draw_mm / feed_rate_mm_per_min
    travel_minutes = total_travel_mm / feed_rate_mm_per_min
    dwell_seconds = path_count * settings.pen_dwell_seconds * 2
    estimated_seconds = max(draw_minutes + travel_minutes, 0.0) * 60.0 + dwell_seconds + 5.0

    total_gcode_lines = len(commands)

    return GCodeStats(
        total_draw_mm=total_draw_mm,
        total_travel_mm=total_travel_mm,
        estimated_seconds=estimated_seconds,
        path_count=path_count,
        line_count=total_gcode_lines,
    )


def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _path_length(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    return sum(_distance(points[i], points[i + 1]) for i in range(len(points) - 1))


def _filter_min_move(
    points: list[tuple[float, float]], min_dist: float
) -> list[tuple[float, float]]:
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
