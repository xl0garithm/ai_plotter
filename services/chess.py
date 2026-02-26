"""Chess board vector generation for plotter."""

from __future__ import annotations

import math
from typing import List, Tuple

from services.vectorizer import VectorData

Point = Tuple[float, float]


def generate_chess_board(
    board_size: int = 800,
    squares: int = 8,
    hatch_spacing: float = 6.0,
) -> VectorData:
    """Generate chess board vector paths with hatched dark squares.

    Args:
        board_size: Total board size in pixels.
        squares: Number of squares per side (default 8 for standard chess).
        hatch_spacing: Spacing between diagonal hatching lines in pixels.

    Returns:
        VectorData with paths for grid lines and hatching.
    """
    paths: List[List[Point]] = []
    square_size = board_size / squares

    # Board outline
    paths.append([
        (0.0, 0.0),
        (float(board_size), 0.0),
        (float(board_size), float(board_size)),
        (0.0, float(board_size)),
        (0.0, 0.0),
    ])

    # Vertical grid lines
    for i in range(1, squares):
        x = i * square_size
        paths.append([(x, 0.0), (x, float(board_size))])

    # Horizontal grid lines
    for i in range(1, squares):
        y = i * square_size
        paths.append([(0.0, y), (float(board_size), y)])

    # Hatching for dark squares
    for row in range(squares):
        for col in range(squares):
            if (row + col) % 2 == 1:
                x0 = col * square_size
                y0 = row * square_size
                hatch_paths = _generate_hatch_lines(x0, y0, square_size, hatch_spacing)
                paths.extend(hatch_paths)

    return VectorData(width=board_size, height=board_size, paths=paths)


def _generate_hatch_lines(
    x0: float,
    y0: float,
    size: float,
    spacing: float,
) -> List[List[Point]]:
    """Generate diagonal hatching lines within a square at 45 degrees."""
    paths: List[List[Point]] = []

    # Generate lines from bottom-left to top-right (45 degree angle)
    # Lines are perpendicular to the direction (1, 1), so they run from
    # bottom-left to top-right of each line segment

    # We need to cover the square with parallel lines.
    # The diagonal of a square has length size * sqrt(2).
    # We'll generate lines by offsetting from the bottom-left corner.

    diagonal = size * math.sqrt(2)
    num_lines = int(diagonal / spacing) + 1

    for i in range(num_lines + 1):
        offset = i * spacing

        # Line starts from left or bottom edge, ends at top or right edge
        # Parametric: we're drawing lines where x + y = constant
        # offset 0: line through (x0, y0) - just the corner point
        # offset max: line through (x0 + size, y0 + size) - opposite corner

        # For line where (x - x0) + (y - y0) = offset:
        # Intersect with square boundaries

        line = _clip_diagonal_to_square(x0, y0, size, offset)
        if line and len(line) == 2:
            paths.append(line)

    return paths


def _clip_diagonal_to_square(
    x0: float,
    y0: float,
    size: float,
    offset: float,
) -> List[Point]:
    """Clip a 45-degree diagonal line to a square.

    The line satisfies: (x - x0) + (y - y0) = offset
    Rearranged: y = y0 + offset - (x - x0) = y0 + offset + x0 - x

    Returns two intersection points with the square boundary, or empty list.
    """
    x1 = x0 + size
    y1 = y0 + size

    intersections: List[Point] = []

    # Check intersection with left edge (x = x0)
    y_at_left = y0 + offset
    if y0 <= y_at_left <= y1:
        intersections.append((x0, y_at_left))

    # Check intersection with bottom edge (y = y0)
    x_at_bottom = x0 + offset
    if x0 < x_at_bottom <= x1:  # exclude corner already counted
        intersections.append((x_at_bottom, y0))

    # Check intersection with right edge (x = x1)
    y_at_right = y0 + offset - size
    if y0 <= y_at_right <= y1:
        intersections.append((x1, y_at_right))

    # Check intersection with top edge (y = y1)
    x_at_top = x0 + offset - size
    if x0 <= x_at_top < x1:  # exclude corner already counted
        intersections.append((x_at_top, y1))

    # Remove duplicates (corners) and ensure we have exactly 2 points
    unique: List[Point] = []
    for pt in intersections:
        is_dup = False
        for existing in unique:
            if abs(pt[0] - existing[0]) < 0.001 and abs(pt[1] - existing[1]) < 0.001:
                is_dup = True
                break
        if not is_dup:
            unique.append(pt)

    if len(unique) == 2:
        return unique
    return []


def uci_square_to_mm(
    file_char: str,
    rank_char: str,
    board_size_mm: float,
    square_count: int,
    origin_x: float,
    origin_y: float,
) -> tuple[float, float]:
    """Map UCI file/rank (e.g. e, 2) to square center in mm. Origin top-left; rank 8 at top."""
    square_size = board_size_mm / square_count
    file_idx = ord(file_char.lower()) - ord("a")
    rank = int(rank_char)
    x = origin_x + (file_idx + 0.5) * square_size
    y = origin_y + (8.5 - rank) * square_size
    return (x, y)


def move_to_gcode(
    uci_move: str,
    capture: bool,
    board_size_mm: float = 200.0,
    square_count: int = 8,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    dwell_s: float = 0.3,
    settle_after_place_s: float = 0.5,
) -> list[str]:
    """Convert one UCI move to G-code for electromagnet arm: go to from, magnet on, dwell, go to to, magnet off, settle. If capture, first move captured piece to discard. Pieces assumed same height so lifted piece clears board."""
    square_size = board_size_mm / square_count
    discard_x = origin_x - square_size * 1.5
    discard_y = origin_y - square_size * 1.5
    lines: list[str] = []
    lines.append("M5 ; electromagnet off")
    from_sq = uci_move[:2]
    to_sq = uci_move[2:4]
    fx, fy = uci_square_to_mm(from_sq[0], from_sq[1], board_size_mm, square_count, origin_x, origin_y)
    tx, ty = uci_square_to_mm(to_sq[0], to_sq[1], board_size_mm, square_count, origin_x, origin_y)
    if capture:
        lines.append(f"G0 X{tx:.2f} Y{ty:.2f} ; to capture square")
        lines.append("M3 S90 ; electromagnet on")
        lines.append(f"G4 P{dwell_s:.2f} ; pickup dwell")
        lines.append(f"G0 X{discard_x:.2f} Y{discard_y:.2f} ; to discard")
        lines.append("M5 ; electromagnet off")
        lines.append(f"G4 P{settle_after_place_s:.2f} ; settle after place")
    lines.append(f"G0 X{fx:.2f} Y{fy:.2f} ; from {from_sq}")
    lines.append("M3 S90 ; electromagnet on")
    lines.append(f"G4 P{dwell_s:.2f} ; pickup dwell")
    lines.append(f"G0 X{tx:.2f} Y{ty:.2f} ; to {to_sq}")
    lines.append("M5 ; electromagnet off")
    lines.append(f"G4 P{settle_after_place_s:.2f} ; settle after place")
    return lines


def generate_chess_demo_gcode(
    board_size_mm: float = 200.0,
    square_count: int = 8,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    tap_dwell_s: float = 0.3,
) -> tuple[list[str], dict]:
    """Generate G-code that moves to every square center and taps.

    Traversal order: row by row top-to-bottom (rank 8→1), left-to-right (a→h).

    Returns:
        Tuple of (gcode_lines, stats_dict).
    """
    square_size = board_size_mm / square_count
    total_squares = square_count * square_count
    lines: list[str] = []

    lines.append(f"; Chess demo: {total_squares} squares, {square_size:.1f}mm each")
    lines.append("M5 ; ensure head up")

    files = "abcdefgh"
    for row in range(square_count):
        rank = square_count - row  # row 0 = rank 8
        for col in range(square_count):
            file_letter = files[col] if col < len(files) else str(col)
            x = origin_x + col * square_size + square_size / 2
            y = origin_y + row * square_size + square_size / 2

            lines.append(f"G0 X{x:.2f} Y{y:.2f} ; {file_letter}{rank}")
            lines.append("M3 S90 ; head down")
            lines.append(f"G4 P{tap_dwell_s:.2f} ; tap dwell")
            lines.append("M5 ; head up")
            lines.append("G4 P0.05 ; settle")

    lines.append("G0 X0.00 Y0.00 ; return home")
    lines.append("G4 P2.0 ; final settle")
    lines.append("M5 ; final head up")

    # Estimate time: rapid moves ~100mm/s, plus dwell per square
    total_travel_mm = 0.0
    prev_x, prev_y = 0.0, 0.0
    for row in range(square_count):
        for col in range(square_count):
            x = origin_x + col * square_size + square_size / 2
            y = origin_y + row * square_size + square_size / 2
            total_travel_mm += math.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)
            prev_x, prev_y = x, y
    # Return home
    total_travel_mm += math.sqrt(prev_x ** 2 + prev_y ** 2)

    travel_time_s = total_travel_mm / 100.0
    dwell_time_s = total_squares * (tap_dwell_s + 0.05) + 2.0
    estimated_time_s = travel_time_s + dwell_time_s

    stats = {
        "total_squares": total_squares,
        "square_size_mm": round(square_size, 2),
        "estimated_seconds": round(estimated_time_s, 1),
        "gcode_lines": len(lines),
    }

    return lines, stats


def generate_chess_demo_svg(
    board_size_mm: float = 200.0,
    square_count: int = 8,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    svg_size: int = 500,
) -> str:
    """Generate an SVG preview of the demo traversal.

    Shows the board grid with numbered dots at each square center.
    """
    square_size = board_size_mm / square_count
    # Scale from mm to SVG pixels
    scale = svg_size / board_size_mm
    margin = 20  # px padding around board
    total_size = svg_size + 2 * margin

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_size}" height="{total_size}" '
        f'viewBox="0 0 {total_size} {total_size}" '
        f'font-family="monospace" font-size="10">',
        f'<rect x="0" y="0" width="{total_size}" height="{total_size}" fill="#f5f5f0"/>',
    ]

    # Draw alternating light/dark squares
    for row in range(square_count):
        for col in range(square_count):
            sx = margin + col * square_size * scale
            sy = margin + row * square_size * scale
            fill = "#d4a574" if (row + col) % 2 == 1 else "#f0dab5"
            parts.append(
                f'<rect x="{sx:.1f}" y="{sy:.1f}" '
                f'width="{square_size * scale:.1f}" height="{square_size * scale:.1f}" '
                f'fill="{fill}" stroke="#8b7355" stroke-width="0.5"/>'
            )

    # Board outline
    parts.append(
        f'<rect x="{margin}" y="{margin}" '
        f'width="{svg_size}" height="{svg_size}" '
        f'fill="none" stroke="#333" stroke-width="2"/>'
    )

    # File labels (a-h) along bottom
    files = "abcdefgh"
    for col in range(square_count):
        cx = margin + col * square_size * scale + square_size * scale / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{total_size - 4}" '
            f'text-anchor="middle" fill="#555" font-size="11">'
            f'{files[col] if col < len(files) else col}</text>'
        )

    # Rank labels (8-1) along left
    for row in range(square_count):
        cy = margin + row * square_size * scale + square_size * scale / 2
        rank = square_count - row
        parts.append(
            f'<text x="{margin - 6}" y="{cy + 4:.1f}" '
            f'text-anchor="end" fill="#555" font-size="11">'
            f'{rank}</text>'
        )

    # Numbered dots at each square center (traversal order)
    dot_radius = max(4, min(12, svg_size / square_count / 4))
    font_size = max(6, min(9, dot_radius * 1.2))
    num = 0
    for row in range(square_count):
        for col in range(square_count):
            num += 1
            cx = margin + (origin_x + col * square_size + square_size / 2) * scale
            cy = margin + (origin_y + row * square_size + square_size / 2) * scale
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{dot_radius:.1f}" '
                f'fill="rgba(220,50,50,0.85)" stroke="#fff" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{cx:.1f}" y="{cy + font_size * 0.35:.1f}" '
                f'text-anchor="middle" fill="#fff" font-size="{font_size:.1f}" '
                f'font-weight="bold">{num}</text>'
            )

    # Draw traversal path as a faint connecting line
    parts.append('<polyline points="')
    points_str = []
    for row in range(square_count):
        for col in range(square_count):
            cx = margin + (origin_x + col * square_size + square_size / 2) * scale
            cy = margin + (origin_y + row * square_size + square_size / 2) * scale
            points_str.append(f"{cx:.1f},{cy:.1f}")
    parts.append(" ".join(points_str))
    parts.append('" fill="none" stroke="rgba(220,50,50,0.3)" stroke-width="1.5" stroke-dasharray="4,3"/>')

    parts.append("</svg>")
    return "\n".join(parts)


def chess_board_to_svg(
    vector_data: VectorData,
    stroke_width: float = 2.0,
) -> str:
    """Convert chess board VectorData to SVG string for preview."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{vector_data.width}" height="{vector_data.height}" '
        f'viewBox="0 0 {vector_data.width} {vector_data.height}" '
        f'fill="none" stroke="black" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round">',
    ]

    for path in vector_data.paths:
        if len(path) < 2:
            continue
        d_parts = [f"M {path[0][0]:.2f} {path[0][1]:.2f}"]
        for x, y in path[1:]:
            d_parts.append(f"L {x:.2f} {y:.2f}")
        lines.append(f'<path d="{" ".join(d_parts)}" />')

    lines.append("</svg>")
    return "\n".join(lines)
