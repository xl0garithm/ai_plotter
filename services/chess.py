"""Chess board vector generation and move G-code for plotter."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from services.electromagnet import MAGNET_GCODE_OFF, MAGNET_GCODE_ON
from services.vectorizer import VectorData

Point = Tuple[float, float]

FILES = "abcdefgh"


@dataclass
class ChessMoveData:
    """Parsed chess move from chess.js verbose format."""

    from_sq: str  # e.g. "e2"
    to_sq: str  # e.g. "e4"
    piece: str  # p, n, b, r, q, k
    color: str  # w or b
    captured: Optional[str]  # piece type captured, or None
    flags: str  # chess.js flags: n=normal, b=pawn push, e=en passant, c=capture, k=kingside castle, q=queenside castle
    promotion: Optional[str]  # piece type promoted to, or None
    capture_index: int = 0  # Nth captured piece (for discard positioning)


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


# --- UCI helpers (simple grid without inter-square gaps; used by execute-move UCI path) ---

_CASTLING_ROOK_UCI: dict[str, str] = {
    "e1g1": "h1f1",
    "e1c1": "a1d1",
    "e8g8": "h8f8",
    "e8c8": "a8d8",
}


def plotter_uci_legs(uci_move: str) -> list[str]:
    """Expand one logical move into 4-char UCI legs for the physical board.

    Castling is two pick-place motions (king, then rook). Other moves are a single leg;
    promotion may use a 5-character UCI — only the first four are used for coordinates.
    """
    u = uci_move.strip()
    base = u[:4]
    if base in _CASTLING_ROOK_UCI:
        return [base, _CASTLING_ROOK_UCI[base]]
    return [base]


def uci_square_to_mm(
    file_char: str,
    rank_char: str,
    board_size_mm: float,
    square_count: int,
    origin_x: float,
    origin_y: float,
) -> tuple[float, float]:
    """Map UCI file/rank (e.g. e, 2) to square center in mm. Origin top-left; highest rank at top."""
    square_size = board_size_mm / square_count
    file_idx = ord(file_char.lower()) - ord("a")
    rank = int(rank_char)
    x = origin_x + (file_idx + 0.5) * square_size
    y = origin_y + (square_count + 0.5 - rank) * square_size
    return (x, y)


def move_to_gcode(
    uci_move: str,
    capture: bool,
    board_size_mm: float = 200.0,
    square_count: int = 8,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    discard_offset_squares: float = 1.5,
    dwell_s: float = 0.3,
    settle_after_place_s: float = 0.5,
    captured_piece_square: str | None = None,
) -> list[str]:
    """Convert one UCI leg to G-code (M3/M5 style) for a uniform square grid without gaps."""
    square_size = board_size_mm / square_count
    discard_x = origin_x - square_size * discard_offset_squares
    discard_y = origin_y - square_size * discard_offset_squares
    lines: list[str] = []
    lines.append("M5 ; electromagnet off")
    from_sq = uci_move[:2]
    to_sq = uci_move[2:4]
    fx, fy = uci_square_to_mm(
        from_sq[0], from_sq[1], board_size_mm, square_count, origin_x, origin_y
    )
    tx, ty = uci_square_to_mm(to_sq[0], to_sq[1], board_size_mm, square_count, origin_x, origin_y)
    if capture:
        if captured_piece_square and len(captured_piece_square) >= 2:
            cx, cy = uci_square_to_mm(
                captured_piece_square[0],
                captured_piece_square[1],
                board_size_mm,
                square_count,
                origin_x,
                origin_y,
            )
            cap_comment = f"en passant victim {captured_piece_square}"
        else:
            cx, cy = tx, ty
            cap_comment = "capture square"
        lines.append(f"G0 X{cx:.2f} Y{cy:.2f} ; to {cap_comment}")
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


def _square_center_mm(
    row: int,
    col: int,
    square_size: float,
    gap_mm: float,
    origin_x: float,
    origin_y: float,
) -> tuple[float, float]:
    """Return the (x, y) center of a board square in mm.

    Layout per axis: gap | square | gap | square | ... | square | gap
    So square i starts at: gap + i * (square_size + gap).
    """
    x = origin_x + gap_mm + col * (square_size + gap_mm) + square_size / 2
    y = origin_y + gap_mm + row * (square_size + gap_mm) + square_size / 2
    return x, y


def algebraic_to_mm(
    square: str,
    square_size: float,
    gap_mm: float,
    origin_x: float,
    origin_y: float,
    square_count: int = 8,
    mirror_ranks: bool = False,
) -> tuple[float, float]:
    """Convert algebraic notation (e.g. 'e4') to (x_mm, y_mm) center coordinates."""
    file_idx = FILES.index(square[0])  # col: a=0, h=7
    rank = int(square[1])  # 1-8
    row = rank - 1 if mirror_ranks else square_count - rank  # row 0 = rank 8 (top) unless mirrored
    return _square_center_mm(row, file_idx, square_size, gap_mm, origin_x, origin_y)


def _magnet_on_gcode(cmd: str, dwell: float) -> list[str]:
    """G-code lines to engage the electromagnet."""
    lines = []
    for part in cmd.split("\n"):
        part = part.strip()
        if part:
            lines.append(f"{part} ; magnet ON")
    lines.append(f"G4 P{dwell:.2f} ; engage dwell")
    return lines


def _magnet_off_gcode(cmd: str, dwell: float) -> list[str]:
    """G-code lines to disengage the electromagnet."""
    lines = []
    for part in cmd.split("\n"):
        part = part.strip()
        if part:
            lines.append(f"{part} ; magnet OFF")
    lines.append(f"G4 P{dwell:.2f} ; release dwell")
    return lines


def _pick_piece(
    x: float,
    y: float,
    magnet_on_cmd: str,
    engage_dwell: float,
    comment: str = "",
) -> list[str]:
    """G-code to move to a position and pick up a piece with the magnet."""
    label = f" ; pick {comment}" if comment else ""
    lines = [f"G0 X{x:.2f} Y{y:.2f}{label}"]
    lines.extend(_magnet_on_gcode(magnet_on_cmd, engage_dwell))
    return lines


def _place_piece(
    x: float,
    y: float,
    feed_rate: int,
    magnet_off_cmd: str,
    release_dwell: float,
    comment: str = "",
) -> list[str]:
    """G-code to carry a piece to a position (G1) and release it."""
    label = f" ; place {comment}" if comment else ""
    lines = [
        f"G1 X{x:.2f} Y{y:.2f} F{feed_rate}{label}",
        "G4 P0 ; sync — drain motion buffer before magnet off",
    ]
    lines.extend(_magnet_off_gcode(magnet_off_cmd, release_dwell))
    return lines


def _capture_discard_position(
    index: int,
    capture_x: float,
    capture_y: float,
    capture_spacing: float,
) -> tuple[float, float]:
    """Return the (x, y) position for the Nth captured/discarded piece."""
    return (capture_x, capture_y + index * capture_spacing)


def _pick_and_carry(
    from_xy: tuple[float, float],
    to_xy: tuple[float, float],
    magnet_on_cmd: str,
    magnet_off_cmd: str,
    engage_dwell: float,
    release_dwell: float,
    move_feed_rate: int,
    comment: str = "",
) -> list[str]:
    """Generate one pick-and-carry phase: rapid to source, magnet on, carry, magnet off."""
    label = f" ; {comment}" if comment else ""
    lines = [
        f"G0 X{from_xy[0]:.2f} Y{from_xy[1]:.2f}{label}",
    ]
    lines.extend(_magnet_on_gcode(magnet_on_cmd, engage_dwell))
    lines.append(f"G1 X{to_xy[0]:.2f} Y{to_xy[1]:.2f} F{move_feed_rate}")
    lines.append("G4 P0 ; sync — drain motion buffer")
    lines.extend(_magnet_off_gcode(magnet_off_cmd, release_dwell))
    return lines


def generate_move_gcode(
    move: ChessMoveData,
    board_size_mm: float = 215.9,
    square_count: int = 8,
    gap_mm: float = 2.0,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    mirror_ranks: bool = False,
    magnet_on_cmd: str = "M3 S255",
    magnet_off_cmd: str = "M3 S0\nM5",
    engage_dwell: float = 0.3,
    release_dwell: float = 0.3,
    move_feed_rate: int = 3000,
    capture_x: float = -30.0,
    capture_y: float = 0.0,
    capture_spacing: float = 15.0,
) -> tuple[list[list[str]], dict]:
    """Generate G-code phases for a single chess move.

    Move types:
    - Normal: 1 phase (pick piece, carry to target)
    - Capture: 2 phases (discard captured piece, then move piece)
    - En passant: 2 phases (discard en-passant pawn, then move piece)
    - Castling: 2 phases (move king, then move rook)

    Returns:
        Tuple of (list_of_phases, stats_dict).
        Each phase is a list of G-code lines.
    """
    square_size = (board_size_mm - (square_count + 1) * gap_mm) / square_count
    phases: list[list[str]] = []

    def sq_mm(sq: str) -> tuple[float, float]:
        return algebraic_to_mm(sq, square_size, gap_mm, origin_x, origin_y, square_count, mirror_ranks)

    from_xy = sq_mm(move.from_sq)
    to_xy = sq_mm(move.to_sq)

    # --- Handle capture: discard captured piece first ---
    if "e" in move.flags:
        # En passant: captured pawn is at target_file + source_rank
        ep_square = f"{move.to_sq[0]}{move.from_sq[1]}"
        ep_xy = sq_mm(ep_square)
        discard_xy = _capture_discard_position(
            move.capture_index, capture_x, capture_y, capture_spacing
        )
        phase = [f"; En passant: discard pawn at {ep_square}"]
        phase.extend(_pick_and_carry(ep_xy, discard_xy, magnet_on_cmd, magnet_off_cmd, engage_dwell, release_dwell, move_feed_rate, f"discard {ep_square}"))
        phases.append(phase)
    elif "c" in move.flags:
        discard_xy = _capture_discard_position(
            move.capture_index, capture_x, capture_y, capture_spacing
        )
        phase = [f"; Capture: discard piece at {move.to_sq}"]
        phase.extend(_pick_and_carry(to_xy, discard_xy, magnet_on_cmd, magnet_off_cmd, engage_dwell, release_dwell, move_feed_rate, f"discard {move.to_sq}"))
        phases.append(phase)

    # --- Move the piece ---
    phase = [f"; Move {move.piece} {move.from_sq} -> {move.to_sq}"]
    phase.extend(_pick_and_carry(from_xy, to_xy, magnet_on_cmd, magnet_off_cmd, engage_dwell, release_dwell, move_feed_rate, f"{move.piece} {move.from_sq}->{move.to_sq}"))
    phases.append(phase)

    # --- Handle castling: also move the rook ---
    if "k" in move.flags:
        rank = move.from_sq[1]
        rook_from_xy = sq_mm(f"h{rank}")
        rook_to_xy = sq_mm(f"f{rank}")
        phase = [f"; Kingside castle: rook h{rank} -> f{rank}"]
        phase.extend(_pick_and_carry(rook_from_xy, rook_to_xy, magnet_on_cmd, magnet_off_cmd, engage_dwell, release_dwell, move_feed_rate, f"rook h{rank}->f{rank}"))
        phases.append(phase)
    elif "q" in move.flags:
        rank = move.from_sq[1]
        rook_from_xy = sq_mm(f"a{rank}")
        rook_to_xy = sq_mm(f"d{rank}")
        phase = [f"; Queenside castle: rook a{rank} -> d{rank}"]
        phase.extend(_pick_and_carry(rook_from_xy, rook_to_xy, magnet_on_cmd, magnet_off_cmd, engage_dwell, release_dwell, move_feed_rate, f"rook a{rank}->d{rank}"))
        phases.append(phase)

    total_lines = sum(len(p) for p in phases)
    stats = {
        "from": move.from_sq,
        "to": move.to_sq,
        "piece": move.piece,
        "flags": move.flags,
        "captured": move.captured,
        "phases": len(phases),
        "gcode_lines": total_lines,
    }

    return phases, stats


def _validate_square(sq: str) -> bool:
    """Check that a square string is valid algebraic notation."""
    return bool(re.match(r"^[a-h][1-8]$", sq))


def generate_pick_place_demo_gcode(
    from_sq: str = "e2",
    to_sq: str = "e4",
    board_size_mm: float = 215.9,
    square_count: int = 8,
    gap_mm: float = 2.0,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    mirror_ranks: bool = False,
    magnet_on_cmd: str = "M3 S255",
    engage_dwell: float = 0.3,
    move_feed_rate: int = 3000,
) -> tuple[list[str], list[str], dict]:
    """Generate a simple pick-and-place demo in two phases.

    Phase 1 (carry): rapid to source, magnet on, carry to target.
    Phase 2 (return): after a hardware reset kills the magnet, return home.

    The caller must reset the Arduino between phases to de-energize the magnet.

    Returns:
        Tuple of (carry_lines, return_lines, stats_dict).
    """
    square_size = (board_size_mm - (square_count + 1) * gap_mm) / square_count

    from_xy = algebraic_to_mm(from_sq, square_size, gap_mm, origin_x, origin_y, square_count, mirror_ranks)
    to_xy = algebraic_to_mm(to_sq, square_size, gap_mm, origin_x, origin_y, square_count, mirror_ranks)

    # Phase 1: pick up and carry (magnet stays on)
    carry: list[str] = [
        f"; Pick-and-place demo: {from_sq} -> {to_sq}",
        f"G0 X{from_xy[0]:.2f} Y{from_xy[1]:.2f} ; rapid to {from_sq}",
    ]
    carry.extend(_magnet_on_gcode(magnet_on_cmd, engage_dwell))
    carry.append(f"G1 X{to_xy[0]:.2f} Y{to_xy[1]:.2f} F{move_feed_rate} ; carry to {to_sq}")
    carry.append("G4 P0 ; sync — drain motion buffer")

    # Phase 2: after reset kills the magnet, go home
    ret: list[str] = [
        "G0 X0.00 Y0.00 ; return home",
    ]

    stats = {
        "from": from_sq,
        "to": to_sq,
        "from_mm": [round(from_xy[0], 2), round(from_xy[1], 2)],
        "to_mm": [round(to_xy[0], 2), round(to_xy[1], 2)],
        "gcode_lines": len(carry) + len(ret),
    }

    return carry, ret, stats


def generate_chess_demo_gcode(
    board_size_mm: float = 215.9,
    square_count: int = 8,
    gap_mm: float = 2.0,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    tap_dwell_s: float = 0.3,
    magnet_on_cmd: str = "M3 S255",
    magnet_off_cmd: str = "M3 S0\nM5",
) -> tuple[list[str], dict]:
    """Generate G-code that moves to every square center and taps.

    Traversal order: row by row top-to-bottom (rank 8→1), left-to-right (a→h).

    Board layout per axis: gap | sq | gap | sq | ... | sq | gap
    square_size = (board_size_mm - (square_count + 1) * gap_mm) / square_count

    Returns:
        Tuple of (gcode_lines, stats_dict).
    """
    square_size = (board_size_mm - (square_count + 1) * gap_mm) / square_count
    total_squares = square_count * square_count
    lines: list[str] = []

    lines.append(f"; Chess demo: {total_squares} squares, {square_size:.2f}mm each, {gap_mm:.1f}mm gap")
    # Ensure magnet off at start
    for part in magnet_off_cmd.split("\n"):
        part = part.strip()
        if part:
            lines.append(f"{part} ; ensure magnet off")

    for row in range(square_count):
        rank = square_count - row  # row 0 = rank 8
        for col in range(square_count):
            file_letter = FILES[col] if col < len(FILES) else str(col)
            x, y = _square_center_mm(row, col, square_size, gap_mm, origin_x, origin_y)

            lines.append(f"G0 X{x:.2f} Y{y:.2f} ; {file_letter}{rank}")
            lines.extend(_magnet_on_gcode(magnet_on_cmd, tap_dwell_s))
            lines.extend(_magnet_off_gcode(magnet_off_cmd, 0.05))

    lines.append("G0 X0.00 Y0.00 ; return home")
    lines.append("G4 P2.0 ; final settle")
    for part in magnet_off_cmd.split("\n"):
        part = part.strip()
        if part:
            lines.append(f"{part} ; final magnet off")

    # Estimate time: rapid moves ~100mm/s, plus dwell per square
    total_travel_mm = 0.0
    prev_x, prev_y = 0.0, 0.0
    for row in range(square_count):
        for col in range(square_count):
            x, y = _square_center_mm(row, col, square_size, gap_mm, origin_x, origin_y)
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
        "gap_mm": gap_mm,
        "estimated_seconds": round(estimated_time_s, 1),
        "gcode_lines": len(lines),
    }

    return lines, stats


def generate_chess_demo_svg(
    board_size_mm: float = 215.9,
    square_count: int = 8,
    gap_mm: float = 2.0,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    svg_size: int = 500,
) -> str:
    """Generate an SVG preview of the demo traversal.

    Shows the board grid with numbered dots at each square center.
    Gaps between squares are rendered as the board background.
    """
    square_size = (board_size_mm - (square_count + 1) * gap_mm) / square_count
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

    # Board background (visible in the gaps)
    parts.append(
        f'<rect x="{margin}" y="{margin}" '
        f'width="{svg_size}" height="{svg_size}" '
        f'fill="#5c3d2e" stroke="#333" stroke-width="2"/>'
    )

    # Draw alternating light/dark squares with gap offsets
    sq_px = square_size * scale
    gap_px = gap_mm * scale
    for row in range(square_count):
        for col in range(square_count):
            sx = margin + (gap_mm + col * (square_size + gap_mm)) * scale
            sy = margin + (gap_mm + row * (square_size + gap_mm)) * scale
            fill = "#d4a574" if (row + col) % 2 == 1 else "#f0dab5"
            parts.append(
                f'<rect x="{sx:.1f}" y="{sy:.1f}" '
                f'width="{sq_px:.1f}" height="{sq_px:.1f}" '
                f'fill="{fill}"/>'
            )

    # File labels (a-h) along bottom
    files = "abcdefgh"
    for col in range(square_count):
        cx_mm = gap_mm + col * (square_size + gap_mm) + square_size / 2
        cx = margin + cx_mm * scale
        parts.append(
            f'<text x="{cx:.1f}" y="{total_size - 4}" '
            f'text-anchor="middle" fill="#555" font-size="11">'
            f'{files[col] if col < len(files) else col}</text>'
        )

    # Rank labels (8-1) along left
    for row in range(square_count):
        cy_mm = gap_mm + row * (square_size + gap_mm) + square_size / 2
        cy = margin + cy_mm * scale
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
            x_mm, y_mm = _square_center_mm(row, col, square_size, gap_mm, origin_x, origin_y)
            cx = margin + x_mm * scale
            cy = margin + y_mm * scale
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
    points_str = []
    for row in range(square_count):
        for col in range(square_count):
            x_mm, y_mm = _square_center_mm(row, col, square_size, gap_mm, origin_x, origin_y)
            cx = margin + x_mm * scale
            cy = margin + y_mm * scale
            points_str.append(f"{cx:.1f},{cy:.1f}")
    parts.append(
        f'<polyline points="{" ".join(points_str)}" '
        f'fill="none" stroke="rgba(220,50,50,0.3)" stroke-width="1.5" stroke-dasharray="4,3"/>'
    )

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


def algebraic_square_to_center_mm(
    alg: str,
    board_size_mm: float,
    square_count: int,
    origin_x: float,
    origin_y: float,
) -> Tuple[float, float]:
    """Map a square like ``e4`` to machine coordinates at the square center (mm).

    Layout matches :func:`generate_chess_demo_gcode`: row 0 is rank *square_count*,
    column 0 is file ``a``.
    """
    alg = alg.strip().lower()
    if len(alg) != 2:
        raise ValueError(f"Invalid square (expected 2 chars): {alg!r}")
    file_ch, rank_ch = alg[0], alg[1]
    if file_ch not in "abcdefgh" or not rank_ch.isdigit():
        raise ValueError(f"Invalid square: {alg!r}")
    rank = int(rank_ch)
    if not 1 <= rank <= square_count:
        raise ValueError(f"Invalid rank for board size: {alg!r}")
    col = ord(file_ch) - ord("a")
    row = square_count - rank
    square_size = board_size_mm / square_count
    x = origin_x + col * square_size + square_size / 2
    y = origin_y + row * square_size + square_size / 2
    return x, y


def generate_piece_move_gcode(
    from_alg: str,
    to_alg: str,
    *,
    board_size_mm: float = 200.0,
    square_count: int = 8,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    source_settle_s: float = 0.05,
    pickup_dwell_s: float = 0.2,
    place_dwell_s: float = 0.15,
) -> list[str]:
    """G-code for one pickup-move-place with host-side magnet directives.

    Sequence: move to source (magnet off), settle, magnet on + pickup dwell,
    rapid to destination, place dwell, magnet off. The plotter must be driven
    with :meth:`PlotterController.send_gcode_lines` and an ``electromagnet``
    instance so ``; @MAGNET_*`` lines take effect.
    """
    fx, fy = algebraic_square_to_center_mm(
        from_alg, board_size_mm, square_count, origin_x, origin_y
    )
    tx, ty = algebraic_square_to_center_mm(
        to_alg, board_size_mm, square_count, origin_x, origin_y
    )

    lines: list[str] = [
        f"; piece move {from_alg}->{to_alg}",
        MAGNET_GCODE_OFF,
        f"G0 X{fx:.2f} Y{fy:.2f} ; pickup {from_alg}",
        f"G4 P{source_settle_s:.2f} ; settle at source",
        MAGNET_GCODE_ON,
        f"G4 P{pickup_dwell_s:.2f} ; pickup dwell",
        f"G0 X{tx:.2f} Y{ty:.2f} ; place {to_alg}",
        f"G4 P{place_dwell_s:.2f} ; settle at destination",
        MAGNET_GCODE_OFF,
    ]
    return lines
